#!/usr/bin/env python3
"""
MCP服务器：高德地图导航服务
提供起点到终点的导航链接生成功能
"""

import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from navigation_service import NavigationService


# 创建MCP服务器实例
server = Server("navigation-server")

# 创建导航服务实例
# 导航服务实例，读取provider_config.json决定默认地图类型
nav_service = NavigationService()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    列出可用的工具
    """
    return [
        types.Tool(
            name="navigate",
            description="根据起点和终点打开地图导航链接（高德/百度），支持多种交通方式",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "地图类型：amap(高德)/baidu(百度)，默认读取配置",
                        "enum": ["amap", "baidu"]
                    },
                    "start_point": {
                        "type": "string",
                        "description": "起点名称，如果为空或'当前位置'则自动获取当前IP定位"
                    },
                    "end_point": {
                        "type": "string", 
                        "description": "终点名称"
                    },
                    "start_city": {
                        "type": "string",
                        "description": "起点城市（可选）"
                    },
                    "end_city": {
                        "type": "string",
                        "description": "终点城市（可选）"
                    },
                    "transport_mode": {
                        "type": "string",
                        "description": "交通方式：driving(驾车)/public_transit(公交)/walking(步行)，默认为driving",
                        "enum": ["driving", "public_transit", "walking"]
                    }
                },
                "required": ["end_point"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """
    处理工具调用
    """
    if name != "navigate":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        raise ValueError("Missing arguments")

    start_point = arguments.get("start_point", "")
    end_point = arguments.get("end_point")
    start_city = arguments.get("start_city")
    end_city = arguments.get("end_city")
    transport_mode = arguments.get("transport_mode")
    provider = arguments.get("provider")

    if not end_point:
        raise ValueError("end_point is required")

    # 如果没有起点或起点为"当前位置"，使用IP定位自动获取
    if not start_point or start_point.strip() in ["", "当前位置", "我的位置", "这里"]:
        start_point = "当前位置"
        start_city = None  # IP定位时不需要指定城市

    # 调用导航服务
    # 如果传入了provider，临时覆盖
    if provider:
        nav_service.provider = provider

    success = nav_service.navigate(start_point, end_point, start_city, end_city, transport_mode)
    
    if success:
        mode_text = f" ({transport_mode})" if transport_mode else ""
        message = f"已成功打开从 {start_point} 到 {end_point} 的导航链接{mode_text}"
    else:
        message = f"打开导航链接失败：从 {start_point} 到 {end_point}"

    return [types.TextContent(type="text", text=message)]


async def main():
    # 使用标准输入输出运行服务器
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="navigation-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
