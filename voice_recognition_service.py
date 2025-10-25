import speech_recognition as sr
import logging
import re
import asyncio
import gzip
import json
import time
import uuid
import websockets
import os

# 配置日志级别
logging.basicConfig(level=logging.DEBUG)

class VoiceRecognitionService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000  # 提高麦克风灵敏度
        self.recognizer.pause_threshold = 1.0   # 暂停检测时间
        self.wake_word = "任意门"
        self.qiniu_base_ws = os.environ.get("QINIU_OPENAI_BASE_WS", "wss://openai.qiniu.com/v1")
        self.qiniu_api_key = os.environ.get("QINIU_OPENAI_API_KEY")
        # 临时禁用 Qiniu ASR 用于测试
        self.qiniu_api_key = None
        self.sample_rate = int(os.environ.get("QINIU_ASR_SAMPLE_RATE", "16000"))
        self.channels = int(os.environ.get("QINIU_ASR_CHANNELS", "1"))
        self.bits = int(os.environ.get("QINIU_ASR_BITS", "16"))
        self.seg_duration_ms = int(os.environ.get("QINIU_ASR_SEG_DURATION_MS", "300"))

    async def listen_and_recognize(self, timeout=5, phrase_time_limit=10):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logging.info("开始监听麦克风...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                pcm_data = audio.get_raw_data(convert_rate=self.sample_rate, convert_width=self.bits // 8)
                if len(pcm_data) == 0:
                    logging.warning("录制音频数据为空")
                    return None

            if self.qiniu_api_key:
                logging.info("发送到 Qiniu ASR...")
                text = await self._qiniu_asr_stream_once(pcm_data)
                if text:
                    logging.info(f"Qiniu 识别结果: {text}")
                    return text
                else:
                    logging.warning("Qiniu ASR 失败，回退到 Google")

            logging.info("使用 Google Speech Recognition...")
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            logging.info(f"Google 识别结果: {text}")
            return text
        except sr.WaitTimeoutError:
            logging.warning("语音监听超时")
            return None
        except sr.UnknownValueError:
            logging.warning("无法识别语音")
            return None
        except Exception as e:
            logging.error(f"语音识别出错: {e}")
            return None

    async def listen_for_wake_word(self, timeout=5, phrase_time_limit=3):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logging.info("开始监听唤醒词...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                pcm_data = audio.get_raw_data(convert_rate=self.sample_rate, convert_width=self.bits // 8)
                if len(pcm_data) == 0:
                    logging.warning("录制音频数据为空")
                    return False

                if self.qiniu_api_key:
                    logging.info("发送到 Qiniu ASR 检测唤醒词...")
                    text = await self._qiniu_asr_stream_once(pcm_data)
                    if text and self.wake_word in text.lower():
                        logging.info(f"检测到唤醒词: {text}")
                        return True
                else:
                    logging.info("使用 Google Speech Recognition 检测唤醒词...")
                    text = self.recognizer.recognize_google(audio, language='zh-CN')
                    if text and self.wake_word in text.lower():
                        logging.info(f"检测到唤醒词: {text}")
                        return True
            return False
        except sr.WaitTimeoutError:
            logging.debug("唤醒词监听超时")
            return False
        except sr.UnknownValueError:
            logging.debug("无法识别唤醒词")
            return False
        except Exception as e:
            logging.error(f"唤醒词检测出错: {e}")
            return False

    # ---- Qiniu ASR 常量定义 ----
    PROTOCOL_VERSION = 0b0001
    FULL_CLIENT_REQUEST = 0b0001
    AUDIO_ONLY_REQUEST = 0b0010
    FULL_SERVER_RESPONSE = 0b1001
    SERVER_ACK = 0b1011
    SERVER_ERROR_RESPONSE = 0b1111

    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    JSON_SERIALIZATION = 0b0001
    GZIP_COMPRESSION = 0b0001

    def _gen_header(self, message_type=FULL_CLIENT_REQUEST,
                    message_type_specific_flags=NO_SEQUENCE,
                    serial=JSON_SERIALIZATION,
                    comp=GZIP_COMPRESSION,
                    reserved=0x00):
        header = bytearray()
        header_size = 1
        header.append((self.PROTOCOL_VERSION << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial << 4) | comp)
        header.append(reserved)
        logging.debug(f"生成头部: {header}")
        return header

    def _gen_before_payload(self, sequence: int):
        b = bytearray()
        b.extend(sequence.to_bytes(4, 'big', signed=True))
        logging.debug(f"生成序列号: {sequence}")
        return b

    def _parse_response(self, res):
        logging.debug(f"原始响应数据: {res}")
        if not isinstance(res, bytes):
            return {'payload_msg': res}
        header_size = res[0] & 0x0f
        message_type = res[1] >> 4
        flags = res[1] & 0x0f
        serial = res[2] >> 4
        comp = res[2] & 0x0f
        payload = res[header_size * 4:]
        result = {}
        if flags & 0x01:
            seq = int.from_bytes(payload[:4], 'big', signed=True)
            result['payload_sequence'] = seq
            payload = payload[4:]
        result['is_last_package'] = bool(flags & 0x02)
        logging.debug(f"消息类型: {message_type}, 是否最后包: {result['is_last_package']}")
        if message_type == self.FULL_SERVER_RESPONSE:
            payload_size = int.from_bytes(payload[:4], 'big', signed=True)
            payload_msg = payload[4:4 + payload_size]
        elif message_type == self.SERVER_ACK:
            seq = int.from_bytes(payload[:4], 'big', signed=True)
            result['seq'] = seq
            if len(payload) >= 8:
                payload_size = int.from_bytes(payload[4:8], 'big', signed=False)
                payload_msg = payload[8:8 + payload_size]
            else:
                payload_msg = b""
        elif message_type == self.SERVER_ERROR_RESPONSE:
            code = int.from_bytes(payload[:4], 'big', signed=False)
            result['code'] = code
            payload_size = int.from_bytes(payload[4:8], 'big', signed=False)
            payload_msg = payload[8:8 + payload_size]
        else:
            payload_msg = payload
        if comp == self.GZIP_COMPRESSION:
            try:
                payload_msg = gzip.decompress(payload_msg)
                logging.debug("GZIP 解压成功")
            except Exception as e:
                logging.error(f"GZIP 解压失败: {e}")
        if serial == self.JSON_SERIALIZATION:
            try:
                payload_text = payload_msg.decode('utf-8')
                payload_msg = json.loads(payload_text)
                logging.debug(f"JSON 解析: {payload_msg}")
            except Exception as e:
                logging.error(f"JSON 解析失败: {e}")
        else:
            payload_msg = payload_msg.decode('utf-8', errors='ignore')
        result['payload_msg'] = payload_msg
        return result

    async def _qiniu_asr_stream_once(self, pcm_bytes: bytes) -> str | None:
        if not self.qiniu_api_key:
            logging.warning("缺少 Qiniu API Key")
            return None
        ws_url = f"{self.qiniu_base_ws}/voice/asr"
        headers = {"Authorization": "Bearer " + self.qiniu_api_key}
        uid = str(uuid.uuid4())
        logging.info(f"生成 UID: {uid}")
        req = {
            "user": {"uid": uid},
            "audio": {
                "format": "pcm",
                "sample_rate": self.sample_rate,
                "bits": self.bits,
                "channel": self.channels,
                "codec": "raw",
            },
            "request": {"model_name": "asr", "enable_punc": True}
        }
        payload_bytes = gzip.compress(json.dumps(req).encode('utf-8'))
        seq = 1
        init_msg = bytearray(self._gen_header(message_type=self.FULL_CLIENT_REQUEST, message_type_specific_flags=self.POS_SEQUENCE))
        init_msg.extend(self._gen_before_payload(sequence=seq))
        init_msg.extend(len(payload_bytes).to_bytes(4, 'big'))
        init_msg.extend(payload_bytes)
        logging.info("发送配置消息")
        try:
            async with websockets.connect(ws_url, extra_headers=headers, max_size=1000000000) as ws:
                await ws.send(init_msg)
                try:
                    res = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    parsed = self._parse_response(res)
                    logging.info(f"配置响应: {parsed}")
                    if 'code' in parsed and parsed['code'] != 0:
                        logging.error(f"配置错误码: {parsed['code']}")
                        return None
                except asyncio.TimeoutError:
                    logging.warning("配置响应超时")
                    return None

                seq += 1
                compressed_chunk = gzip.compress(pcm_bytes)
                audio_msg = bytearray(self._gen_header(message_type=self.AUDIO_ONLY_REQUEST, message_type_specific_flags=self.POS_SEQUENCE))
                audio_msg.extend(self._gen_before_payload(sequence=seq))
                audio_msg.extend(len(compressed_chunk).to_bytes(4, 'big'))
                audio_msg.extend(compressed_chunk)
                logging.info("发送音频数据")
                await ws.send(audio_msg)

                final_text = ""
                begin = time.time()
                while time.time() - begin < 10.0:
                    try:
                        res = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        parsed = self._parse_response(res)
                        msg = parsed.get('payload_msg')
                        if isinstance(msg, dict):
                            if 'result' in msg and 'text' in msg['result']:
                                text = msg['result']['text']
                            elif 'data' in msg and 'result' in msg['data'] and 'text' in msg['data']['result']:
                                text = msg['data']['result']['text']
                            else:
                                text = None
                            if text:
                                final_text = text
                                logging.info(f"中间识别文本: {text}")
                        if parsed.get('is_last_package'):
                            logging.info("收到最后包")
                            break
                    except asyncio.TimeoutError:
                        continue
                return final_text if final_text else None
        except Exception as e:
            logging.error(f"WebSocket 连接或发送失败: {e}")
            return None

    def parse_navigation_command(self, text, require_wake_word=True):
        if not text:
            logging.warning("输入文本为空")
            return {'valid': False}

        text = text.replace(" ", "").replace(",", "").lower()
        logging.debug(f"处理后的输入文本: {text}")

        # 对于手动语音输入，放宽唤醒词要求
        if require_wake_word:
            if self.wake_word not in text and "hi" not in text:
                if "任意" in text or "门" in text:
                    logging.info(f"部分匹配唤醒词: {text}")
                else:
                    logging.warning("缺少唤醒词，解析失败")
                    return {'valid': False}

        result = {
            'valid': True,
            'start_point': None,
            'end_point': None,
            'transport_mode': None
        }

        transport_keywords = {
            '步行': 'walking',
            '驾车': 'driving',
            '自驾': 'driving',
            '开车': 'driving',
            '公交': 'public_transit',
            '地铁': 'public_transit'
        }

        for keyword, mode in transport_keywords.items():
            if keyword in text:
                result['transport_mode'] = mode
                break

        from_to_pattern = r'从(.+?)到(.+)'
        match = re.search(from_to_pattern, text)
        if match:
            result['start_point'] = match.group(1).strip()
            result['end_point'] = match.group(2).strip()
            logging.debug(f"解析导航: 从 {result['start_point']} 到 {result['end_point']}, 方式: {result['transport_mode']}")
            return result

        go_to_pattern = r'去(.+)'
        match = re.search(go_to_pattern, text)
        if match:
            result['end_point'] = match.group(1).strip()
            logging.debug(f"解析导航: 去 {result['end_point']}, 方式: {result['transport_mode']}")
            return result

        logging.warning("无法匹配导航模式")
        return {'valid': False}