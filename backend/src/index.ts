import express from "express";
import cors from "cors";
import { spawn } from "child_process";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

interface NavigationRequest {
  from: string;
  to: string;
  mode?: "walking" | "driving" | "transit";
  city?: string;
}

interface NavigationResponse {
  success: boolean;
  message?: string;
  route?: any;
  error?: string;
}

function callClaude(prompt: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const claudePath = process.env.CLAUDE_CLI_PATH || "claude";
    const child = spawn(claudePath, ["--message", prompt], {
      env: process.env,
    });

    let output = "";
    let errorOutput = "";

    child.stdout.on("data", (data) => {
      output += data.toString();
    });

    child.stderr.on("data", (data) => {
      errorOutput += data.toString();
    });

    child.on("close", (code) => {
      if (code === 0) {
        resolve(output);
      } else {
        reject(new Error(`Claude CLI exited with code ${code}: ${errorOutput}`));
      }
    });

    child.on("error", (err) => {
      reject(err);
    });
  });
}

function buildPrompt(request: NavigationRequest): string {
  const mode = request.mode || "walking";
  const modeMap = {
    walking: "步行",
    driving: "驾车",
    transit: "公交",
  };

  let prompt = `请帮我规划一条从"${request.from}"到"${request.to}"的${modeMap[mode]}路线。

请使用 Amap MCP 工具完成以下步骤：
1. 使用 geocode 工具将起点"${request.from}"转换为经纬度坐标
2. 使用 geocode 工具将终点"${request.to}"转换为经纬度坐标
3. 使用 route_${mode} 工具规划路线`;

  if (mode === "transit" && request.city) {
    prompt += `\n城市：${request.city}`;
  }

  prompt += `\n\n请以 JSON 格式返回结果，包含：
- origin_location: 起点坐标
- destination_location: 终点坐标
- distance: 距离（米）
- duration: 时长（秒）
- polyline: 路线坐标串
- steps: 详细步骤`;

  return prompt;
}

app.post("/api/navigate", async (req, res) => {
  try {
    const request: NavigationRequest = req.body;

    if (!request.from || !request.to) {
      return res.status(400).json({
        success: false,
        error: "起点和终点不能为空",
      });
    }

    const prompt = buildPrompt(request);
    const claudeResponse = await callClaude(prompt);

    const jsonMatch = claudeResponse.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const route = JSON.parse(jsonMatch[0]);
      return res.json({
        success: true,
        route,
      });
    }

    return res.json({
      success: true,
      message: claudeResponse,
    });
  } catch (error) {
    console.error("Navigation error:", error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "服务器内部错误",
    });
  }
});

app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});
