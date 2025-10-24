# 语音输入方案调研

本文档详细对比了多种语音识别方案，为任意门导航系统提供参考。

## 方案对比

| 方案 | 优点 | 缺点 | 中文支持 | 成本 | 推荐指数 |
|------|------|------|----------|------|----------|
| Web Speech API | 免费，无需配置 | 需要网络，准确度一般 | ⭐⭐⭐ | 免费 | ⭐⭐⭐ |
| 讯飞语音听写 | 准确度高，专为中文优化 | 需要注册申请 | ⭐⭐⭐⭐⭐ | 按量付费 | ⭐⭐⭐⭐⭐ |
| 百度语音识别 | 稳定可靠，文档完善 | 需要注册 | ⭐⭐⭐⭐ | 按量付费 | ⭐⭐⭐⭐ |
| 阿里云智能语音 | 阿里云生态整合好 | 需要阿里云账号 | ⭐⭐⭐⭐ | 按量付费 | ⭐⭐⭐⭐ |
| 腾讯云语音识别 | 腾讯云生态 | 需要腾讯云账号 | ⭐⭐⭐⭐ | 按量付费 | ⭐⭐⭐⭐ |
| Azure Speech | 国际化支持好 | 国内访问可能慢 | ⭐⭐⭐⭐ | 按量付费 | ⭐⭐⭐ |

## 详细方案

### 1. Web Speech API（当前方案）

**优点：**
- 浏览器原生支持，无需额外配置
- 免费使用
- 实现简单

**缺点：**
- 仅支持 Chrome 浏览器
- 需要网络连接
- 中文识别准确度一般
- 无法离线使用

**实现示例：**
```javascript
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'zh-CN';
recognition.continuous = false;

recognition.onresult = (event) => {
  const transcript = event.results[0][0].transcript;
  console.log('识别结果:', transcript);
};

recognition.start();
```

### 2. 讯飞语音听写 ⭐⭐⭐⭐⭐（推荐）

**优点：**
- 中文识别准确度业界领先
- 专为中文优化
- 提供 WebSocket 和 HTTP API
- 实时语音识别
- 支持多种音频格式

**缺点：**
- 需要注册并申请 API Key
- 按量收费（有免费额度）

**价格：**
- 每日免费额度：500 次
- 超出部分：0.0125 元/次

**接入步骤：**

1. 注册讯飞开放平台账号：https://www.xfyun.cn/
2. 创建应用，获取 APPID、APIKey、APISecret
3. 选择接入方式：

#### WebSocket 实时语音识别（推荐）

```javascript
// 安装依赖
npm install crypto-js

// 实现代码
import CryptoJS from 'crypto-js';

class XunfeiASR {
  constructor(appId, apiKey, apiSecret) {
    this.appId = appId;
    this.apiKey = apiKey;
    this.apiSecret = apiSecret;
    this.ws = null;
  }

  getWebSocketUrl() {
    const url = 'wss://iat-api.xfyun.cn/v2/iat';
    const host = 'iat-api.xfyun.cn';
    const date = new Date().toUTCString();
    
    const signatureOrigin = `host: ${host}\ndate: ${date}\nGET /v2/iat HTTP/1.1`;
    const signature = CryptoJS.HmacSHA256(signatureOrigin, this.apiSecret);
    const signatureBase64 = CryptoJS.enc.Base64.stringify(signature);
    
    const authorizationOrigin = `api_key="${this.apiKey}", algorithm="hmac-sha256", headers="host date request-line", signature="${signatureBase64}"`;
    const authorization = btoa(authorizationOrigin);
    
    return `${url}?authorization=${authorization}&date=${date}&host=${host}`;
  }

  start(onResult, onError) {
    const wsUrl = this.getWebSocketUrl();
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      // 发送音频数据
      const params = {
        common: { app_id: this.appId },
        business: {
          language: 'zh_cn',
          domain: 'iat',
          accent: 'mandarin'
        },
        data: {
          status: 0,
          format: 'audio/L16;rate=16000',
          encoding: 'raw',
          audio: '' // Base64 编码的音频数据
        }
      };
      this.ws.send(JSON.stringify(params));
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.code === 0) {
        const result = data.data.result;
        if (result) {
          const text = result.ws.map(w => w.cw[0].w).join('');
          onResult(text);
        }
      } else {
        onError(data.message);
      }
    };

    this.ws.onerror = (error) => {
      onError(error);
    };
  }

  stop() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用
const asr = new XunfeiASR('your_app_id', 'your_api_key', 'your_api_secret');
asr.start(
  (text) => console.log('识别结果:', text),
  (error) => console.error('识别错误:', error)
);
```

### 3. 百度语音识别

**优点：**
- 准确度高
- 文档完善
- 支持多种语言
- SDK 完善

**缺点：**
- 需要百度云账号
- 按量收费

**价格：**
- 每日免费额度：50000 次
- 超出部分：0.0038 元/次

**接入步骤：**

1. 注册百度智能云：https://cloud.baidu.com/
2. 开通语音识别服务
3. 创建应用获取 API Key 和 Secret Key

**实现示例：**

```javascript
// 获取 Access Token
async function getAccessToken(apiKey, secretKey) {
  const response = await fetch(
    `https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=${apiKey}&client_secret=${secretKey}`
  );
  const data = await response.json();
  return data.access_token;
}

// 语音识别
async function recognize(audioData, accessToken) {
  const response = await fetch(
    `https://vop.baidu.com/server_api?dev_pid=1537&cuid=electron_app&token=${accessToken}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'audio/pcm;rate=16000'
      },
      body: audioData
    }
  );
  const result = await response.json();
  return result.result[0];
}
```

### 4. 阿里云智能语音

**优点：**
- 阿里云生态集成好
- 支持实时识别和录音文件识别
- 准确度高

**缺点：**
- 需要阿里云账号
- 配置相对复杂

**价格：**
- 按时长收费：0.0025 元/秒

**接入文档：**
https://help.aliyun.com/product/30413.html

### 5. 腾讯云语音识别

**优点：**
- 腾讯云生态
- 支持实时和离线识别
- 准确度高

**缺点：**
- 需要腾讯云账号

**价格：**
- 按时长收费：0.0025 元/秒
- 每月免费额度：10 小时

**接入文档：**
https://cloud.tencent.com/product/asr

### 6. Azure Speech Services

**优点：**
- 国际化支持好
- 支持多种语言
- 准确度高
- 文档完善

**缺点：**
- 国内访问可能较慢
- 需要 Azure 账号

**价格：**
- 免费层：每月 5 小时
- 标准层：$1/小时

**实现示例：**

```javascript
// 安装依赖
npm install microsoft-cognitiveservices-speech-sdk

import * as sdk from 'microsoft-cognitiveservices-speech-sdk';

function recognizeSpeech(subscriptionKey, region) {
  const speechConfig = sdk.SpeechConfig.fromSubscription(subscriptionKey, region);
  speechConfig.speechRecognitionLanguage = 'zh-CN';

  const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
  const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

  recognizer.recognizeOnceAsync(
    (result) => {
      console.log('识别结果:', result.text);
      recognizer.close();
    },
    (error) => {
      console.error('识别错误:', error);
      recognizer.close();
    }
  );
}
```

## 推荐方案

### 开发测试阶段
使用 **Web Speech API**，简单快速，无需配置。

### 生产环境

#### 国内项目（推荐）
使用 **讯飞语音听写**：
- ✅ 中文识别准确度最高
- ✅ 延迟低
- ✅ 价格合理
- ✅ 免费额度充足

#### 国际化项目
使用 **Azure Speech Services**：
- ✅ 多语言支持好
- ✅ 全球节点
- ✅ 文档完善

## Electron 集成建议

在 Electron 中集成语音识别时，建议：

1. **主进程处理音频流**
   - 使用 Node.js 的音频库获取麦克风输入
   - 在主进程中调用语音识别 API

2. **渲染进程展示 UI**
   - 显示录音状态
   - 展示识别结果

3. **IPC 通信**
   - 渲染进程发起录音请求
   - 主进程返回识别结果

**示例架构：**

```javascript
// 主进程 (main.js)
import recorder from 'node-record-lpcm16';

ipcMain.handle('start-recording', async () => {
  const recording = recorder.record({
    sampleRate: 16000,
    channels: 1
  });

  recording.stream()
    .on('data', (chunk) => {
      // 发送音频数据到语音识别服务
      sendToASR(chunk);
    });
});

// 渲染进程 (renderer.js)
document.getElementById('record-btn').addEventListener('click', async () => {
  await window.electronAPI.startRecording();
});
```

## 总结

- **快速原型**：Web Speech API
- **国内生产环境**：讯飞语音听写（强烈推荐）
- **国际化项目**：Azure Speech Services
- **预算充足**：百度/阿里/腾讯云（三选一）

建议从 Web Speech API 开始，待项目稳定后迁移到讯飞语音听写以提升用户体验。
