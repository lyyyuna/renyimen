import sys
import subprocess
import json
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QTextEdit, QProgressBar, QComboBox
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from navigation_service import NavigationService


class NavigationWorker(QThread):
    """后台处理导航请求的工作线程"""
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, text, transport_mode=None):
        super().__init__()
        self.text = text
        self.transport_mode = transport_mode
    
    def run(self):
        try:
            # 执行导航处理逻辑
            config_path = os.path.join(os.path.dirname(__file__), "claude_desktop_config.json")
            transport_mode_text = f"\n\n交通方式：{self.transport_mode}" if self.transport_mode else ""
            prompt = f"""用户输入："{self.text}"{transport_mode_text}

请分析这段文字是否包含导航需求。如果包含导航需求，请使用已注册的MCP导航工具来处理：

1. 识别起点和终点信息
2. 调用navigate工具，参数格式：
   - start_point: 起点名称
   - end_point: 终点名称  
   - start_city: 起点城市（可选）
   - end_city: 终点城市（可选）
   - transport_mode: 交通方式（{'已选择：' + self.transport_mode if self.transport_mode else '可选'}）

支持的导航格式：
- "从A到B"
- "去某地"  
- "导航到某地"
- "开车从A到B"

支持的交通方式：
- driving（驾车）
- taxi（打车）
- public_transit（公共交通）
- carpooling（顺风车）
- cycling（骑行）
- walking（步行）
- train（火车）
- airplane（飞机）
- motorcycle（摩托车）

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
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("任意门智能导航")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("请输入导航需求:")
        layout.addWidget(self.label)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("例如：从上海新天地到中友嘉园")
        self.input_field.returnPressed.connect(self.on_enter_pressed)
        layout.addWidget(self.input_field)
        
        transport_layout = QHBoxLayout()
        transport_label = QLabel("交通方式:")
        transport_layout.addWidget(transport_label)
        
        self.transport_combo = QComboBox()
        self.transport_combo.addItem("驾车 (driving)", "driving")
        self.transport_combo.addItem("打车 (taxi)", "taxi")
        self.transport_combo.addItem("公共交通 (public_transit)", "public_transit")
        self.transport_combo.addItem("顺风车 (carpooling)", "carpooling")
        self.transport_combo.addItem("骑行 (cycling)", "cycling")
        self.transport_combo.addItem("步行 (walking)", "walking")
        self.transport_combo.addItem("火车 (train)", "train")
        self.transport_combo.addItem("飞机 (airplane)", "airplane")
        self.transport_combo.addItem("摩托车 (motorcycle)", "motorcycle")
        transport_layout.addWidget(self.transport_combo)
        layout.addLayout(transport_layout)
        
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
    
    def on_submit(self):
        text = self.input_field.text()
        if text:
            transport_mode = self.transport_combo.currentData()
            transport_text = self.transport_combo.currentText()
            self.output_text.append(f"你输入了: {text}")
            self.output_text.append(f"交通方式: {transport_text}")
            self.start_navigation_process(text, transport_mode)
            self.input_field.clear()
    
    def start_navigation_process(self, text, transport_mode=None):
        """启动导航处理过程"""
        # 禁用输入控件
        self.input_field.setEnabled(False)
        self.transport_combo.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.submit_button.setText("处理中...")
        
        # 显示进度条并开始动画
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.progress_value = 0
        self.progress_timer.start(100)  # 每100ms更新一次
        
        self.output_text.append("🤖 正在分析导航请求...")
        
        # 启动后台线程
        self.worker = NavigationWorker(text, transport_mode)
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
        self.transport_combo.setEnabled(True)
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