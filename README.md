# 任意门智能导航系统

基于 Electron + Claude AI + 高德地图 MCP 的智能导航桌面应用。

## 系统架构

```
┌─────────────────────────┐
│   Electron 应用         │
│  ┌─────────────────┐   │
│  │  渲染进程        │   │
│  │  (Vue 3前端)    │   │
│  │  - 文字输入      │   │
│  │  - 语音输入      │   │
│  │  - 地图展示      │   │
│  └────────┬────────┘   │
│           │ IPC        │
│  ┌────────▼────────┐   │
│  │  主进程          │   │
│  │  - Claude CLI   │   │
│  │    调用          │   │
│  └────────┬────────┘   │
└───────────┼────────────┘
            │ CLI
            ▼
    ┌───────────────┐
    │  Claude CLI   │
    │  + MCP 配置   │
    └───────┬───────┘
            │ MCP Protocol
            ▼
    ┌───────────────┐
    │ 高德地图 MCP   │
    │  - 地理编码    │
    │  - 路线规划    │
    └───────────────┘
```

## 特性

✅ **Electron 桌面应用** - 无需单独启动 backend 服务  
✅ **直接调用 Claude CLI** - 通过主进程调用本地 Claude 命令行  
✅ **基于 MCP 协议** - 零硬编码，灵活扩展  
✅ **智能语音输入** - 支持中文语音识别  
✅ **多种出行方式** - 步行、驾车、公交路线规划  
✅ **高德地图集成** - 实时路线可视化展示  

## 快速开始

### 1. 前置要求

- Node.js >= 18
- 已安装 Claude CLI 工具
- 高德地图 API Key（[申请地址](https://console.amap.com/)）
- Anthropic API Key

### 2. 安装依赖

```bash
# 安装主项目依赖
npm install

# 安装 MCP 服务依赖
cd amap-mcp
npm install
cd ..
```

### 3. 配置环境变量

```bash
# 根目录配置
cp .env.example .env

# MCP 服务配置
cp amap-mcp/.env.example amap-mcp/.env

# 编辑 .env 文件，填入你的 API Keys
```

### 4. 配置 Claude CLI

编辑 Claude CLI 配置文件（通常在 `~/.config/claude/config.json`），添加 MCP 服务：

```json
{
  "mcpServers": {
    "amap": {
      "command": "node",
      "args": ["/absolute/path/to/renyimen/amap-mcp/dist/index.js"],
      "env": {
        "AMAP_API_KEY": "your_amap_api_key"
      }
    }
  }
}
```

**重要：** 将路径替换为实际的绝对路径。

### 5. 构建 MCP 服务

```bash
cd amap-mcp
npm run build
cd ..
```

### 6. 更新高德地图 API Key

编辑 `index.html`，替换 `YOUR_AMAP_KEY` 为你的实际 API Key：

```html
<script type="text/javascript" src="https://webapi.amap.com/maps?v=2.0&key=YOUR_AMAP_KEY"></script>
```

### 7. 启动应用

```bash
# 开发模式（推荐）
npm run electron:dev

# 或分别启动
# 终端1: npm run dev
# 终端2: electron .
```

### 8. 打包应用

```bash
npm run electron:build
```

生成的应用在 `dist-electron/` 目录。

## 使用方法

### 文字输入

1. 在输入框输入导航需求，例如：
   - "从天安门到西单"
   - "从北京站到颐和园"
   - "从国贸到三里屯"

2. 选择出行方式（步行/驾车/公交）

3. 点击"导航"按钮

### 语音输入

1. 点击"🎤 语音输入"按钮

2. 允许浏览器使用麦克风权限

3. 说出导航需求，格式：
   - "从天安门到西单"
   - "从北京站到颐和园"

4. 语音识别完成后自动填入输入框

5. 选择出行方式并提交

## 技术栈

### 主应用
- **Electron** - 桌面应用框架
- **Vue 3** - 前端框架
- **Vite** - 构建工具
- **高德地图 JS API** - 地图展示

### MCP 服务
- **TypeScript** - 类型安全
- **@modelcontextprotocol/sdk** - MCP 协议实现
- **高德地图 Web 服务 API** - 地理编码和路线规划

### AI 集成
- **Claude CLI** - 本地命令行工具
- **Model Context Protocol** - AI 工具调用协议

## 项目结构

```
renyimen/
├── electron/              # Electron 主进程
│   ├── main.js           # 主进程入口
│   └── preload.js        # 预加载脚本
├── src/                  # Vue 前端源码
│   ├── App.vue           # 主组件
│   └── main.js           # 前端入口
├── amap-mcp/             # 高德地图 MCP 服务
│   ├── src/
│   │   └── index.ts      # MCP 服务实现
│   ├── package.json
│   └── tsconfig.json
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
├── package.json          # 主项目配置
└── README.md             # 本文档
```

## 工作原理

1. **用户输入** - 通过文字或语音输入导航需求

2. **IPC 通信** - 渲染进程通过 IPC 将请求发送到主进程

3. **调用 Claude CLI** - 主进程调用本地 Claude CLI，传入构建好的 prompt

4. **MCP 工具调用** - Claude 理解需求后，自动调用高德地图 MCP 工具：
   - `geocode` - 将起点和终点地址转换为经纬度
   - `plan_route` - 规划路线

5. **返回结果** - MCP 服务返回路线信息给 Claude，Claude 处理后返回 JSON 格式

6. **可视化展示** - 前端接收结果，在高德地图上展示路线

## 语音输入方案

### 当前方案：Web Speech API

- ✅ 无需额外配置
- ✅ 浏览器原生支持
- ⚠️ 需要 Chrome 浏览器
- ⚠️ 需要网络连接
- ⚠️ 识别准确度中等

### 生产环境推荐方案

详见 `docs/voice-input-solutions.md`，推荐方案包括：

1. **讯飞语音听写** ⭐⭐⭐⭐⭐
   - 中文识别准确度高
   - 提供 WebSocket 和 HTTP API
   - 适合国内项目

2. **百度语音识别**
   - 稳定可靠
   - 文档完善

3. **Azure Speech Services**
   - 国际化项目首选

## 常见问题

### Q: Claude CLI 调用失败？

A: 检查以下几点：
1. 确认已安装 Claude CLI 并可在命令行中运行
2. 检查 ANTHROPIC_API_KEY 是否正确配置
3. 确认 MCP 服务路径配置正确
4. 查看 Electron 开发者工具的控制台输出

### Q: 地图不显示？

A: 
1. 检查 index.html 中的高德地图 API Key 是否正确
2. 确认网络连接正常
3. 打开浏览器开发者工具查看错误信息

### Q: 语音输入不工作？

A:
1. 确认使用 Chrome 浏览器
2. 检查麦克风权限是否授予
3. 确认网络连接（Web Speech API 需要联网）

### Q: MCP 服务无响应？

A:
1. 确认 amap-mcp 已执行 `npm run build`
2. 检查 .env 文件中的 AMAP_API_KEY 是否正确
3. 查看 Claude CLI 配置文件中的 MCP 路径是否为绝对路径

## 开发指南

### 调试主进程

```bash
# 启动时添加调试参数
electron --inspect=5858 .
```

然后在 Chrome 中打开 `chrome://inspect` 进行调试。

### 调试渲染进程

开发模式下会自动打开 DevTools，或在应用中按 `Ctrl+Shift+I`（macOS: `Cmd+Option+I`）。

### 修改 MCP 服务

```bash
cd amap-mcp
# 修改 src/index.ts
npm run build
# 重启 Electron 应用
```

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！
