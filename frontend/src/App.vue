<template>
  <div class="app">
    <header class="header">
      <h1>🚪 任意门 - 智能导航</h1>
    </header>

    <main class="main">
      <div class="input-panel">
        <div class="input-group">
          <label>起点：</label>
          <input
            v-model="from"
            type="text"
            placeholder="请输入起点地址"
            @keyup.enter="handleNavigate"
          />
        </div>

        <div class="input-group">
          <label>终点：</label>
          <input
            v-model="to"
            type="text"
            placeholder="请输入终点地址"
            @keyup.enter="handleNavigate"
          />
        </div>

        <div class="input-group">
          <label>出行方式：</label>
          <select v-model="mode">
            <option value="walking">步行</option>
            <option value="driving">驾车</option>
            <option value="transit">公交</option>
          </select>
        </div>

        <div v-if="mode === 'transit'" class="input-group">
          <label>城市：</label>
          <input
            v-model="city"
            type="text"
            placeholder="请输入城市名称"
            @keyup.enter="handleNavigate"
          />
        </div>

        <div class="button-group">
          <button @click="handleNavigate" :disabled="loading" class="btn-primary">
            {{ loading ? "规划中..." : "开始导航" }}
          </button>
          <button @click="handleVoiceInput" :disabled="loading" class="btn-secondary">
            🎤 语音输入
          </button>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div v-if="route" class="route-info">
          <h3>路线信息</h3>
          <p><strong>距离：</strong>{{ formatDistance(route.distance) }}</p>
          <p><strong>时长：</strong>{{ formatDuration(route.duration) }}</p>
        </div>
      </div>

      <div class="map-container">
        <div id="amap" ref="mapContainer"></div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";

const from = ref("");
const to = ref("");
const mode = ref<"walking" | "driving" | "transit">("walking");
const city = ref("");
const loading = ref(false);
const error = ref("");
const route = ref<any>(null);
const mapContainer = ref<HTMLElement | null>(null);

let map: any = null;
let AMap: any = null;

onMounted(async () => {
  try {
    AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_KEY || "",
      version: "2.0",
      plugins: ["AMap.Driving", "AMap.Walking", "AMap.Transfer"],
    });

    map = new AMap.Map("amap", {
      zoom: 13,
      center: [116.397428, 39.90923],
    });
  } catch (e) {
    console.error("地图加载失败", e);
    error.value = "地图加载失败，请检查配置";
  }
});

async function handleNavigate() {
  if (!from.value || !to.value) {
    error.value = "请输入起点和终点";
    return;
  }

  if (mode.value === "transit" && !city.value) {
    error.value = "公交模式下请输入城市";
    return;
  }

  loading.value = true;
  error.value = "";
  route.value = null;

  try {
    const response = await fetch("http://localhost:3000/api/navigate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: from.value,
        to: to.value,
        mode: mode.value,
        city: city.value,
      }),
    });

    const data = await response.json();

    if (data.success && data.route) {
      route.value = data.route;
      displayRoute(data.route);
    } else {
      error.value = data.error || "导航规划失败";
    }
  } catch (e) {
    console.error("导航请求失败", e);
    error.value = "服务器连接失败，请确保后端服务正在运行";
  } finally {
    loading.value = false;
  }
}

function displayRoute(routeData: any) {
  if (!map || !AMap) return;

  map.clearMap();

  if (routeData.polyline) {
    const path = routeData.polyline.split(";").map((point: string) => {
      const [lng, lat] = point.split(",");
      return [parseFloat(lng), parseFloat(lat)];
    });

    const polyline = new AMap.Polyline({
      path: path,
      strokeColor: "#3b82f6",
      strokeWeight: 6,
      strokeOpacity: 0.8,
    });

    map.add(polyline);
    map.setFitView([polyline]);
  }

  if (routeData.origin_location) {
    const [lng, lat] = routeData.origin_location.split(",");
    const startMarker = new AMap.Marker({
      position: [parseFloat(lng), parseFloat(lat)],
      icon: "//a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-default.png",
      title: "起点",
    });
    map.add(startMarker);
  }

  if (routeData.destination_location) {
    const [lng, lat] = routeData.destination_location.split(",");
    const endMarker = new AMap.Marker({
      position: [parseFloat(lng), parseFloat(lat)],
      icon: "//a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-red.png",
      title: "终点",
    });
    map.add(endMarker);
  }
}

function handleVoiceInput() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    error.value = "您的浏览器不支持语音识别，请使用 Chrome 浏览器";
    return;
  }

  const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    loading.value = true;
    error.value = "正在听取...请说话";
  };

  recognition.onresult = (event: any) => {
    const transcript = event.results[0][0].transcript;
    parseVoiceInput(transcript);
    loading.value = false;
  };

  recognition.onerror = (event: any) => {
    error.value = `语音识别错误：${event.error}`;
    loading.value = false;
  };

  recognition.onend = () => {
    loading.value = false;
  };

  recognition.start();
}

function parseVoiceInput(text: string) {
  const fromMatch = text.match(/从(.+?)到/);
  const toMatch = text.match(/到(.+?)$/);

  if (fromMatch && toMatch) {
    from.value = fromMatch[1].trim();
    to.value = toMatch[1].trim();
    error.value = "";
  } else {
    error.value = '无法识别地址，请说类似"从天安门到西单"的格式';
  }
}

function formatDistance(meters: string | number): string {
  const m = typeof meters === "string" ? parseInt(meters) : meters;
  if (m < 1000) {
    return `${m} 米`;
  }
  return `${(m / 1000).toFixed(2)} 公里`;
}

function formatDuration(seconds: string | number): string {
  const s = typeof seconds === "string" ? parseInt(seconds) : seconds;
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  
  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`;
  }
  return `${minutes} 分钟`;
}
</script>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.input-panel {
  width: 400px;
  padding: 2rem;
  background: #f8f9fa;
  overflow-y: auto;
  border-right: 1px solid #e0e0e0;
}

.input-group {
  margin-bottom: 1.5rem;
}

.input-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.input-group input,
.input-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.input-group input:focus,
.input-group select:focus {
  outline: none;
  border-color: #667eea;
}

.button-group {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.btn-primary,
.btn-secondary {
  flex: 1;
  padding: 0.875rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
}

.btn-secondary:hover:not(:disabled) {
  background: #667eea;
  color: white;
}

.error-message {
  padding: 1rem;
  background: #fee;
  color: #c33;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.route-info {
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.route-info h3 {
  margin-bottom: 0.75rem;
  color: #667eea;
}

.route-info p {
  margin-bottom: 0.5rem;
  color: #555;
}

.map-container {
  flex: 1;
  position: relative;
}

#amap {
  width: 100%;
  height: 100%;
}
</style>
