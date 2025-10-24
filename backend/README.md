# 任意门后端服务

提供 API 接口来调用 Claude CLI 进行导航规划。

## 功能

- 接收前端导航请求
- 调用 Claude CLI
- Claude CLI 通过 MCP 调用高德地图服务
- 返回路线规划结果

## 安装

```bash
npm install
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 配置 Claude CLI 路径（如果不在 PATH 中）
3. 确保 Claude CLI 已配置好 Amap MCP 服务

## 运行

开发模式：
```bash
npm run dev
```

构建：
```bash
npm run build
```

生产运行：
```bash
npm start
```

## API 文档

### POST /api/navigate

规划导航路线

请求体：
```json
{
  "from": "北京天安门",
  "to": "北京西站",
  "mode": "walking",
  "city": "北京"
}
```

参数说明：
- `from` (必需): 起点地址
- `to` (必需): 终点地址
- `mode` (可选): 出行方式，可选值：walking（步行）、driving（驾车）、transit（公交），默认 walking
- `city` (可选): 城市名称，公交模式下必需

响应：
```json
{
  "success": true,
  "route": {
    "origin_location": "116.397428,39.90923",
    "destination_location": "116.322056,39.89491",
    "distance": "6543",
    "duration": "4800",
    "polyline": "...",
    "steps": [...]
  }
}
```

### GET /api/health

健康检查

响应：
```json
{
  "status": "ok"
}
```
