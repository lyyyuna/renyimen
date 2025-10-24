import sys
import subprocess
import json
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QTextEdit, QProgressBar
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from navigation_service import NavigationService
from voice_recognition_service import VoiceRecognitionService


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

1. 识别起点和终点信息
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


class VoiceWorker(QThread):
    finished = Signal(str)
    error = Signal(str)
    recognized = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.voice_service = VoiceRecognitionService()
        self.is_running = True
    
    def run(self):
        try:
            result = self.voice_service.listen_for_navigation(timeout=10)
            if result:
                text = f"{result['raw_text']}"
                self.recognized.emit(result['raw_text'])
                self.finished.emit(f"✅ 识别成功: {result['raw_text']}")
            else:
                self.error.emit("未识别到有效的导航指令")
        except Exception as e:
            self.error.emit(f"语音识别失败: {str(e)}")
    
    def stop(self):
        self.is_running = False


class InputApp(QWidget):
    def __init__(self):
        super().__init__()
        self.nav_service = NavigationService()
        self.voice_worker = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("任意门智能导航")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("请输入文字或使用语音:")
        layout.addWidget(self.label)
        
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("例如：驾车从张江人工智能岛到虹桥火车站")
        self.input_field.returnPressed.connect(self.on_enter_pressed)
        input_layout.addWidget(self.input_field)
        
        self.voice_button = QPushButton("🎤 语音")
        self.voice_button.clicked.connect(self.on_voice_input)
        self.voice_button.setFixedWidth(80)
        input_layout.addWidget(self.voice_button)
        
        layout.addLayout(input_layout)
        
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
        self.voice_button.setEnabled(False)
        self.voice_button.setText("🎤 监听中...")
        self.input_field.setEnabled(False)
        self.submit_button.setEnabled(False)
        
        self.output_text.append("🎤 请说话... (例如: hi,任意门,我想步行去崇明岛)")
        
        self.voice_worker = VoiceWorker()
        self.voice_worker.recognized.connect(self.on_voice_recognized)
        self.voice_worker.finished.connect(self.on_voice_finished)
        self.voice_worker.error.connect(self.on_voice_error)
        self.voice_worker.start()
    
    def on_voice_recognized(self, text):
        self.input_field.setText(text)
    
    def on_voice_finished(self, message):
        self.output_text.append(message)
        self.voice_button.setEnabled(True)
        self.voice_button.setText("🎤 语音")
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
        
        if self.input_field.text():
            self.on_submit()
    
    def on_voice_error(self, error):
        self.output_text.append(f"❌ {error}")
        self.voice_button.setEnabled(True)
        self.voice_button.setText("🎤 语音")
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
    
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
        
        # 显示进度条并开始动画
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.progress_value = 0
        self.progress_timer.start(100)  # 每100ms更新一次
        
        self.output_text.append("🤖 正在分析导航请求...")
        
        # 启动后台线程
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