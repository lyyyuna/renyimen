import sys
import subprocess
import json
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QTextEdit, QProgressBar, QComboBox
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from navigation_service import NavigationService
from voice_recognition_service import VoiceRecognitionService


class VoiceRecognitionWorker(QThread):
    """后台处理语音识别的工作线程"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, voice_service):
        super().__init__()
        self.voice_service = voice_service

    def run(self):
        try:
            text = self.voice_service.listen_and_recognize(timeout=5, phrase_time_limit=10)
            if text:
                self.finished.emit(text)
            else:
                self.error.emit("未识别到语音或识别失败")
        except Exception as e:
            self.error.emit(f"语音识别出错: {str(e)}")


class NavigationWorker(QThread):
    """后台处理导航请求的工作线程"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            # 执行导航处理逻辑
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
        self.voice_listening = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("任意门智能导航")
        self.setFixedSize(550, 450)

        layout = QVBoxLayout()

        self.label = QLabel("请输入导航需求:")
        layout.addWidget(self.label)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("例如：驾车从张江人工智能岛到虹桥火车站")
        self.input_field.returnPressed.connect(self.on_enter_pressed)
        input_layout.addWidget(self.input_field)

        # 地图类型下拉（高德/百度）
        self.map_provider_combo = QComboBox()
        self.map_provider_combo.addItems(["高德", "百度"])
        self.map_provider_combo.setFixedWidth(90)
        input_layout.addWidget(self.map_provider_combo)

        self.voice_button = QPushButton("🎤 开始")
        self.voice_button.setFixedWidth(80)
        self.voice_button.clicked.connect(self.on_voice_input)
        input_layout.addWidget(self.voice_button)

        self.voice_pause_button = QPushButton("⏸ 暂停")
        self.voice_pause_button.setFixedWidth(80)
        self.voice_pause_button.setEnabled(False)
        self.voice_pause_button.clicked.connect(self.on_voice_pause_toggle)
        input_layout.addWidget(self.voice_pause_button)

        layout.addLayout(input_layout)

        self.voice_hint_label = QLabel("提示: 点击语音按钮后说\"hi,任意门,我想驾车/公交/步行从A到B\"")
        self.voice_hint_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.voice_hint_label)

        self.submit_button = QPushButton("确定")
        self.submit_button.clicked.connect(self.on_submit)
        layout.addWidget(self.submit_button)

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.output_label = QLabel("输出:")
        layout.addWidget(self.output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        self.setLayout(layout)

        # 初始化进度条定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_value = 0

    def on_enter_pressed(self):
        self.on_submit()

    def on_voice_input(self):
        """开始/停止后台语音输入"""
        if not self.voice_listening:
            # Start background listening
            self.output_text.append("🎤 后台监听已启动，请说话...")
            self.input_field.setEnabled(False)
            self.submit_button.setEnabled(False)
            started = self.voice_service.start_background_listening(self._on_bg_text, phrase_time_limit=10, error_callback=self._on_bg_error)
            if started:
                self.voice_listening = True
                self.voice_button.setText("■ 停止")
                self.voice_pause_button.setEnabled(True)
                self.voice_hint_label.setText("提示: 说出导航需求，点击暂停/继续控制识别")
            else:
                self.output_text.append("❌ 启动后台监听失败")
        else:
            # Stop background listening
            self.voice_service.stop_background_listening()
            self._reset_voice_ui()

    def on_voice_recognition_finished(self, text):
        """语音识别完成"""
        self.output_text.append(f"🎤 识别到: {text}")

        result = self.voice_service.parse_navigation_command(text)

        if result['valid']:
            # 停止后台监听，避免重复触发导航
            if self.voice_listening:
                self.voice_service.stop_background_listening()
                self.voice_listening = False
                self.voice_pause_button.setEnabled(False)
            command_text = text
            self.input_field.setText(command_text)
            self.output_text.append("✅ 检测到导航指令,正在处理...")
            self.start_navigation_process(command_text)
        else:
            self.output_text.append("❌ 未检测到有效的导航指令")
            self.output_text.append("💡 请使用格式: hi,任意门,我想驾车/公交/步行从A到B")
            self._reset_voice_ui()

    def on_voice_recognition_error(self, error):
        """语音识别出错"""
        self.output_text.append(f"❌ {error}")
        self._reset_voice_ui()

    def _on_bg_text(self, text: str):
        """后台监听回调：切回UI线程处理识别文本"""
        QTimer.singleShot(0, lambda: self._handle_bg_text(text))

    def _handle_bg_text(self, text: str):
        # Mirror single-run behavior
        self.on_voice_recognition_finished(text)

    def _on_bg_error(self, message: str):
        """后台监听错误/未识别反馈：切回UI线程更新提示"""
        QTimer.singleShot(0, lambda: self._handle_bg_error(message))

    def _handle_bg_error(self, message: str):
        # 当后台未识别或服务错误时给予用户反馈，不打断监听
        if self.voice_listening:
            self.output_text.append(f"⚠️ {message}")

    def on_voice_pause_toggle(self):
        """暂停/继续后台语音识别"""
        if not self.voice_listening:
            return
        # Toggle pause state
        # Try to pause or resume via service
        # We can determine current state via button text
        if self.voice_pause_button.text().startswith("⏸"):
            ok = self.voice_service.pause_background()
            if ok:
                self.voice_pause_button.setText("▶️ 继续")
                self.output_text.append("⏸ 已暂停识别")
        else:
            ok = self.voice_service.resume_background()
            if ok:
                self.voice_pause_button.setText("⏸ 暂停")
                self.output_text.append("▶️ 已恢复识别")

    def _reset_voice_ui(self):
        """恢复与语音相关的UI状态"""
        self.voice_listening = False
        self.voice_button.setEnabled(True)
        self.voice_button.setText("🎤 开始")
        self.voice_pause_button.setEnabled(False)
        self.voice_pause_button.setText("⏸ 暂停")
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.voice_hint_label.setText("提示: 点击语音开始后台监听，或直接输入")

    def on_submit(self):
        text = self.input_field.text()
        if text:
            self.output_text.append(f"你输入了: {text}")
            self.start_navigation_process(text)
            self.input_field.clear()

    def start_navigation_process(self, text):
        """启动导航处理过程"""
        # 禁用输入控件
        self.input_field.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.submit_button.setText("处理中...")
        self.voice_button.setEnabled(False)

        # 显示进度条并开始动画
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.progress_value = 0
        self.progress_timer.start(100)  # 每100ms更新一次

        self.output_text.append("🤖 正在分析导航请求...")

        # 启动后台线程
        # 将选择的地图类型设置到环境变量，供 MCP 服务读取
        provider = "amap" if self.map_provider_combo.currentText() == "高德" else "baidu"
        os.environ["MAP_PROVIDER"] = provider

        # 同步到本地导航服务备用解析
        self.nav_service.provider = provider

        self.worker = NavigationWorker(text)
        self.worker.finished.connect(self.on_navigation_finished)
        self.worker.error.connect(self.on_navigation_error)
        self.worker.start()

    def update_progress(self):
        """更新进度条动画"""
        self.progress_value = (self.progress_value + 5) % 100
        if self.progress_bar.maximum() != 0:
            self.progress_bar.setValue(self.progress_value)

    def on_navigation_finished(self, result):
        """导航处理完成"""
        self.finish_navigation_process()
        self.output_text.append(result)

    def on_navigation_error(self, error):
        """导航处理出错"""
        self.finish_navigation_process()
        self.output_text.append(error)
        # 尝试备用解析
        self.fallback_navigation_parse(self.worker.text)

    def finish_navigation_process(self):
        """结束导航处理过程"""
        # 停止进度条
        self.progress_timer.stop()
        self.progress_bar.setVisible(False)

        # 恢复输入控件
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.submit_button.setText("确定")
        self.voice_button.setEnabled(True)
        self.voice_button.setText("🎤 开始")
        self.voice_pause_button.setEnabled(False)



    def fallback_navigation_parse(self, text):
        """备用导航解析方案"""
        text_lower = text.lower()

        # 简单的关键词识别
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



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InputApp()
    window.show()
    sys.exit(app.exec())
