import speech_recognition as sr
import re
from typing import Optional, Dict


class VoiceRecognitionService:
    def __init__(self, wake_word: str = "任意门"):
        self.recognizer = sr.Recognizer()
        self.wake_word = wake_word
        self.microphone = None
        
    def listen_once(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[str]:
        try:
            if self.microphone is None:
                self.microphone = sr.Microphone()
            
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
            
            text = self.recognizer.recognize_google(audio, language="zh-CN")
            return text
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"语音识别服务错误: {e}")
            return None
        except Exception as e:
            print(f"语音识别异常: {e}")
            return None
    
    def parse_navigation_command(self, text: str) -> Optional[Dict[str, str]]:
        if not text:
            return None
        
        text = text.replace("，", ",").replace(" ", "")
        
        if self.wake_word not in text and "hi" not in text.lower():
            return None
        
        travel_mode = "driving"
        if "步行" in text or "走路" in text:
            travel_mode = "walking"
        elif "驾车" in text or "开车" in text:
            travel_mode = "driving"
        elif "公交" in text or "坐车" in text:
            travel_mode = "bus"
        
        start_point = None
        end_point = None
        
        pattern1 = r"从(.+?)到(.+?)$"
        match = re.search(pattern1, text)
        if match:
            start_point = match.group(1).strip()
            end_point = match.group(2).strip()
        else:
            pattern2 = r"去(.+?)$"
            match = re.search(pattern2, text)
            if match:
                end_point = match.group(1).strip()
                start_point = "当前位置"
        
        if end_point:
            return {
                "start_point": start_point,
                "end_point": end_point,
                "travel_mode": travel_mode,
                "raw_text": text
            }
        
        return None
    
    def listen_for_navigation(self, timeout: int = 5) -> Optional[Dict[str, str]]:
        text = self.listen_once(timeout=timeout)
        if text:
            return self.parse_navigation_command(text)
        return None


if __name__ == "__main__":
    service = VoiceRecognitionService()
    
    test_cases = [
        "hi，任意门，我想步行去崇明岛",
        "hi，任意门，我想驾车从张江人工智能岛到虹桥火车站",
        "任意门，我要去天安门",
        "hi任意门开车从上海到北京"
    ]
    
    print("测试语音命令解析:")
    for test in test_cases:
        result = service.parse_navigation_command(test)
        print(f"\n输入: {test}")
        print(f"解析结果: {result}")
