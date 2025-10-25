import speech_recognition as sr
import re


class VoiceRecognitionService:

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.wake_word = "任意门"
        # Background listening control
        self._bg_stop = None  # callable to stop background listener
        self._paused = False
        self._source = None
        self._callback = None

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

    def start_background_listening(self, callback, phrase_time_limit=10, error_callback=None):
        """
        Start background listening and invoke callback(text) on recognition.
        Stores a stop function that can be called to end listening.
        """
        if self._bg_stop is not None:
            return False
        self._callback = callback
        self._error_callback = error_callback
        try:
            self._source = sr.Microphone()
            with self._source as src:
                # Improve stability by adapting to ambient noise
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.adjust_for_ambient_noise(src, duration=0.6)

            def _internal_callback(recognizer, audio):
                if self._paused:
                    return
                try:
                    text = recognizer.recognize_google(audio, language='zh-CN')
                    if self._callback:
                        self._callback(text)
                except sr.UnknownValueError:
                    # No speech or could not understand
                    if self._error_callback:
                        try:
                            self._error_callback("未识别到语音或语音不清晰")
                        except Exception:
                            pass
                except sr.RequestError as e:
                    # Recognition service error
                    if self._error_callback:
                        try:
                            self._error_callback(f"语音识别服务请求失败: {e}")
                        except Exception:
                            pass
                except Exception as e:
                    # Other runtime errors
                    if self._error_callback:
                        try:
                            self._error_callback(f"语音识别出错: {e}")
                        except Exception:
                            pass

            self._bg_stop = self.recognizer.listen_in_background(self._source, _internal_callback, phrase_time_limit=phrase_time_limit)
            self._paused = False
            return True
        except Exception as e:
            print(f"启动后台监听失败: {e}")
            self._bg_stop = None
            self._source = None
            return False

    def pause_background(self):
        """Pause recognition callbacks without releasing microphone."""
        if self._bg_stop is None:
            return False
        self._paused = True
        return True

    def resume_background(self):
        """Resume recognition callbacks."""
        if self._bg_stop is None:
            return False
        self._paused = False
        return True

    def stop_background_listening(self):
        """Stop background listening and release resources."""
        if self._bg_stop:
            try:
                self._bg_stop(wait_for_stop=False)
            except Exception:
                pass
        self._bg_stop = None
        self._paused = False
        self._callback = None
        self._error_callback = None
        if self._source:
            try:
                self._source.__exit__(None, None, None)
            except Exception:
                pass
        self._source = None

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
