# 语音输入方案调研

## 已实现方案：Web Speech API

当前前端已实现基于浏览器原生 Web Speech API 的语音输入功能。

### 优点
- 无需额外 API Key
- 实现简单，代码量少
- 适合快速原型开发
- 无服务器成本

### 缺点
- 浏览器兼容性有限（主要支持 Chrome/Edge）
- 需要 HTTPS 环境（或 localhost）
- 识别准确度受环境影响
- 依赖网络连接（调用 Google 服务）

## 推荐的替代方案

### 1. 讯飞语音听写 (科大讯飞)

**特点：**
- 中文识别准确度高
- 支持实时语音转写
- 提供 WebAPI 和 WebSocket 接口
- 国内服务，响应速度快

**适用场景：**
- 需要高准确度的中文识别
- 对实时性要求高的应用
- 国内用户为主的产品

**接入方式：**
```javascript
// 需要申请 APPID
import CryptoJS from 'crypto-js'

const APPID = 'your_appid'
const API_KEY = 'your_api_key'
const API_SECRET = 'your_api_secret'

// WebSocket 方式
const wsUrl = 'wss://iat-api.xfyun.cn/v2/iat'
```

**价格：**
- 免费额度：500 次/天
- 收费标准：0.0004 元/次

### 2. 百度语音识别

**特点：**
- 成熟的语音识别服务
- 支持多种音频格式
- 提供长语音识别
- 可自定义垂直领域模型

**适用场景：**
- 需要识别较长语音内容
- 有特定行业词汇的应用
- 需要离线识别能力

**接入方式：**
```javascript
// REST API
const token = await getAccessToken(API_KEY, SECRET_KEY)
const response = await fetch('https://vop.baidu.com/server_api', {
  method: 'POST',
  body: audioData
})
```

**价格：**
- 免费额度：5 万次/月
- 收费标准：0.0024 元/次

### 3. 阿里云智能语音

**特点：**
- 企业级服务稳定性
- 支持多种语言和方言
- 实时语音识别和录音文件识别
- 与阿里云其他服务集成方便

**适用场景：**
- 企业级应用
- 多语言支持需求
- 已使用阿里云其他服务

**接入方式：**
```javascript
// SDK 方式
import NlsClient from '@alicloud/nls-client'

const client = new NlsClient({
  accessKeyId: 'your_key_id',
  accessKeySecret: 'your_key_secret'
})
```

**价格：**
- 免费额度：300 小时/月
- 收费标准：按时长计费

### 4. 腾讯云语音识别

**特点：**
- 多场景识别模型
- 支持热词配置
- 流式识别和一句话识别
- 与微信生态集成

**适用场景：**
- 微信小程序/公众号应用
- 需要行业热词定制
- 对实时性要求高

**接入方式：**
```javascript
// WebSocket 流式识别
const ws = new WebSocket('wss://asr.cloud.tencent.com/...')
ws.send(audioChunk)
```

**价格：**
- 免费额度：15 小时/月
- 收费标准：0.0012-0.002 元/分钟

### 5. Azure Speech Services (微软)

**特点：**
- 全球化部署
- 多语言支持最全面
- 自定义语音模型
- 可与 ChatGPT 等 AI 服务集成

**适用场景：**
- 国际化产品
- 需要多语言支持
- 对准确度要求极高

**接入方式：**
```javascript
import * as sdk from 'microsoft-cognitiveservices-speech-sdk'

const recognizer = new sdk.SpeechRecognizer(config)
recognizer.recognizeOnceAsync(result => {
  console.log(result.text)
})
```

**价格：**
- 免费额度：5 小时/月
- 收费标准：$1/小时

## 方案对比

| 方案 | 中文准确度 | 实时性 | 成本 | 开发难度 | 推荐指数 |
|------|-----------|--------|------|----------|----------|
| Web Speech API | ⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | ⭐ | ⭐⭐⭐ |
| 讯飞语音 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 低 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 百度语音 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 低 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 阿里云 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 腾讯云 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 低 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Azure Speech | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐ | ⭐⭐⭐ |

## 推荐方案

针对本项目（任意门导航）的特点，推荐以下方案：

### 首选：讯飞语音听写
- **理由**：中文识别准确度最高，适合地址识别场景
- **成本**：免费额度足够开发和小规模使用
- **实现**：参考 [讯飞开放平台文档](https://www.xfyun.cn/doc/asr/voicedictation/API.html)

### 备选：百度语音识别
- **理由**：免费额度更大，适合快速增长的用户量
- **成本**：5 万次/月免费额度
- **实现**：参考 [百度 AI 开放平台文档](https://ai.baidu.com/ai-doc/SPEECH/Vk38lxily)

## 实现建议

1. **前端录音**：使用 MediaRecorder API 录制音频
2. **音频处理**：转换为对应服务要求的格式（通常是 PCM/WAV）
3. **发送识别**：通过 WebSocket 实时传输或 HTTP 上传完整音频
4. **结果解析**：处理识别结果，提取地址信息
5. **错误处理**：添加网络异常、识别失败等情况的处理

## 示例代码结构

```javascript
// 语音输入管理器
class VoiceInputManager {
  constructor(provider = 'xunfei') {
    this.provider = provider
    this.recorder = null
    this.ws = null
  }

  async start() {
    // 获取麦克风权限
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.recorder = new MediaRecorder(stream)
    
    // 初始化识别服务
    this.initProvider()
    
    // 开始录音
    this.recorder.start()
  }

  initProvider() {
    switch(this.provider) {
      case 'xunfei':
        this.initXunfei()
        break
      case 'baidu':
        this.initBaidu()
        break
      // ...
    }
  }

  stop() {
    this.recorder.stop()
    this.ws?.close()
  }
}
```

## 下一步

1. 根据项目预算和用户规模选择合适的语音服务
2. 申请相应的 API Key
3. 实现录音和语音识别功能
4. 优化识别结果的地址解析逻辑
5. 添加用户反馈机制，持续优化识别准确度
