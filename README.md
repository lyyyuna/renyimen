# 任意门 (Renyimen)

🚪 基于 AI 的智能导航系统,通过文字或语音输入,自动规划从 A 到 B 的路线。

## 项目简介

任意门是一个创新的导航应用,结合了 Claude AI、MCP（Model Context Protocol）和高德地图,为用户提供智能化的导航体验。

### 核心特性

- 🗣️ **智能输入**：支持文字输入和语音输入
- 🗺️ **多种出行方式**：步行、驾车、公交路线规划
- 🤖 **AI 驱动**：基于 Claude AI 理解用户意图
- 🔌 **MCP 架构**：不硬编码,灵活扩展
- 📍 **高德地图**：准确的路线规划和地图展示

## 系统架构

```
┌─────────────────┐
│   前端界面       │  (Vue 3 + 高德地图 JS API)
│  - 文字输入      │
│  - 语音输入      │
│  - 地图显示      │
└────────┬────────┘
         │ HTTP API
         ▼
┌─────────────────┐
│  后端服务        │  (Node.js + Express)
│  - 请求处理      │
│  - CLI 调用      │
└────────┬────────┘
         │ CLI
         ▼
┌─────────────────┐
│  Claude CLI      │  (本地命令行工具)
│  - MCP 配置      │
│  - AI 理解       │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│  高德 MCP 服务   │  (TypeScript)
│  - 地理编码      │
│  - 路径规划      │
│  - API 调用      │
└─────────────────┘
```

## 项目结构

```
renyimen/
├── amap-mcp/           # 高德地图 MCP 服务
│   ├── src/
│   │   └── index.ts    # MCP 服务器实现
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
│
├── backend/            # 后端服务
│   ├── src/
│   │   └── index.ts    # Express 服务器
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
│
├── frontend/           # 前端界面
│   ├── src/
│   │   ├── App.vue     # 主组件
│   │   └── main.ts     # 入口文件
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
│
├── docs/               # 文档
│   └── voice-input-solutions.md  # 语音输入方案调研
│
└── README.md           # 项目说明
```

## 快速开始

### 前置要求

- Node.js 18+
- Claude CLI（已安装并配置）
- 高德地图 API Key（[申请地址](https://lbs.amap.com/)）

### 1. 安装依赖

```bash
# 安装 MCP 服务依赖
cd amap-mcp
npm install
cd ..

# 安装后端依赖
cd backend
npm install
cd ..

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 2. 配置环境变量

#### 高德 MCP 服务
```bash
cd amap-mcp
cp .env.example .env
# 编辑 .env 文件,填入高德地图 API Key
```

#### 后端服务
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件,配置 Claude CLI 路径（如需要）
```

#### 前端
```bash
cd frontend
cp .env.example .env
# 编辑 .env 文件,填入高德地图 Web 端 Key
```

### 3. 配置 Claude CLI

在 Claude CLI 的配置文件中添加 MCP 服务：

```json
{
  "mcpServers": {
    "amap": {
      "command": "node",
      "args": ["/path/to/renyimen/amap-mcp/dist/index.js"],
      "env": {
        "AMAP_API_KEY": "your_api_key"
      }
    }
  }
}
```

### 4. 运行服务

#### 启动 MCP 服务
```bash
cd amap-mcp
npm run build
npm start
```

#### 启动后端服务
```bash
cd backend
npm run dev
```

#### 启动前端
```bash
cd frontend
npm run dev
```

访问 `http://localhost:5173` 即可使用。

## 使用说明

### 文字输入

1. 在"起点"输入框输入起始地址
2. 在"终点"输入框输入目的地地址
3. 选择出行方式（步行/驾车/公交）
4. 点击"开始导航"按钮

### 语音输入

1. 点击"🎤 语音输入"按钮
2. 授权麦克风权限（首次使用）
3. 说出导航需求,格式：**"从[起点]到[终点]"**
   - 例如："从天安门到西单"
   - 例如："从北京站到鸟巢"
4. 系统自动识别并填入起点和终点

> **注意**：语音输入需要使用 Chrome 浏览器,且需要在 HTTPS 或 localhost 环境下使用。

## 开发指南

### MCP 服务开发

MCP 服务负责与高德地图 API 交互,提供以下工具：

- `geocode`: 地址转坐标
- `route_walking`: 步行路线规划
- `route_driving`: 驾车路线规划
- `route_transit`: 公交路线规划

详见 [amap-mcp/README.md](amap-mcp/README.md)

### 后端服务开发

后端服务提供 HTTP API,调用 Claude CLI 处理用户请求。

API 文档见 [backend/README.md](backend/README.md)

### 前端开发

基于 Vue 3 + Vite,使用高德地图 JS API 展示地图和路线。

开发说明见 [frontend/README.md](frontend/README.md)

## 语音输入方案

当前使用 Web Speech API 实现语音输入。如需更高的识别准确度,建议使用专业的语音识别服务：

- 讯飞语音听写（推荐）
- 百度语音识别
- 阿里云智能语音
- 腾讯云语音识别

详细方案对比见 [docs/voice-input-solutions.md](docs/voice-input-solutions.md)

## 技术栈

### 前端
- Vue 3
- TypeScript
- Vite
- 高德地图 JS API

### 后端
- Node.js
- Express
- TypeScript

### MCP 服务
- @modelcontextprotocol/sdk
- TypeScript
- Axios

## 常见问题

### Q: 语音输入无法使用？
A: 请确保：
1. 使用 Chrome 浏览器
2. 在 HTTPS 或 localhost 环境
3. 已授权麦克风权限

### Q: 无法规划路线？
A: 请检查：
1. 高德地图 API Key 是否正确配置
2. 后端服务是否正常运行
3. Claude CLI 是否正确配置 MCP 服务
4. 网络连接是否正常

### Q: MCP 服务无法启动？
A: 请确认：
1. Node.js 版本是否 18+
2. 依赖是否正确安装
3. API Key 是否有效

## 路线图

- [x] 基础导航功能
- [x] 文字输入
- [x] 语音输入（Web Speech API）
- [ ] 集成专业语音识别服务
- [ ] 历史记录保存
- [ ] 收藏地点功能
- [ ] 实时路况信息
- [ ] 多地点路线规划
- [ ] 移动端适配

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 联系方式

如有问题或建议,请提交 Issue。
