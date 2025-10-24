# 任意门智能导航系统

基于 Electron + Vue 3 + Claude AI + 高德地图的智能导航桌面应用。

## 特性

- 🖥️ **Electron 桌面应用** - 跨平台桌面应用，支持 Windows、macOS、Linux
- 🎤 **智能语音输入** - 支持中文语音识别（基于 Web Speech API）
- 💬 **自然语言理解** - 通过 Claude AI 理解自然语言导航需求
- 🗺️ **高德地图集成** - 实时路线规划和可视化展示
- 🚶 **多种出行方式** - 支持步行、驾车、公交路线规划
- ⚡ **简单架构** - 无需单独部署后端服务

## 技术栈

### 前端
- **Electron** - 桌面应用框架
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **高德地图 JS API 2.0** - 地图展示和路线规划

### 后端
- **Claude CLI** - Anthropic 官方命令行工具
- **Node.js** - JavaScript 运行时

## 项目结构

```
renyimen/
├── electron/              # Electron 主进程代码
│   ├── main.js           # 主进程入口，处理窗口创建和 Claude CLI 调用
│   └── preload.js        # 预加载脚本，暴露安全的 IPC 接口
├── src/                  # Vue 前端源码
│   ├── App.vue           # 主组件，包含 UI 和地图逻辑
│   └── main.js           # 前端入口
├── docs/                 # 文档目录
│   └── voice-input-solutions.md  # 语音输入方案调研
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
├── package.json          # 项目依赖配置
├── .env.example          # 环境变量示例
└── README.md             # 项目文档
```

## 系统架构

```
┌─────────────────────────────────┐
│      Electron 应用              │
│  ┌─────────────────────────┐   │
│  │   渲染进程 (Vue 3)      │   │
│  │  ┌──────────────────┐   │   │
│  │  │  用户界面        │   │   │
│  │  │  - 文字输入      │   │   │
│  │  │  - 语音输入      │   │   │
│  │  │  - 出行方式选择  │   │   │
│  │  │  - 地图展示      │   │   │
│  │  └──────────────────┘   │   │
│  └──────────┬──────────────┘   │
│             │ IPC 通信          │
│  ┌──────────▼──────────────┐   │
│  │   主进程 (main.js)      │   │
│  │  - 窗口管理              │   │
│  │  - 调用 Claude CLI      │   │
│  │  - 解析返回结果          │   │
│  └──────────┬──────────────┘   │
└─────────────┼──────────────────┘
              │ spawn
              ▼
      ┌───────────────┐
      │  Claude CLI   │
      │  + MCP 配置   │
      └───────────────┘
```

## 快速开始

### 前置要求

- **Node.js** >= 18
- **Claude CLI** - [安装指南](https://docs.anthropic.com/claude/docs/claude-cli)
- **Anthropic API Key** - [获取地址](https://console.anthropic.com/)
- **高德地图 API Key** - [申请地址](https://console.amap.com/)

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/lyyyuna/renyimen.git
cd renyimen
```

#### 2. 安装依赖

```bash
npm install
```

#### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Keys：

```env
AMAP_API_KEY=your_amap_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

#### 4. 配置高德地图密钥

编辑 `index.html`，替换高德地图 API Key 和安全密钥：

```html
<script type="text/javascript">
  window._AMapSecurityConfig = {
    securityJsCode: 'YOUR_SECURITY_KEY'  // 替换为你的安全密钥
  }
</script>
<script type="text/javascript" src="https://webapi.amap.com/maps?v=2.0&key=YOUR_AMAP_KEY"></script>
```

#### 5. 配置 Claude CLI（可选）

如果需要使用高德地图 MCP 服务，编辑 Claude CLI 配置文件（`~/.config/claude/config.json`）：

```json
{
  "mcpServers": {
    "amap": {
      "command": "node",
      "args": ["/path/to/your/amap-mcp/server.js"],
      "env": {
        "AMAP_API_KEY": "your_amap_api_key"
      }
    }
  }
}
```

### 运行应用

#### 开发模式

```bash
npm run electron:dev
```

该命令会：
1. 启动 Vite 开发服务器（端口 5173）
2. 自动打开 Electron 窗口
3. 启用热重载

#### 生产模式

```bash
# 构建前端资源
npm run build

# 打包 Electron 应用
npm run electron:build
```

打包后的应用位于 `dist-electron/` 目录。

## 使用指南

### 文字输入导航

1. 在输入框中输入导航需求，例如：
   - "从天安门到西单"
   - "从北京站到颐和园"
   - "从国贸到三里屯"

2. 选择出行方式：
   - 🚶 步行
   - 🚗 驾车
   - 🚌 公交

3. 点击"导航"按钮

### 语音输入导航

1. 点击"🎤 语音输入"按钮

2. 允许浏览器使用麦克风权限

3. 清晰地说出导航需求：
   - "从天安门到西单"
   - "从北京站到颐和园"

4. 语音识别完成后，内容会自动填入输入框

5. 选择出行方式并点击"导航"

### 查看路线信息

导航成功后，页面会显示：
- 起点和终点名称
- 路线距离
- 预计时间
- 地图上的可视化路线

## 工作原理

1. **用户输入** - 用户通过文字或语音输入导航需求
2. **IPC 通信** - 渲染进程通过 Electron IPC 将请求发送到主进程
3. **调用 Claude** - 主进程调用本地 Claude CLI，传入用户需求和选择的出行方式
4. **AI 理解** - Claude 理解自然语言，提取起点、终点信息
5. **返回结果** - Claude 返回 JSON 格式的路线信息
6. **解析展示** - 主进程解析结果，发送回渲染进程
7. **地图渲染** - Vue 组件在高德地图上绘制路线

## 开发指南

### 调试主进程

```bash
electron --inspect=5858 .
```

然后在 Chrome 浏览器访问 `chrome://inspect` 进行调试。

### 调试渲染进程

开发模式会自动打开 DevTools，或在应用中按：
- **Windows/Linux**: `Ctrl + Shift + I`
- **macOS**: `Cmd + Option + I`

### 修改前端代码

编辑 `src/App.vue`，Vite 会自动热重载。

### 修改主进程代码

编辑 `electron/main.js`，需要重启 Electron 应用才能生效。

## 语音识别方案

### 当前方案：Web Speech API

- ✅ 浏览器原生支持，无需额外配置
- ✅ 免费使用
- ⚠️ 需要 Chrome/Edge 浏览器
- ⚠️ 需要网络连接
- ⚠️ 中文识别准确度中等

### 生产环境推荐

详见 [`docs/voice-input-solutions.md`](docs/voice-input-solutions.md)，推荐方案：

1. **讯飞语音听写** ⭐⭐⭐⭐⭐
   - 中文识别准确度高
   - 延迟低，适合实时应用
   - 免费额度充足

2. **百度语音识别** ⭐⭐⭐⭐
   - 稳定可靠
   - 文档完善

3. **Azure Speech Services** ⭐⭐⭐
   - 国际化支持好
   - 多语言支持

## 常见问题

### Claude CLI 调用失败？

**解决方法：**
1. 确认已安装 Claude CLI：`claude --version`
2. 检查 `ANTHROPIC_API_KEY` 是否配置正确
3. 查看 Electron 开发者工具的控制台输出
4. 检查网络连接是否正常

### 地图无法显示？

**解决方法：**
1. 检查 `index.html` 中的高德地图 API Key 是否正确
2. 确认安全密钥 `securityJsCode` 已配置
3. 打开浏览器开发者工具查看控制台错误
4. 确认网络连接正常

### 语音输入无响应？

**解决方法：**
1. 确认使用 Chrome 或 Edge 浏览器（Electron 默认使用 Chromium）
2. 检查麦克风权限是否已授予
3. 确认网络连接（Web Speech API 需要联网）
4. 尝试在系统设置中检查麦克风是否正常工作

### 路线规划失败？

**解决方法：**
1. 确保输入格式正确："从 起点 到 终点"
2. 使用具体的地点名称，避免模糊描述
3. 检查高德地图 API Key 配额是否充足
4. 查看控制台错误信息

## 打包发布

### Windows

```bash
npm run electron:build
```

生成的安装包：`dist-electron/renyimen-Setup-1.0.0.exe`

### macOS

```bash
npm run electron:build
```

生成的应用：`dist-electron/renyimen-1.0.0.dmg`

### Linux

```bash
npm run electron:build
```

生成的应用：`dist-electron/renyimen-1.0.0.AppImage`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

## 致谢

- [Anthropic Claude](https://www.anthropic.com/) - 强大的 AI 能力
- [高德地图](https://lbs.amap.com/) - 地图和路线规划服务
- [Electron](https://www.electronjs.org/) - 跨平台桌面应用框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
