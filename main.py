import sys
import logging
import subprocess
import json
import os
import asyncio
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QTextEdit, QProgressBar, QComboBox
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon
from navigation_service import NavigationService
from voice_recognition_service import VoiceRecognitionService

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# macOS 事件循环优化
os.environ["QT_MAC_WANTS_LAYER"] = "1"

class VoiceRecognitionWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, voice_service, is_wake_word=False):
        super().__init__()
        self.voice_service = voice_service
        self.is_wake_word = is_wake_word
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            if self.is_wake_word:
                result = self.loop.run_until_complete(self.voice_service.listen_for_wake_word(timeout=5, phrase_time_limit=3))
                if result:
                    self.finished.emit("唤醒词检测成功")
                else:
                    self.error.emit("未检测到唤醒词")
            else:
                text = self.loop.run_until_complete(self.voice_service.listen_and_recognize(timeout=5, phrase_time_limit=10))
                if text:
                    self.finished.emit(text)
                else:
                    self.error.emit("未识别到语音或识别失败")
        except Exception as e:
            self.error.emit(f"语音识别出错: {str(e)}")
        finally:
            self.loop.close()
            self.loop = None

    def stop(self):
        logging.info("停止 VoiceRecognitionWorker 线程")
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.quit()
        self.wait(1000)

class NavigationWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), "claude_desktop_config.json")
            prompt = f"""用户输入："{self.text}"

请分析这段文字是否包含导航需求。如果包含导航需求，请使用已注册的MCP导航工具来处理：

1. 识别起点和终点信息，如果不指定起点，则起点参数为空
2. 识别交通方式（如果用户在输入中指定了交通方式）
3. 调用navigate工具，参数格式：
   - start_point: 起点名称
   - end_point: 终点名称
   - start_city: 起点城市（可选）
   - end_city: 终点城市（可选）
   - transport_mode: 交通方式（如果用户指定了交通方式）
   
支持的导航格式：
- "从A到B"
- "去某地"
- "导航到某地"
- "驾车从A到B"
- "打车去某地"
- "骑车从A到B"

支持的交通方式识别（从用户输入中提取）：
- 驾车/开车 → driving
- 公共交通/公交/地铁 → public_transit
- 步行/走路 → walking

如果无法识别为导航请求，请简单回复"这不是导航请求"。
如果是导航请求，请直接调用navigate工具，不要只是回复文字。"""

            cmd = [
                "claude",
                "--mcp-config", config_path,
                "--dangerously-skip-permissions",
                "--print",
                prompt
            ]

            env = os.environ.copy()
            env["CLAUDE_MCP_CONFIG"] = config_path

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            if result.returncode == 0:
                response = result.stdout.strip()
                self.finished.emit(f"✅ Claude回复: {response}")
            else:
                error_msg = result.stderr.strip() or "命令执行失败"
                self.error.emit(f"❌ 执行失败: {error_msg}")

        except Exception as e:
            self.error.emit(f"❌ 调用Claude CLI失败: {str(e)}")

class InputApp(QWidget):
    def __init__(self):
        super().__init__()
        self.nav_service = NavigationService()
        self.voice_service = VoiceRecognitionService()
        self.is_listening_wake_word = False
        self.active_threads = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("任意门智能导航")
        self.setFixedSize(550, 450)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()

        self.label = QLabel("请输入导航需求:")
        layout.addWidget(self.label)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("例如：驾车从张江人工智能岛到虹桥火车站")
        self.input_field.returnPressed.connect(self.on_enter_pressed)
        input_layout.addWidget(self.input_field)

        self.map_provider_combo = QComboBox()
        self.map_provider_combo.addItems(["高德", "百度"])
        self.map_provider_combo.setFixedWidth(90)
        input_layout.addWidget(self.map_provider_combo)

        self.voice_button = QPushButton("🎤 语音")
        self.voice_button.setFixedWidth(80)
        self.voice_button.clicked.connect(self.on_voice_input)
        input_layout.addWidget(self.voice_button)

        self.wake_word_button = QPushButton("唤醒监听")
        self.wake_word_button.setFixedWidth(100)
        self.wake_word_button.clicked.connect(self.toggle_wake_word_listening)
        input_layout.addWidget(self.wake_word_button)

        layout.addLayout(input_layout)

        self.voice_hint_label = QLabel("提示: 清晰地说\"hi,任意门,我想驾车/公交/步行从A到B\"")
        self.voice_hint_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.voice_hint_label)

        self.submit_button = QPushButton("确定")
        self.submit_button.clicked.connect(self.on_submit)
        layout.addWidget(self.submit_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.output_label = QLabel("输出:")
        layout.addWidget(self.output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        self.setLayout(layout)

        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_value = 0

    def toggle_wake_word_listening(self):
        if not self.is_listening_wake_word:
            self.is_listening_wake_word = True
            self.wake_word_button.setText("停止监听")
            self.output_text.append("🔊 开始监听唤醒词...")
            self.start_wake_word_listening()
        else:
            self.is_listening_wake_word = False
            self.wake_word_button.setText("唤醒监听")
            self.output_text.append("🛑 停止监听唤醒词")
            for thread in self.active_threads[:]:
                thread.stop()
                self.active_threads.remove(thread)

    def start_wake_word_listening(self):
        if not self.is_listening_wake_word:
            return
        self.voice_worker = VoiceRecognitionWorker(self.voice_service, is_wake_word=True)
        self.voice_worker.finished.connect(self.on_wake_word_detected)
        self.voice_worker.error.connect(self.on_wake_word_error)
        self.active_threads.append(self.voice_worker)
        self.voice_worker.start()

    def on_wake_word_detected(self):
        self.output_text.append("✅ 检测到唤醒词，进入语音识别...")
        self.is_listening_wake_word = False
        self.wake_word_button.setText("唤醒监听")
        for thread in self.active_threads[:]:
            thread.stop()
            self.active_threads.remove(thread)
        self.on_voice_input()

    def on_wake_word_error(self, error):
        self.output_text.append(f"❌ {error}")
        if "Qiniu API 认证失败或配额超限" in str(error):
            self.output_text.append("⚠️ Qiniu ASR 认证失败，请检查 API 密钥或配额限制（登录 Qiniu 控制台或联系支持）")
        else:
            self.output_text.append("⚠️ 唤醒词检测失败，请清晰地说‘hi,任意门’")
        for thread in self.active_threads[:]:
            if thread == self.sender():
                thread.stop()
                self.active_threads.remove(thread)
        self.start_wake_word_listening()

    def on_voice_input(self):
        self.output_text.append("🎤 请说话...")
        self.voice_button.setEnabled(False)
        self.voice_button.setText("识别中...")
        self.input_field.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.wake_word_button.setEnabled(False)

        self.voice_worker = VoiceRecognitionWorker(self.voice_service)
        self.voice_worker.finished.connect(self.on_voice_recognition_finished)
        self.voice_worker.error.connect(self.on_voice_recognition_error)
        self.active_threads.append(self.voice_worker)
        self.voice_worker.start()

    def on_voice_recognition_finished(self, text):
        self.output_text.append(f"🎤 识别到: {text}")
        result = self.voice_service.parse_navigation_command(text, require_wake_word=False)
        if result['valid']:
            command_text = text
            self.input_field.setText(command_text)
            self.output_text.append("✅ 检测到导航指令，正在处理...")
            self.start_navigation_process(command_text)
        else:
            self.output_text.append("❌ 未检测到有效的导航指令")
            self.output_text.append("💡 请使用格式: 驾车/公交/步行从A到B 或 去某地")
            logging.warning(f"解析失败，输入文本: {text}")
            if "导航" in text or "去" in text:
                self.output_text.append("⚠️ 可能因响应不完整未触发导航，请重试或切换到 Google 模式")
        for thread in self.active_threads[:]:
            if thread == self.sender():
                thread.stop()
                self.active_threads.remove(thread)
        self.finish_voice_process()

    def on_voice_recognition_error(self, error):
        self.output_text.append(f"❌ {error}")
        if "Qiniu API 认证失败或配额超限" in str(error):
            self.output_text.append("⚠️ Qiniu ASR 认证失败，请检查 API 密钥或配额限制（登录 Qiniu 控制台或联系支持）")
        else:
            self.output_text.append("⚠️ 语音识别失败，请检查麦克风或网络")
        for thread in self.active_threads[:]:
            if thread == self.sender():
                thread.stop()
                self.active_threads.remove(thread)
        self.finish_voice_process()

    def finish_voice_process(self):
        self.voice_button.setEnabled(True)
        self.voice_button.setText("🎤 语音")
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.wake_word_button.setEnabled(True)
        if self.is_listening_wake_word:
            self.start_wake_word_listening()

    def on_enter_pressed(self):
        self.on_submit()

    def on_submit(self):
        text = self.input_field.text()
        if text:
            self.output_text.append(f"你输入了: {text}")
            self.start_navigation_process(text)
            self.input_field.clear()

    def start_navigation_process(self, text):
        self.input_field.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.submit_button.setText("处理中...")
        self.voice_button.setEnabled(False)
        self.wake_word_button.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_value = 0
        self.progress_timer.start(100)

        self.output_text.append("🤖 正在分析导航请求...")

        provider = "amap" if self.map_provider_combo.currentText() == "高德" else "baidu"
        os.environ["MAP_PROVIDER"] = provider
        self.nav_service.provider = provider

        self.worker = NavigationWorker(text)
        self.worker.finished.connect(self.on_navigation_finished)
        self.worker.error.connect(self.on_navigation_error)
        self.active_threads.append(self.worker)
        self.worker.start()

    def update_progress(self):
        self.progress_value = (self.progress_value + 5) % 100
        if self.progress_bar.maximum() != 0:
            self.progress_bar.setValue(self.progress_value)

    def on_navigation_finished(self, result):
        self.finish_navigation_process()
        self.output_text.append(result)
        for thread in self.active_threads[:]:
            if thread == self.sender():
                thread.quit()
                thread.wait(1000)
                self.active_threads.remove(thread)

    def on_navigation_error(self, error):
        self.finish_navigation_process()
        self.output_text.append(error)
        self.fallback_navigation_parse(self.worker.text)
        for thread in self.active_threads[:]:
            if thread == self.sender():
                thread.quit()
                thread.wait(1000)
                self.active_threads.remove(thread)

    def finish_navigation_process(self):
        self.progress_timer.stop()
        self.progress_bar.setVisible(False)
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.submit_button.setText("确定")
        self.voice_button.setEnabled(True)
        self.wake_word_button.setEnabled(True)
        if self.is_listening_wake_word:
            self.start_wake_word_listening()

    def fallback_navigation_parse(self, text):
        text_lower = text.lower()
        if "从" in text and "到" in text:
            parts = text.split("从")
            if len(parts) > 1:
                rest = parts[1]
                if "到" in rest:
                    from_to = rest.split("到")
                    if len(from_to) >= 2:
                        start = from_to[0].strip()
                        end = from_to[1].strip()
                        success = self.nav_service.navigate(start, end)
                        if success:
                            self.output_text.append(f"🗺️ 备用解析成功: {start} → {end}")
                        else:
                            self.output_text.append(f"❌ 导航失败: {start} → {end}")
                        return
        elif "去" in text:
            parts = text.split("去")
            if len(parts) > 1:
                destination = parts[1].strip()
                success = self.nav_service.navigate("当前位置", destination)
                if success:
                    self.output_text.append(f"🗺️ 备用解析成功: 当前位置 → {destination}")
                else:
                    self.output_text.append(f"❌ 导航失败: 当前位置 → {destination}")
                return
        self.output_text.append("❓ 无法识别导航请求，请使用'从A到B'或'去某地'的格式")

    def closeEvent(self, event):
        logging.info("窗口关闭，停止所有线程")
        self.is_listening_wake_word = False
        for thread in self.active_threads[:]:
            thread.stop()
            self.active_threads.remove(thread)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = InputApp()
    window.show()
    sys.exit(app.exec())