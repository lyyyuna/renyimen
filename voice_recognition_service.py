import speech_recognition as sr
import re
import asyncio
import gzip
import json
import time
import uuid
import websockets
import os


class VoiceRecognitionService:

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.wake_word = "任意门"
        # Qiniu ASR config
        self.qiniu_base_ws = os.environ.get("QINIU_OPENAI_BASE_WS", "wss://openai.qiniu.com/v1")
        self.qiniu_api_key = os.environ.get("QINIU_OPENAI_API_KEY")
        # Defaults for streaming PCM
        self.sample_rate = int(os.environ.get("QINIU_ASR_SAMPLE_RATE", "16000"))
        self.channels = int(os.environ.get("QINIU_ASR_CHANNELS", "1"))
        self.bits = int(os.environ.get("QINIU_ASR_BITS", "16"))
        self.seg_duration_ms = int(os.environ.get("QINIU_ASR_SEG_DURATION_MS", "300"))

    def listen_and_recognize(self, timeout=5, phrase_time_limit=10):
        """
        监听并识别语音

        Args:
            timeout: 等待语音输入的超时时间(秒)
            phrase_time_limit: 单次语音输入的最大时长(秒)

        Returns:
            str: 识别到的文本,如果失败返回None
        """
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            # Prefer Qiniu ASR if API key available; fallback to Google
            if self.qiniu_api_key:
                pcm_data = audio.get_raw_data(convert_rate=self.sample_rate, convert_width=self.bits // 8)
                text = asyncio.run(self._qiniu_asr_stream_once(pcm_data))
                return text
            else:
                text = self.recognizer.recognize_google(audio, language='zh-CN')
                return text

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"语音识别服务请求失败: {e}")
            return None
        except Exception as e:
            print(f"语音识别出错: {e}")
            return None

    # ---- Qiniu ASR streaming over WebSocket (single-shot) ----
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
                    flags=NO_SEQUENCE,
                    serial=JSON_SERIALIZATION,
                    comp=GZIP_COMPRESSION,
                    reserved=0x00):
        header = bytearray()
        header_size = 1
        header.append((self.PROTOCOL_VERSION << 4) | header_size)
        header.append((message_type << 4) | flags)
        header.append((serial << 4) | comp)
        header.append(reserved)
        return header

    def _gen_before_payload(self, sequence: int):
        b = bytearray()
        b.extend(sequence.to_bytes(4, 'big', signed=True))
        return b

    def _parse_response(self, res):
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
        if message_type == self.FULL_SERVER_RESPONSE:
            payload_size = int.from_bytes(payload[:4], 'big', signed=True)
            payload_msg = payload[4:]
        elif message_type == self.SERVER_ACK:
            seq = int.from_bytes(payload[:4], 'big', signed=True)
            result['seq'] = seq
            if len(payload) >= 8:
                payload_size = int.from_bytes(payload[4:8], 'big', signed=False)
                payload_msg = payload[8:]
            else:
                payload_msg = b""
        elif message_type == self.SERVER_ERROR_RESPONSE:
            code = int.from_bytes(payload[:4], 'big', signed=False)
            result['code'] = code
            payload_size = int.from_bytes(payload[4:8], 'big', signed=False)
            payload_msg = payload[8:]
        else:
            payload_msg = payload
        if comp == self.GZIP_COMPRESSION:
            try:
                payload_msg = gzip.decompress(payload_msg)
            except Exception:
                pass
        if serial == self.JSON_SERIALIZATION:
            try:
                payload_text = payload_msg.decode('utf-8')
                payload_msg = json.loads(payload_text)
            except Exception:
                pass
        else:
            payload_msg = payload_msg.decode('utf-8', errors='ignore')
        result['payload_msg'] = payload_msg
        return result

    async def _qiniu_asr_stream_once(self, pcm_bytes: bytes) -> str | None:
        if not self.qiniu_api_key:
            return None
        ws_url = f"{self.qiniu_base_ws}/voice/asr"
        headers = {"Authorization": "Bearer " + self.qiniu_api_key}
        # Build initial config payload
        req = {
            "user": {"uid": "renyimen"},
            "audio": {
                "format": "pcm",
                "sample_rate": self.sample_rate,
                "bits": self.bits,
                "channel": self.channels,
                "codec": "raw",
            },
            "request": {"model_name": "asr", "enable_punc": True}
        }
        seq = 1
        payload_bytes = gzip.compress(json.dumps(req).encode('utf-8'))
        init_msg = bytearray(self._gen_header(flags=self.POS_SEQUENCE))
        init_msg.extend(self._gen_before_payload(sequence=seq))
        init_msg.extend((len(payload_bytes)).to_bytes(4, 'big'))
        init_msg.extend(payload_bytes)
        try:
            async with websockets.connect(ws_url, extra_headers=headers, max_size=1000000000) as ws:
                await ws.send(init_msg)
                try:
                    res = await asyncio.wait_for(ws.recv(), timeout=10.0)
                except asyncio.TimeoutError:
                    return None
                _ = self._parse_response(res)
                # send audio chunk(s)
                seq += 1
                compressed_chunk = gzip.compress(pcm_bytes)
                audio_msg = bytearray(self._gen_header(message_type=self.AUDIO_ONLY_REQUEST, flags=self.POS_SEQUENCE))
                audio_msg.extend(self._gen_before_payload(sequence=seq))
                audio_msg.extend((len(compressed_chunk)).to_bytes(4, 'big'))
                audio_msg.extend(compressed_chunk)
                await ws.send(audio_msg)
                # keep reading until last package or timeout
                final_text = None
                begin = time.time()
                while time.time() - begin < 5.0:
                    try:
                        res = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    parsed = self._parse_response(res)
                    msg = parsed.get('payload_msg')
                    if isinstance(msg, dict):
                        data = msg.get('data') or {}
                        result = data.get('result') or {}
                        text = result.get('text')
                        if text:
                            final_text = text
                    if parsed.get('is_last_package'):
                        break
                return final_text
        except Exception:
            return None

    def parse_navigation_command(self, text):
        """
        解析导航命令

        支持格式:
        - "hi,任意门,我想步行去崇明岛"
        - "hi,任意门,我想驾车从张江人工智能岛到虹桥火车站"
        - "hi,任意门,我想公交去人民广场"

        Args:
            text: 语音识别的文本

        Returns:
            dict: 包含解析结果的字典,格式:
            {
                'valid': bool,  # 是否是有效的导航命令
                'start_point': str,  # 起点(可能为None)
                'end_point': str,  # 终点
                'transport_mode': str  # 交通方式('walking', 'driving', 'public_transit')
            }
        """
        if not text:
            return {'valid': False}

        text = text.replace(" ", "").replace(",", ",").lower()

        if self.wake_word not in text and "hi" not in text:
            return {'valid': False}

        result = {
            'valid': True,
            'start_point': None,
            'end_point': None,
            'transport_mode': None
        }

        # 只支持 驾车、公交、步行
        transport_keywords = {
            '步行': 'walking',

            '驾车': 'driving',

            '公交': 'public_transit'
        }

        for keyword, mode in transport_keywords.items():
            if keyword in text:
                result['transport_mode'] = mode
                break

        from_to_pattern = r'从(.+?)到(.+?)$'
        match = re.search(from_to_pattern, text)
        if match:
            result['start_point'] = match.group(1).strip()
            result['end_point'] = match.group(2).strip()
            return result

        go_to_pattern = r'去(.+?)$'
        match = re.search(go_to_pattern, text)
        if match:
            result['end_point'] = match.group(1).strip()
            return result

        return {'valid': False}


if __name__ == "__main__":
    service = VoiceRecognitionService()

    test_cases = [
        "hi,任意门,我想步行去崇明岛",
        "hi,任意门,我想驾车从张江人工智能岛到虹桥火车站",
        "hi 任意门 我想打车去浦东机场",
        "随便说点什么"
    ]

    print("测试语音命令解析:")
    for test in test_cases:
        result = service.parse_navigation_command(test)
        print(f"\n输入: {test}")
        print(f"结果: {result}")
