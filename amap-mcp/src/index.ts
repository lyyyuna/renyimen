import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";

const AMAP_API_KEY = process.env.AMAP_API_KEY || "";

interface GeoCodeResult {
  formatted_address: string;
  location: string;
}

interface RouteResult {
  distance: string;
  duration: string;
  steps: any[];
  polyline: string;
}

const server = new Server(
  {
    name: "amap-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "geocode",
        description: "将地址转换为经纬度坐标",
        inputSchema: {
          type: "object",
          properties: {
            address: {
              type: "string",
              description: "要查询的地址",
            },
            city: {
              type: "string",
              description: "城市名称（可选）",
            },
          },
          required: ["address"],
        },
      },
      {
        name: "route_walking",
        description: "规划步行路线",
        inputSchema: {
          type: "object",
          properties: {
            origin: {
              type: "string",
              description: "起点坐标，格式：经度,纬度",
            },
            destination: {
              type: "string",
              description: "终点坐标，格式：经度,纬度",
            },
          },
          required: ["origin", "destination"],
        },
      },
      {
        name: "route_driving",
        description: "规划驾车路线",
        inputSchema: {
          type: "object",
          properties: {
            origin: {
              type: "string",
              description: "起点坐标，格式：经度,纬度",
            },
            destination: {
              type: "string",
              description: "终点坐标，格式：经度,纬度",
            },
          },
          required: ["origin", "destination"],
        },
      },
      {
        name: "route_transit",
        description: "规划公交路线",
        inputSchema: {
          type: "object",
          properties: {
            origin: {
              type: "string",
              description: "起点坐标，格式：经度,纬度",
            },
            destination: {
              type: "string",
              description: "终点坐标，格式：经度,纬度",
            },
            city: {
              type: "string",
              description: "城市名称",
            },
          },
          required: ["origin", "destination", "city"],
        },
      },
    ],
  };
});

async function geocode(address: string, city?: string): Promise<GeoCodeResult> {
  const params: any = {
    key: AMAP_API_KEY,
    address: address,
  };
  if (city) {
    params.city = city;
  }

  const response = await axios.get("https://restapi.amap.com/v3/geocode/geo", {
    params,
  });

  if (response.data.status === "1" && response.data.geocodes.length > 0) {
    const result = response.data.geocodes[0];
    return {
      formatted_address: result.formatted_address,
      location: result.location,
    };
  }
  throw new Error(`地理编码失败: ${response.data.info}`);
}

async function routeWalking(origin: string, destination: string): Promise<RouteResult> {
  const response = await axios.get("https://restapi.amap.com/v3/direction/walking", {
    params: {
      key: AMAP_API_KEY,
      origin,
      destination,
    },
  });

  if (response.data.status === "1" && response.data.route) {
    const path = response.data.route.paths[0];
    return {
      distance: path.distance,
      duration: path.duration,
      steps: path.steps,
      polyline: path.steps.map((s: any) => s.polyline).join(";"),
    };
  }
  throw new Error(`步行路线规划失败: ${response.data.info}`);
}

async function routeDriving(origin: string, destination: string): Promise<RouteResult> {
  const response = await axios.get("https://restapi.amap.com/v3/direction/driving", {
    params: {
      key: AMAP_API_KEY,
      origin,
      destination,
    },
  });

  if (response.data.status === "1" && response.data.route) {
    const path = response.data.route.paths[0];
    return {
      distance: path.distance,
      duration: path.duration,
      steps: path.steps,
      polyline: path.steps.map((s: any) => s.polyline).join(";"),
    };
  }
  throw new Error(`驾车路线规划失败: ${response.data.info}`);
}

async function routeTransit(origin: string, destination: string, city: string): Promise<any> {
  const response = await axios.get("https://restapi.amap.com/v3/direction/transit/integrated", {
    params: {
      key: AMAP_API_KEY,
      origin,
      destination,
      city,
    },
  });

  if (response.data.status === "1" && response.data.route) {
    return response.data.route.transits[0];
  }
  throw new Error(`公交路线规划失败: ${response.data.info}`);
}

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "geocode": {
        const result = await geocode(args.address as string, args.city as string);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "route_walking": {
        const result = await routeWalking(
          args.origin as string,
          args.destination as string
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "route_driving": {
        const result = await routeDriving(
          args.origin as string,
          args.destination as string
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "route_transit": {
        const result = await routeTransit(
          args.origin as string,
          args.destination as string,
          args.city as string
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: "text",
          text: `Error: ${errorMessage}`,
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Amap MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
