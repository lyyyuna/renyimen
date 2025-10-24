# 任意门智能导航系统

基于 Claude CLI + MCP 的智能导航应用，支持自然语言输入，自动解析导航需求并打开地图导航链接（高德/百度）。

## 功能特性

- 🗣️ **自然语言输入** - 支持"从A到B"、"去某地"等自然表达
- 🎤 **语音识别** - 支持语音输入导航指令，唤醒词"hi,任意门"
- 🤖 **AI智能解析** - 基于 Claude CLI + MCP 服务解析导航意图
- 🗺️ **多地图集成** - 自动生成并打开导航链接，支持高德与百度
- 💻 **友好UI界面** - PySide6 图形界面，支持异步处理
- 🔧 **MCP架构** - 可扩展的 Model Context Protocol 服务

## 系统要求

- Python 3.11+
- Claude CLI (需要 Anthropic 账号)
- 高德/百度地图 API Key（可选百度）

## 安装步骤

### 1. 安装 uv 工具

uv 是一个快速的 Python 包管理器，用于替代 pip 和 virtualenv。

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**验证安装:**
```bash
uv --version
```

### 2. 克隆项目并安装依赖

```bash
git clone <repository-url>
cd renyimen
```

**使用 uv 安装依赖:**
```bash
uv sync
```

这会自动创建虚拟环境并安装所有依赖包。

### 3. 安装和配置 Claude CLI

**安装 Claude CLI:**
```bash
npm install -g @anthropic-ai/claude-cli
```

**登录 Claude:**
```bash
claude auth login
```

### 4. 获取地图 API Key（可选）

1. 访问 [高德开放平台](https://console.amap.com/)
2. 注册账号并创建应用
3. 获取 Web 服务 API Key
4. 设置环境变量（推荐）：
   - `AMAP_API_KEY`：高德地图 API Key
   - `BAIDU_MAP_AK`：百度地图 AK（访问百度开放平台获取）
   
   如果未设置 `BAIDU_MAP_AK`，也可使用百度地图，但将退化为仅用名称进行导航（不解析坐标）。

### 5. 运行应用

**激活虚拟环境并运行:**
```bash
uv run python main.py
```

或者

```bash
source .venv/bin/activate  # Linux/macOS
# .venv\\Scripts\\activate  # Windows
python main.py
```

## 使用方法

### 文字输入方式

1. 启动应用后，在输入框中输入导航需求
2. 支持的格式：
   - "从上海新天地到中友嘉园"
   - "去天安门"
   - "导航到北京大学"
   - "开车从A到B"
3. 点击确定或按回车键
4. 系统会自动解析并打开浏览器显示导航路线

### 语音输入方式 🎤

1. 点击"🎤 语音"按钮
2. 对着麦克风说出导航指令，支持的格式：
   - "hi,任意门,我想步行去崇明岛"
   - "hi,任意门,我想驾车从张江人工智能岛到虹桥火车站"
   - "hi,任意门,我想打车去浦东机场"
3. 系统会自动识别语音并解析导航需求
4. 识别成功后自动处理导航请求

## 技术架构

### 核心组件

- `main.py` - PySide6 图形界面主程序
- `voice_recognition_service.py` - 语音识别服务
- `mcp_navigation_server.py` - MCP 导航服务器
- `amap_service.py` - 高德地图 API 封装
- `baidu_service.py` - 百度地图 API 封装
- `navigation_service.py` - 导航服务逻辑
- `claude_desktop_config.json` - MCP 服务配置

### 工作流程

1. 用户输入自然语言导航请求
2. 通过 Claude CLI 调用 MCP 导航服务
3. MCP 服务解析起点终点并调用对应地图 API（支持高德/百度）
4. 生成导航 URL 并自动打开浏览器
5. 显示处理结果和状态

## 开发说明

### 项目结构

```
renyimen/
├── main.py                       # 主应用程序
├── voice_recognition_service.py  # 语音识别服务
├── mcp_navigation_server.py      # MCP 服务器
├── amap_service.py               # 高德地图 API
├── baidu_service.py              # 百度地图 API
├── navigation_service.py         # 导航服务
├── claude_desktop_config.json    # MCP 配置
├── pyproject.toml                # 项目配置
├── uv.lock                       # 依赖锁定文件
└── README.md                     # 说明文档
```

### 添加新功能

1. 在 `mcp_navigation_server.py` 中添加新的 MCP 工具
2. 在 `amap_service.py` / `baidu_service.py` 添加新的 API 功能
3. 修改 `main.py` 更新 UI 和交互逻辑

### 调试模式

启用调试模式查看详细日志：
```bash
uv run python main.py --debug
```

## 常见问题

**Q: Claude CLI 提示权限错误？**
A: 应用已配置 `--dangerously-skip-permissions` 参数，如仍有问题请检查 MCP 配置。

**Q: 高德/百度地图 API 调用失败？**
A: 请检查 API Key 是否正确，以及是否有调用配额。

**Q: UI 界面无响应？**
**使用百度地图**：
- 在界面输入框右侧选择下拉框中的“百度”，会设置 `MAP_PROVIDER=baidu`，MCP 导航服务会根据该变量切换到百度地图。
- 如果设置了 `BAIDU_MAP_AK`，会尽量解析起终点坐标提高准确性；未设置则以名称直链跳转。

**其他故障排查**：
A: 应用使用异步处理，如果卡死请检查 Claude CLI 是否正常安装。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
