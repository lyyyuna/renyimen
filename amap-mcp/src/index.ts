#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const AMAP_API_KEY = process.env.AMAP_API_KEY;

if (!AMAP_API_KEY) {
  console.error('错误: 未设置 AMAP_API_KEY 环境变量');
  process.exit(1);
}

interface Location {
  longitude: number;
  latitude: number;
}

interface GeocodingResult {
  name: string;
  location: Location;
}

interface RouteStep {
  instruction: string;
  distance: number;
  duration: number;
}

interface Route {
  mode: string;
  distance: number;
  duration: number;
  steps: RouteStep[];
  polyline?: number[][];
}

const server = new Server(
  {
    name: 'amap-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

async function geocode(address: string): Promise<GeocodingResult> {
  try {
    const response = await axios.get('https://restapi.amap.com/v3/geocode/geo', {
      params: {
        key: AMAP_API_KEY,
        address: address,
      },
    });

    if (response.data.status === '1' && response.data.geocodes?.length > 0) {
      const geocode = response.data.geocodes[0];
      const [lng, lat] = geocode.location.split(',').map(parseFloat);
      
      return {
        name: geocode.formatted_address || address,
        location: {
          longitude: lng,
          latitude: lat,
        },
      };
    }

    throw new Error(`地理编码失败: ${address}`);
  } catch (error: any) {
    throw new Error(`地理编码请求失败: ${error.message}`);
  }
}

async function planRoute(
  origin: Location,
  destination: Location,
  mode: string = 'walking'
): Promise<Route> {
  try {
    let endpoint = '';
    let modeParam = '';

    switch (mode) {
      case 'walking':
        endpoint = 'https://restapi.amap.com/v3/direction/walking';
        break;
      case 'driving':
        endpoint = 'https://restapi.amap.com/v3/direction/driving';
        break;
      case 'transit':
        endpoint = 'https://restapi.amap.com/v3/direction/transit/integrated';
        break;
      default:
        endpoint = 'https://restapi.amap.com/v3/direction/walking';
    }

    const response = await axios.get(endpoint, {
      params: {
        key: AMAP_API_KEY,
        origin: `${origin.longitude},${origin.latitude}`,
        destination: `${destination.longitude},${destination.latitude}`,
        city: mode === 'transit' ? '北京' : undefined,
      },
    });

    if (response.data.status !== '1') {
      throw new Error('路线规划失败');
    }

    let routeData;
    if (mode === 'transit') {
      routeData = response.data.route?.transits?.[0];
    } else if (mode === 'driving') {
      routeData = response.data.route?.paths?.[0];
    } else {
      routeData = response.data.route?.paths?.[0];
    }

    if (!routeData) {
      throw new Error('未找到路线');
    }

    const steps: RouteStep[] = (routeData.steps || []).map((step: any) => ({
      instruction: step.instruction || step.walking?.instruction || '',
      distance: parseInt(step.distance || step.walking?.distance || '0'),
      duration: parseInt(step.duration || step.walking?.duration || '0'),
    }));

    return {
      mode,
      distance: parseInt(routeData.distance || '0'),
      duration: parseInt(routeData.duration || '0'),
      steps,
    };
  } catch (error: any) {
    throw new Error(`路线规划请求失败: ${error.message}`);
  }
}

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'geocode',
        description: '将地址转换为经纬度坐标',
        inputSchema: {
          type: 'object',
          properties: {
            address: {
              type: 'string',
              description: '要转换的地址',
            },
          },
          required: ['address'],
        },
      },
      {
        name: 'plan_route',
        description: '规划从起点到终点的路线',
        inputSchema: {
          type: 'object',
          properties: {
            origin: {
              type: 'string',
              description: '起点地址',
            },
            destination: {
              type: 'string',
              description: '终点地址',
            },
            mode: {
              type: 'string',
              description: '出行方式: walking(步行), driving(驾车), transit(公交)',
              enum: ['walking', 'driving', 'transit'],
              default: 'walking',
            },
          },
          required: ['origin', 'destination'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === 'geocode') {
      const result = await geocode(args.address as string);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }

    if (name === 'plan_route') {
      const originGeo = await geocode(args.origin as string);
      const destGeo = await geocode(args.destination as string);
      
      const route = await planRoute(
        originGeo.location,
        destGeo.location,
        (args.mode as string) || 'walking'
      );

      const result = {
        origin: originGeo,
        destination: destGeo,
        routes: [route],
      };

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }

    throw new Error(`未知工具: ${name}`);
  } catch (error: any) {
    return {
      content: [
        {
          type: 'text',
          text: `错误: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('高德地图 MCP 服务已启动');
}

main().catch((error) => {
  console.error('服务启动失败:', error);
  process.exit(1);
});
