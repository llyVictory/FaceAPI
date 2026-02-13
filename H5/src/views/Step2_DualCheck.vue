<template>
  <div class="step-container">
    <Camera @ready="onCameraReady" @error="onCameraError" ref="cameraRef" />
    
    <div class="overlay-ui">
      <!-- Top Status Bar -->
      <div class="status-bar">
        <div class="step-badge">现场合拍</div>
        <div class="instruction">{{ instructionText }}</div>
      </div>

       <!-- Countdown Timer -->
       <div class="timer" :class="{ critical: timeLeft <= 10 }">
          ⏱ {{ timeLeft }}s
       </div>

      <!-- Detection Indicators -->
      <div class="indicators">
        <div class="indicator" :class="{ ok: isFaceMatched }">
          <span class="icon">👤</span> 人脸: {{ faceStatus }}
        </div>
        <div class="indicator" :class="{ ok: isQrMatched }">
          <span class="icon">📍</span> 位置: {{ qrStatus }}
        </div>
      </div>

      <!-- Loading / API Check Overlay -->
      <div v-if="verifying" class="processing-overlay">
          <div class="spinner"></div>
          <p>正在连接云端验证身份...</p>
      </div>

      <!-- Success Modal -->
      <div v-if="isGlobalSuccess" class="success-screen">
        <div class="success-content">
          <div class="checkmark">✔</div>
          <h2>签到成功</h2>
          <div class="result-details">
             <p>👤 姓名: <strong>{{ verifiedName }}</strong></p>
             <p>📍 地点: {{ verifiedAddress }}</p>
             <p>🕒 时间: {{ verifiedTime }}</p>
          </div>
          <button @click="resetApp">重新演示</button>
        </div>
      </div>
      
      <!-- Fail/timeout Modal -->
      <div v-if="isFailed" class="fail-screen">
        <div class="fail-content">
          <div class="crossmark">✕</div>
          <h2>{{ failReason }}</h2>
          <button @click="resetApp">重试</button>
        </div>
      </div>

       <!-- Debug Info (Optional) -->
       <div v-if="debugMsg" class="debug-toast">{{ debugMsg }}</div>
       
       <!-- Success Counter Debug -->
       <div class="counter-debug">确认中: {{ successCounterDisplay }}/10</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted, onMounted } from 'vue';
import Camera from '../components/Camera.vue';
import { faceEngine, api as faceapi } from '../logic/face';
import { scanQRCode } from '../logic/scanner';
import { verifyIdentity } from '../logic/api';
import { appState } from '../state';
import { CONFIG } from '../config';

const cameraRef = ref(null);
const instructionText = ref("请与现场二维码同框合影");
const faceStatus = ref("未检测");
const qrStatus = ref("未检测");
const debugMsg = ref("");

// State
const isFaceMatched = ref(false);
const isQrMatched = ref(false);
const timeLeft = ref(CONFIG.TIMEOUT_SECONDS);
const verifying = ref(false);
const isGlobalSuccess = ref(false);
const isFailed = ref(false);
const failReason = ref("");

// Result Data
const verifiedName = ref("");
const verifiedAddress = ref("");
const verifiedTime = ref("");



let videoEl = null;
let canvasEl = null;
let loopId = null;
let timerId = null;
let successCounter = 0;
let missCounter = 0;
let lastValidAddress = "";
const successCounterDisplay = ref(0); 

// GPS State
const gpsAddress = ref("定位中...");
const gpsCoords = ref(null);

const onCameraReady = ({ video, canvas }) => {
  videoEl = video;
  canvasEl = canvas;
  startDualLoop();
  startTimer();
  initLocation(); // Start GPS
};

const initLocation = () => {
    if (!navigator.geolocation) {
        gpsAddress.value = "不支持定位";
        return;
    }
    
    navigator.geolocation.getCurrentPosition(async (pos) => {
        const { latitude, longitude } = pos.coords;
        gpsCoords.value = { lat: latitude, lng: longitude };
        gpsAddress.value = `GPS: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`; // Fallback
        
        // Reverse Geocode (OpenStreetMap Nominatim)
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1&accept-language=zh-CN`;
            const res = await fetch(url);
            const data = await res.json();
            if (data && data.display_name) {
                // Shorten address if too long
                let addr = data.display_name;
                // Try to take specific parts if available to be cleaner
                if (data.address) {
                    const city = data.address.city || data.address.town || "";
                    const road = data.address.road || "";
                    const building = data.address.building || "";
                    if (city || road) {
                        addr = `${city} ${road} ${building}`;
                    }
                }
                gpsAddress.value = addr;
            }
        } catch (e) {
            console.warn("Geocoding failed:", e);
            // Keep numerical GPS as fallback
        }
    }, (err) => {
        console.error("GPS Error:", err);
        gpsAddress.value = "定位失败";
    }, {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0
    });
};


const onCameraError = (err) => {
  debugMsg.value = err.message;
};

const startTimer = () => {
    timerId = setInterval(() => {
        timeLeft.value--;
        if (timeLeft.value <= 0) {
            handleFail("验证超时");
        }
    }, 1000);
};

const resetApp = () => {
    appState.reset();
}

const handleFail = (reason) => {
    isFailed.value = true;
    failReason.value = reason;
    stopAll();
};

const stopAll = () => {
    if (loopId) cancelAnimationFrame(loopId);
    if (timerId) clearInterval(timerId);
};

const startDualLoop = async () => {
  const loop = async () => {
    if (!videoEl || videoEl.paused || videoEl.ended || verifying.value || isFailed.value) return;

    // 1. Face Detection
    const detection = await faceEngine.detectSingleFace(videoEl);
    
    // 2. QR Detection
    const ctx = canvasEl.getContext('2d');
    ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
    const qrResult = scanQRCode(ctx, canvasEl.width, canvasEl.height);
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

    // --- Face Logic ---
    if (detection) {
      const dist = faceapi.euclideanDistance(detection.descriptor, appState.baseFaceDescriptor);
      // debugMsg.value = `Distance: ${dist.toFixed(4)}`; // reduce noise
      
      const box = detection.detection.box;
      
      if (dist < 0.5) { // Match Threshold
         isFaceMatched.value = true;
         faceStatus.value = "本人";
         drawBox(ctx, box, '#4CAF50', `我 (${dist.toFixed(2)})`);
      } else {
         isFaceMatched.value = false;
         faceStatus.value = "非本人";
         drawBox(ctx, box, '#F44336', `陌生人 (${dist.toFixed(2)})`);
      }
    } else {
      isFaceMatched.value = false;
      faceStatus.value = "未检测";
    }

    // --- QR Logic ---
    let currentAddress = null;
    if (qrResult) {
      drawPoly(ctx, qrResult.location, '#2196F3');
      // For demo, accept ANY QR, or specific ones. 
      // User said "arbitrary string is fine, write to CSV address"
      if (qrResult.data) {
         currentAddress = qrResult.data;
         isQrMatched.value = true;
         qrStatus.value = "已获取";
      }
    } else {
      isQrMatched.value = false;
      qrStatus.value = "未检测";
    }

    // --- Final Check ---
    if (isFaceMatched.value && isQrMatched.value) {
        successCounter++;
        missCounter = 0; // Reset miss counter on success
        lastValidAddress = currentAddress; // Cache valid address
        
        successCounterDisplay.value = successCounter; 
        if (successCounter > 10) { 
            handlePreSuccess(lastValidAddress);
            return; // Stop current loop logic immediately
        }
    } else {
        // Grace period: Allow missing a few frames (e.g. 5 frames approx 150ms)
        missCounter++;
        if (missCounter > 10) {
            successCounter = 0;
            successCounterDisplay.value = 0;
        }
        // If within grace period, do NOT reset successCounter
    }

    loopId = requestAnimationFrame(loop);
  };

  loop();
};

const handlePreSuccess = async (address) => {
    stopAll(); // Stop timer and loop
    verifying.value = true;
    
    // 1. Capture Image Blob
    const captureBlob = await new Promise(resolve => {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = videoEl.videoWidth;
        tempCanvas.height = videoEl.videoHeight;
        tempCanvas.getContext('2d').drawImage(videoEl, 0, 0);
        tempCanvas.toBlob(resolve, 'image/jpeg', 0.9);
    });

    // 2. Call Backend
    try {
        const fullAddress = `${address} @ ${gpsAddress.value}`;
        const res = await verifyIdentity(captureBlob, fullAddress);
        
        if (res.code === 200 && res.isMatch) {
             isGlobalSuccess.value = true;
             verifiedName.value = res.userId;
             verifiedAddress.value = res.address;
             verifiedTime.value = new Date().toLocaleTimeString();
        } else {
             handleFail(`认证失败: ${res.msg}`);
        }

    } catch (e) {
        handleFail(`网络/服务器错误: ${e.message}`);
    } finally {
        verifying.value = false;
    }
};

const drawBox = (ctx, box, color, label) => {
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.strokeRect(box.x, box.y, box.width, box.height);
  
  // Draw text in correct orientation (counter the CSS mirror)
  ctx.save();
  const textX = box.x + box.width / 2;
  const textY = box.y - 10;
  ctx.translate(textX, textY);
  ctx.scale(-1, 1); 
  ctx.fillStyle = color;
  ctx.font = 'bold 16px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(label, 0, 0);
  ctx.restore();
};

const drawPoly = (ctx, loc, color) => {
  ctx.beginPath();
  ctx.lineWidth = 4;
  ctx.strokeStyle = color;
  ctx.moveTo(loc.topLeftCorner.x, loc.topLeftCorner.y);
  ctx.lineTo(loc.topRightCorner.x, loc.topRightCorner.y);
  ctx.lineTo(loc.bottomRightCorner.x, loc.bottomRightCorner.y);
  ctx.lineTo(loc.bottomLeftCorner.x, loc.bottomLeftCorner.y);
  ctx.lineTo(loc.topLeftCorner.x, loc.topLeftCorner.y);
  ctx.stroke();
};

onUnmounted(() => {
  stopAll();
});
</script>

<style scoped>
.step-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  background: black;
}

.overlay-ui {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.status-bar {
  margin-top: 40px;
  background: rgba(0, 0, 0, 0.6);
  padding: 10px 20px;
  border-radius: 30px;
  backdrop-filter: blur(10px);
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.timer {
    margin-top: 20px;
    font-size: 24px;
    font-weight: bold;
    color: white;
    background: rgba(0,0,0,0.5);
    padding: 5px 15px;
    border-radius: 12px;
}
.timer.critical {
    color: #ff4d4d;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); }
}

.step-badge {
  font-size: 12px;
  color: #2196F3; /* Blue for Step 2 */
  font-weight: bold;
  margin-bottom: 4px;
}

.instruction {
  font-size: 18px;
  color: white;
  font-weight: 500;
}

.indicators {
    position: absolute;
    bottom: 120px;
    width: 100%;
    display: flex;
    justify-content: center;
    gap: 20px;
}

.indicator {
    background: rgba(0,0,0,0.5);
    color: #ccc;
    padding: 10px 15px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.3s;
}

.indicator.ok {
    background: rgba(76, 175, 80, 0.2);
    border-color: #4CAF50;
    color: #4CAF50;
}

/* Processing Overlay */
.processing-overlay {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.8);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: white;
    z-index: 20;
}
.spinner {
    width: 40px; height: 40px;
    border: 4px solid rgba(255,255,255,0.3);
    border-top-color: #2196F3;
    border-radius: 50%;
    animation: spin 1s infinite linear;
    margin-bottom: 20px;
}
@keyframes spin { to { transform: rotate(360deg); } }


.success-screen, .fail-screen {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.9);
    pointer-events: auto;
    display: flex;
    justify-content: center;
    align-items: center;
    animation: fadeIn 0.5s ease;
    z-index: 30;
}

.success-content, .fail-content {
    text-align: center;
    color: white;
}

.checkmark {
    width: 80px;
    height: 80px;
    background: #4CAF50;
    border-radius: 50%;
    font-size: 40px;
    line-height: 80px;
    margin: 0 auto 20px;
    box-shadow: 0 0 30px #4CAF50;
}

.crossmark {
    width: 80px;
    height: 80px;
    background: #FF5252;
    border-radius: 50%;
    font-size: 40px;
    line-height: 80px;
    margin: 0 auto 20px;
    box-shadow: 0 0 30px #FF5252;
}

.result-details {
    margin: 20px 0;
    text-align: left;
    background: rgba(255,255,255,0.1);
    padding: 20px;
    border-radius: 12px;
}
.result-details p {
    margin: 8px 0;
    font-size: 16px;
}

button {
    margin-top: 20px;
    padding: 10px 24px;
    background: white;
    color: black;
    border: none;
    border-radius: 20px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
}

.debug-toast {
  position: absolute;
  top: 100px;
  right: 10px;
  color: yellow;
  font-family: monospace;
  font-size: 10px;
  background: rgba(0,0,0,0.5);
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.counter-debug {
  position: absolute;
  top: 130px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: #4CAF50;
  padding: 6px 12px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
}
</style>
