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

ipcMain.handle('call-claude', async (event, userInput) => {
  return new Promise((resolve, reject) => {
    const prompt = `用户需要导航服务。请使用高德地图MCP工具来处理以下请求：

"${userInput}"

请调用MCP工具获取路线信息，并返回JSON格式的结果，包含：
- origin: 起点信息（包含name和location）
- destination: 终点信息（包含name和location）
- routes: 路线数组（每条路线包含mode、distance、duration、steps等信息）

确保返回格式严格遵循JSON标准。`;

    const claudeProcess = spawn('claude', ['-p', prompt], {
      env: {
        ...process.env,
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY
      }
    });

    let output = '';
    let errorOutput = '';

    claudeProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    claudeProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    claudeProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Claude CLI failed: ${errorOutput}`));
        return;
      }

      try {
        const jsonMatch = output.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const result = JSON.parse(jsonMatch[0]);
          resolve(result);
        } else {
          resolve({ output, raw: true });
        }
      } catch (error) {
        resolve({ output, raw: true });
      }
    });

    claudeProcess.on('error', (error) => {
      reject(new Error(`Failed to start Claude CLI: ${error.message}`));
    });
  });
});
