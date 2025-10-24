# 高德地图 MCP 服务

基于 Model Context Protocol 的高德地图集成服务。

## 功能

- 地理编码：将地址转换为经纬度坐标
- 步行路线规划
- 驾车路线规划
- 公交路线规划

## 安装

```bash
npm install
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 在 [高德开放平台](https://lbs.amap.com/) 申请 API Key
3. 将 API Key 填入 `.env` 文件

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

## Claude CLI 配置

在 Claude CLI 的配置文件中添加此 MCP 服务：

```json
{
  "mcpServers": {
    "amap": {
      "command": "node",
      "args": ["/path/to/amap-mcp/dist/index.js"],
      "env": {
        "AMAP_API_KEY": "your_api_key"
      }
    }
  }
}
```

## API 说明

### geocode
将地址转换为经纬度坐标

参数：
- `address` (必需): 地址
- `city` (可选): 城市名称

### route_walking
规划步行路线

参数：
- `origin` (必需): 起点坐标（经度,纬度）
- `destination` (必需): 终点坐标（经度,纬度）

### route_driving
规划驾车路线

参数：
- `origin` (必需): 起点坐标（经度,纬度）
- `destination` (必需): 终点坐标（经度,纬度）

### route_transit
规划公交路线

参数：
- `origin` (必需): 起点坐标（经度,纬度）
- `destination` (必需): 终点坐标（经度,纬度）
- `city` (必需): 城市名称
