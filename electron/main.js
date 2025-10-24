import { app, BrowserWindow, ipcMain } from 'electron';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 解析 Claude 文本回复中的路线信息
function parseRouteFromText(text) {
  try {
    console.log('🔍 [parseRouteFromText] 解析文本:', text.substring(0, 200) + '...');
    
    // 检查是否包含路线相关关键词
    if (!text.includes('距离') && !text.includes('时间') && !text.includes('路线')) {
      return null;
    }
    
    // 提取距离信息 (支持米和公里)
    let distance = 0;
    const distanceMatches = text.match(/距离[：:]\s*(\d+(?:\.\d+)?)\s*(米|公里|km)/i);
    if (distanceMatches) {
      const value = parseFloat(distanceMatches[1]);
      const unit = distanceMatches[2];
      distance = (unit === '公里' || unit === 'km') ? value * 1000 : value;
    }
    
    // 提取时间信息 (支持分钟和小时)
    let duration = 0;
    const durationMatches = text.match(/时间[：:]\s*(\d+)\s*(分钟|小时)/i);
    if (durationMatches) {
      const value = parseInt(durationMatches[1]);
      const unit = durationMatches[2];
      duration = unit === '小时' ? value * 3600 : value * 60;
    }
    
    // 提取起点和终点
    const fromMatch = text.match(/从\s*([^\s，,到]+)/);
    const toMatch = text.match(/到\s*([^\s，,]+)/);
    
    const origin = fromMatch ? fromMatch[1] : '起点';
    const destination = toMatch ? toMatch[1] : '终点';
    
    // 构造前端期望的格式
    const originCoord = [116.397428, 39.90923]; // 默认坐标 (天安门)
    const destCoord = [116.327586, 39.913423];   // 默认坐标 (西单)
    
    const result = {
      origin: {
        name: origin,
        location: {
          longitude: originCoord[0],
          latitude: originCoord[1]
        }
      },
      destination: {
        name: destination,
        location: {
          longitude: destCoord[0],
          latitude: destCoord[1]
        }
      },
      routes: [{
        mode: 'walking',
        distance: distance,
        duration: duration,
        steps: [],
        polyline: [
          originCoord,
          destCoord
        ]
      }]
    };
    
    console.log('✅ [parseRouteFromText] 解析结果:', result);
    return result;
    
  } catch (error) {
    console.log('❌ [parseRouteFromText] 解析失败:', error.message);
    return null;
  }
}

ipcMain.handle('call-claude', async (event, userInput) => {
  console.log('🚀 [call-claude] 开始处理请求:', userInput);
  
  return new Promise((resolve, reject) => {
    // 解析用户输入，提取起点和终点
    const prompt = `你是一个智能导航助手。用户输入：${userInput}

请分析用户的导航需求，并执行以下步骤：
1. 识别起点和终点位置（如果用户说"从A到B"，A是起点，B是终点）
2. 根据用户指定的出行方式（步行、驾车、公交）调用高德地图MCP服务
3. 使用 plan_route 工具规划路线
4. 最后，将路线规划结果以JSON格式返回，格式如下：

{
  "origin": {
    "name": "起点名称",
    "location": {"longitude": 经度, "latitude": 纬度}
  },
  "destination": {
    "name": "终点名称", 
    "location": {"longitude": 经度, "latitude": 纬度}
  },
  "routes": [{
    "mode": "walking/driving/transit",
    "distance": 距离(米),
    "duration": 时间(秒),
    "steps": [详细步骤],
    "polyline": [[经度,纬度]坐标数组]
  }]
}

如果MCP服务调用失败，请以友好的方式说明距离和预计时间，格式为：
"从[起点]到[终点]，预计距离：X公里，预计时间：X分钟"

可用的出行方式：
- walking（步行）- 默认方式
- driving（驾车）
- transit（公交）

请立即开始处理这个导航请求。`;

    console.log('📝 [call-claude] 构建的 prompt:', prompt.substring(0, 100) + '...');
    
    // 使用 shell 执行，配置高德官方 MCP 服务
    const escapedPrompt = prompt.replace(/"/g, '\\"');
    const mcpConfig = JSON.stringify({
      mcpServers: {
        "amap": {
          "command": "npx",
          "args": ["-y", "@amap/amap-maps-mcp-server"],
          "env": {
            "AMAP_MAPS_API_KEY": "c1e4a95a52e7937bc4bece908648ea7e"
          }
        }
      }
    });
    const escapedMcpConfig = mcpConfig.replace(/"/g, '\\"');
    const command = `/usr/local/bin/claude -p "${escapedPrompt}" --mcp-config "${escapedMcpConfig}"`;
    console.log('⚙️ [call-claude] Claude CLI 命令:', command);
    
    // 使用继承的环境变量，让 Claude CLI 使用已配置的认证
    const claudeProcess = spawn('sh', ['-c', command], {
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: false,
      detached: false
    });

    let output = '';
    let errorOutput = '';
    
    console.log('🔄 [call-claude] Claude 进程已启动, PID:', claudeProcess.pid);
    
    // 立即检查进程状态
    setTimeout(() => {
      console.log('🔍 [call-claude] 进程状态检查 (2秒后):', claudeProcess.killed ? '已终止' : '运行中');
    }, 2000);

    claudeProcess.stdout.on('data', (data) => {
      const chunk = data.toString();
      console.log('📤 [call-claude] Claude stdout:', chunk.substring(0, 200));
      output += chunk;
    });

    claudeProcess.stderr.on('data', (data) => {
      const chunk = data.toString();
      console.log('❌ [call-claude] Claude stderr:', chunk);
      errorOutput += chunk;
    });

    claudeProcess.on('close', (code) => {
      console.log('🏁 [call-claude] Claude 进程结束, 退出码:', code);
      console.log('📋 [call-claude] 完整输出长度:', output.length);
      console.log('📋 [call-claude] 完整错误输出:', errorOutput);
      
      if (code !== 0) {
        console.log('💥 [call-claude] Claude CLI 执行失败');
        reject(new Error(`Claude CLI failed: ${errorOutput}`));
        return;
      }

      try {
        console.log('🔍 [call-claude] 尝试解析 JSON...');
        const jsonMatch = output.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          console.log('✅ [call-claude] 找到 JSON 格式输出');
          const result = JSON.parse(jsonMatch[0]);
          console.log('🎉 [call-claude] JSON 解析成功:', Object.keys(result));
          resolve(result);
        } else {
          console.log('⚠️ [call-claude] 未找到 JSON 格式，尝试解析 MCP 工具调用结果...');
          
          // 尝试从文本中提取路线信息
          const routeResult = parseRouteFromText(output);
          if (routeResult) {
            console.log('✅ [call-claude] 成功解析导航结果');
            resolve(routeResult);
          } else {
            console.log('⚠️ [call-claude] 无法解析导航结果，返回原始输出');
            resolve({ output, raw: true });
          }
        }
      } catch (error) {
        console.log('❌ [call-claude] JSON 解析失败:', error.message);
        resolve({ output, raw: true });
      }
    });

    claudeProcess.on('error', (error) => {
      console.log('💥 [call-claude] 进程启动失败:', error.message);
      reject(new Error(`Failed to start Claude CLI: ${error.message}`));
    });
    
    // 添加超时处理 - 30秒应该足够
    const timeoutHandle = setTimeout(() => {
      if (!claudeProcess.killed) {
        console.log('⏰ [call-claude] 进程超时，强制终止');
        claudeProcess.kill('SIGTERM');
        reject(new Error('Claude CLI 调用超时 (30秒)'));
      }
    }, 90000);
    
    // 在进程结束时清理定时器
    claudeProcess.on('close', () => {
      clearTimeout(timeoutHandle);
    });
  });
});
