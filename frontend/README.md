# 任意门前端

基于 Vue 3 + Vite 的智能导航前端界面。

## 功能

- 文字输入起点和终点
- 语音输入支持（基于 Web Speech API）
- 高德地图显示
- 路线展示
- 支持步行、驾车、公交三种出行方式

## 安装

```bash
npm install
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 在 [高德开放平台](https://lbs.amap.com/) 申请 Web 端 Key
3. 将 Key 填入 `.env` 文件的 `VITE_AMAP_KEY`

## 运行

开发模式：
```bash
npm run dev
```

构建：
```bash
npm run build
```

预览构建结果：
```bash
npm run preview
```

## 语音输入说明

语音输入功能基于浏览器的 Web Speech API 实现：

- **浏览器支持**：Chrome、Edge（基于 Chromium）
- **输入格式**：说"从[起点]到[终点]"，例如"从天安门到西单"
- **注意事项**：
  - 需要 HTTPS 或 localhost 环境
  - 首次使用需要授权麦克风权限
  - 语音识别准确度受环境噪音影响

### 其他语音输入方案

如需更好的语音识别效果，可考虑集成：

1. **讯飞语音听写**：国内语音识别服务，中文识别准确度高
2. **百度语音识别**：提供 Web API 和 SDK
3. **阿里云智能语音**：企业级语音服务
4. **腾讯云语音识别**：支持实时语音识别

这些方案需要申请相应的 API Key 并修改前端代码。

## 依赖项

- Vue 3：前端框架
- Vite：构建工具
- @amap/amap-jsapi-loader：高德地图 JS API 加载器

## 开发说明

确保后端服务运行在 `http://localhost:3000`，如需修改后端地址，请在 `src/App.vue` 中修改 API 请求地址。
