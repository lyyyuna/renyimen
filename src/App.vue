<template>
  <div id="app" class="app-container">
    <header class="app-header">
      <h1>🚪 任意门智能导航</h1>
      <p class="subtitle">基于 Claude AI + 高德地图 MCP</p>
    </header>

    <main class="main-content">
      <div class="input-section">
        <div class="input-group">
          <input
            v-model="userInput"
            @keyup.enter="handleSubmit"
            type="text"
            placeholder="例如：从天安门到西单"
            class="text-input"
            :disabled="loading"
          />
          <button @click="handleSubmit" class="submit-btn" :disabled="loading || !userInput.trim()">
            {{ loading ? '处理中...' : '导航' }}
          </button>
        </div>

        <div class="voice-section">
          <button @click="toggleVoiceInput" class="voice-btn" :class="{ active: isRecording }">
            {{ isRecording ? '🔴 停止录音' : '🎤 语音输入' }}
          </button>
          <span v-if="isRecording" class="recording-indicator">正在录音...</span>
        </div>

        <div class="mode-selector">
          <label>出行方式：</label>
          <button
            v-for="mode in travelModes"
            :key="mode.value"
            @click="selectedMode = mode.value"
            class="mode-btn"
            :class="{ active: selectedMode === mode.value }"
          >
            {{ mode.label }}
          </button>
        </div>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <div v-if="routeInfo" class="route-info">
        <h3>路线信息</h3>
        <div class="route-details">
          <p><strong>起点：</strong>{{ routeInfo.origin?.name || '未知' }}</p>
          <p><strong>终点：</strong>{{ routeInfo.destination?.name || '未知' }}</p>
          <div v-if="routeInfo.routes && routeInfo.routes.length > 0">
            <h4>推荐路线</h4>
            <div v-for="(route, index) in routeInfo.routes" :key="index" class="route-item">
              <p><strong>方式：</strong>{{ getModeLabel(route.mode) }}</p>
              <p><strong>距离：</strong>{{ formatDistance(route.distance) }}</p>
              <p><strong>时间：</strong>{{ formatDuration(route.duration) }}</p>
            </div>
          </div>
        </div>
      </div>

      <div id="map-container" class="map-container"></div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      userInput: '',
      loading: false,
      error: null,
      routeInfo: null,
      selectedMode: 'walking',
      travelModes: [
        { label: '🚶 步行', value: 'walking' },
        { label: '🚗 驾车', value: 'driving' },
        { label: '🚌 公交', value: 'transit' }
      ],
      isRecording: false,
      recognition: null,
      map: null,
      markers: []
    };
  },
  mounted() {
    this.initMap();
    this.initVoiceRecognition();
  },
  methods: {
    initMap() {
      if (typeof AMap !== 'undefined') {
        this.map = new AMap.Map('map-container', {
          zoom: 13,
          center: [116.397428, 39.90923],
          viewMode: '3D'
        });
      }
    },
    initVoiceRecognition() {
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'zh-CN';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;

        this.recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          this.userInput = transcript;
          this.isRecording = false;
        };

        this.recognition.onerror = () => {
          this.isRecording = false;
          this.error = '语音识别失败，请重试';
        };

        this.recognition.onend = () => {
          this.isRecording = false;
        };
      }
    },
    async toggleVoiceInput() {
      if (!this.recognition) {
        this.error = '您的浏览器不支持语音识别';
        return;
      }

      if (this.isRecording) {
        this.recognition.stop();
      } else {
        this.error = null;
        
        try {
          const permission = await window.electronAPI.requestMicrophonePermission();
          console.log('🎤 麦克风权限结果:', permission);
          
          if (!permission.granted) {
            this.error = '需要麦克风权限才能使用语音输入功能';
            return;
          }
          
          this.isRecording = true;
          this.recognition.start();
        } catch (err) {
          console.error('请求麦克风权限失败:', err);
          this.error = '无法获取麦克风权限';
        }
      }
    },
    async handleSubmit() {
      if (!this.userInput.trim() || this.loading) return;

      this.loading = true;
      this.error = null;
      this.routeInfo = null;

      try {
        const input = `${this.userInput}，使用${this.getModeLabel(this.selectedMode)}方式`;
        const result = await window.electronAPI.callClaude(input);

        if (result.raw) {
          this.error = '无法解析导航结果，请重试';
        } else {
          this.routeInfo = result;
          this.displayRouteOnMap(result);
        }
      } catch (err) {
        this.error = err.message || '处理请求时出错';
      } finally {
        this.loading = false;
      }
    },
    displayRouteOnMap(routeInfo) {
      if (!this.map || !routeInfo.origin || !routeInfo.destination) return;

      this.markers.forEach(marker => marker.setMap(null));
      this.markers = [];

      const originLng = routeInfo.origin.location?.longitude || routeInfo.origin.location?.[0];
      const originLat = routeInfo.origin.location?.latitude || routeInfo.origin.location?.[1];
      const destLng = routeInfo.destination.location?.longitude || routeInfo.destination.location?.[0];
      const destLat = routeInfo.destination.location?.latitude || routeInfo.destination.location?.[1];

      if (originLng && originLat && destLng && destLat) {
        const originMarker = new AMap.Marker({
          position: [originLng, originLat],
          title: routeInfo.origin.name,
          label: { content: '起' }
        });

        const destMarker = new AMap.Marker({
          position: [destLng, destLat],
          title: routeInfo.destination.name,
          label: { content: '终' }
        });

        this.markers.push(originMarker, destMarker);
        this.map.add(this.markers);

        this.map.setFitView(this.markers);

        if (routeInfo.routes && routeInfo.routes[0]?.polyline) {
          const polyline = new AMap.Polyline({
            path: routeInfo.routes[0].polyline,
            strokeColor: '#3b82f6',
            strokeWeight: 6
          });
          this.map.add(polyline);
        }
      }
    },
    getModeLabel(mode) {
      const modeMap = {
        walking: '步行',
        driving: '驾车',
        transit: '公交'
      };
      return modeMap[mode] || mode;
    },
    formatDistance(meters) {
      if (!meters) return '-';
      if (meters < 1000) return `${meters}米`;
      return `${(meters / 1000).toFixed(1)}公里`;
    },
    formatDuration(seconds) {
      if (!seconds) return '-';
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}分钟`;
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours}小时${mins}分钟`;
    }
  }
};
</script>

<style scoped>
.app-container {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  max-width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  margin: 0;
  font-size: 2em;
}

.subtitle {
  margin: 5px 0 0;
  opacity: 0.9;
  font-size: 0.9em;
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.input-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.input-group {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.text-input {
  flex: 1;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1em;
  transition: border-color 0.3s;
}

.text-input:focus {
  outline: none;
  border-color: #667eea;
}

.submit-btn {
  padding: 12px 30px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
  transition: background 0.3s;
}

.submit-btn:hover:not(:disabled) {
  background: #5568d3;
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.voice-section {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.voice-btn {
  padding: 10px 20px;
  background: white;
  border: 2px solid #667eea;
  color: #667eea;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.voice-btn:hover {
  background: #667eea;
  color: white;
}

.voice-btn.active {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
}

.recording-indicator {
  color: #ef4444;
  font-weight: bold;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.mode-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mode-selector label {
  font-weight: bold;
}

.mode-btn {
  padding: 8px 16px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.mode-btn:hover {
  border-color: #667eea;
}

.mode-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
  border-left: 4px solid #c33;
}

.route-info {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.route-info h3 {
  margin-top: 0;
  color: #667eea;
}

.route-details p {
  margin: 8px 0;
}

.route-item {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 6px;
  margin: 10px 0;
  border-left: 4px solid #667eea;
}

.map-container {
  width: 100%;
  height: 500px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
