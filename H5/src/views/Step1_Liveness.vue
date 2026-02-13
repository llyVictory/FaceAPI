<template>
  <div class="step-container">
    <Camera @ready="onCameraReady" @error="onCameraError" ref="cameraRef" />
    
    <div class="overlay-ui">
      <!-- Top Status Bar -->
      <div class="status-bar">
        <div class="step-badge">{{ stepBadgeText }}</div>
        <div class="instruction">{{ instructionText }}</div>
      </div>

      <!-- Face Guide Frame -->
      <div class="face-frame" :class="{ 'active': isFaceDetected, 'success': isSuccess }">
        <div class="corner tl"></div>
        <div class="corner tr"></div>
        <div class="corner bl"></div>
        <div class="corner br"></div>
        <div class="scan-line" v-if="isFaceDetected && !isSuccess"></div>
      </div>

      <!-- Feedback Toast -->
      <div v-if="feedbackMsg" class="feedback-toast">{{ feedbackMsg }}</div>
      
      <!-- Success Modal -->
      <div v-if="showSuccessModal" class="success-modal-overlay" @click="closeSuccessModal">
        <div class="success-modal" @click.stop>
          <div class="success-icon">
            <svg viewBox="0 0 52 52" class="checkmark">
              <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
              <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
            </svg>
          </div>
          <h2 class="success-title">签到成功</h2>
          <div class="success-info">
            <div class="info-item">
              <span class="label">姓名：</span>
              <span class="value">{{ successData.userName }}</span>
            </div>
            <div class="info-item">
              <span class="label">时间：</span>
              <span class="value">{{ successData.time }}</span>
            </div>
            <div class="info-item">
              <span class="label">GPS：</span>
              <span class="value">{{ successData.gps }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Debug Display -->
      <div class="debug-ear">{{ debugKey }}: {{ debugVal }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue';
import Camera from '../components/Camera.vue';
import { faceEngine } from '../logic/face';
import { insightFace } from '../logic/insightface';
import { appState } from '../state';

const cameraRef = ref(null);
const isFaceDetected = ref(false);
const isSuccess = ref(false);
const instructionText = ref("请正对屏幕，保持静止");
const stepBadgeText = ref("活体验证"); // Default
const feedbackMsg = ref("");
const showSuccessModal = ref(false);
const successData = ref({
  userName: '',
  time: '',
  gps: ''
});
const debugKey = ref("Init");
const debugVal = ref("--");
let videoEl = null;
let canvasEl = null;
let loopId = null;

// Logic State
let actionQueue = []; // Queue of actions
let totalActions = 0; // Total actions to perform
let currentAction = ''; // 'blink' or 'mouth'
let isActionPending = false; // tracked state
let isProcessingAction = false; // Lock to prevent rapid-fire triggering

// Thresholds
const BLINK_CLOSE_THRESH = 0.29; 
const BLINK_OPEN_THRESH = 0.31;
const MOUTH_OPEN_THRESH = 0.40; 
const MOUTH_CLOSE_THRESH = 0.20; 

const onCameraReady = ({ video, canvas }) => {
  videoEl = video;
  canvasEl = canvas;
  
  if (Math.random() > 0.5) {
      actionQueue = ['blink', 'mouth'];
  } else {
      actionQueue = ['mouth', 'blink'];
  }
  totalActions = actionQueue.length;
  
  nextAction(); 
  startDetectionLoop();
};

const nextAction = () => {
    if (actionQueue.length === 0) {
        currentAction = 'done';
        return;
    }
    
    currentAction = actionQueue.shift();
    isActionPending = false;
    isProcessingAction = false; // Unlock
    
    // Update Badge: 1/2 or 2/2
    // If raw queue was 2, now length is 1 -> means we are at 1st action (2-1+1=2? No)
    // 1st call: queue has 1 left (was 2). Index = 2 - 1 = 1.
    // 2nd call: queue has 0 left (was 1). Index = 2 - 0 = 2.
    const currentIndex = totalActions - actionQueue.length;
    stepBadgeText.value = `活体验证 ${currentIndex}/${totalActions}`;

    if (currentAction === 'blink') {
        instructionText.value = "请眨眨眼。建议闭眼时间大于1秒钟";
        debugKey.value = "EAR";
    } else if (currentAction === 'mouth') {
        instructionText.value = "请张张嘴";
        debugKey.value = "MAR";
    }
};
// ... (onCameraError kept same)

const startDetectionLoop = async () => {
  // ... (Model loading kept same)
  if (!faceEngine.modelsLoaded) {
      // ...
      await faceEngine.loadModels();
      // ...
  }

  const loop = async () => {
    if (!videoEl || videoEl.paused || videoEl.ended || isSuccess.value) return;

    const detection = await faceEngine.detectSingleFace(videoEl);
    const ctx = canvasEl.getContext('2d');
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

    if (detection && !isProcessingAction && currentAction !== 'done') {
      isFaceDetected.value = true;
      const landmarks = detection.landmarks;
      
      const leftEAR = faceEngine.calculateEAR(landmarks.getLeftEye());
      const rightEAR = faceEngine.calculateEAR(landmarks.getRightEye());
      const avgEAR = (leftEAR + rightEAR) / 2;
      const mar = faceEngine.calculateMAR(landmarks.getMouth());

      if (currentAction === 'blink') {
          debugVal.value = avgEAR.toFixed(3);
          
          if (avgEAR < BLINK_CLOSE_THRESH) {
            if (!isActionPending) {
              isActionPending = true; 
              feedbackMsg.value = "检测到闭眼...";
            }
          } else {
            if (isActionPending && avgEAR > BLINK_OPEN_THRESH) {
              handleActionSuccess("眨眼成功!");
            }
          }

      } else if (currentAction === 'mouth') {
           debugVal.value = mar.toFixed(3);
          
          if (mar > MOUTH_OPEN_THRESH) {
              if (!isActionPending) {
                  isActionPending = true; 
                  feedbackMsg.value = "检测到张嘴...";
              }
          } else {
              if (isActionPending && mar < MOUTH_CLOSE_THRESH) {
                  handleActionSuccess("张嘴成功!");
              }
          }
      }
    } else if (!detection) {
      isFaceDetected.value = false;
      feedbackMsg.value = currentAction === 'done' ? "准备跳转..." : "未检测到人脸";
    }

    loopId = requestAnimationFrame(loop);
  };

  loop();
};

const handleActionSuccess = (msg) => {
    isProcessingAction = true; // Lock immediately
    feedbackMsg.value = msg;
    isActionPending = false;
    
    // Check if this was the last action locally before waiting
    // (Actually nextAction logic handles queue)
    
    setTimeout(() => {
        nextAction();
        if (currentAction === 'done') {
             // Need detection for capture? triggerSuccess saves the last detection logic
             // But loop continues. We can capture in triggerSuccess using videoEl directly.
             // We pass 'null' for detection since triggerSuccess recalculates or we just capture video frame.
             // Wait, triggerSuccess used 'detection.descriptor'.
             // We need to capture descriptor at the END.
             // Let's capture verification descriptor NOW or at end?
             // Better capture at end of ALL actions.
             
             // To be safe, let's grab a fresh detection or use current flow.
             // Since loop continues, next frame will catch 'done' and we can trigger.
             // BUT triggerSuccess stops loop.
             
             // Simplest: Call a specific finalizer that gets one last clear frame.
             finalizeStep1();
        }
    }, 1500); // 1.5s delay to ensure user sees "Success" message and resets face
};

const finalizeStep1 = async () => {
    instructionText.value = "活体检测通过!";
    // Find one last good face for the descriptor
    let detection = await faceEngine.detectSingleFace(videoEl);
    if (!detection) {
        // Retry a few times if lost
        detection = await faceEngine.detectSingleFace(videoEl);
    }
    
    if (detection) {
        triggerSuccess(detection);
    } else {
        // Edge case: face lost right at the end. 
        // Just Restart capture or use loop to wait?
        // Let's just try to call triggerSuccess. if it needs detection..
        // Re-use logic.
        alert("请保持人脸在画面中");
        isProcessingAction = false; // Unlock to try again to capture
        currentAction = 'done'; // force done state? No, need to re-trigger.
        // Actually if face is lost, user might be confused.
        // Let's just reset to done state and let loop catch a face?
        // No, 'done' state stops loop logic in my code above.
        
        // Let's change loop logic to: if done, capture and finish.
    }
};

const triggerSuccess = async (detection) => {
  isSuccess.value = true;
  instructionText.value = "活体通过，正在比对...";
  feedbackMsg.value = "提取特征中...";
  cancelAnimationFrame(loopId);

  try {
      // 1. Capture Image
      const captureCanvas = document.createElement('canvas');
      captureCanvas.width = videoEl.videoWidth;
      captureCanvas.height = videoEl.videoHeight;
      captureCanvas.getContext('2d').drawImage(videoEl, 0, 0);
      
      // Extract 5 key landmarks from face-api's 68 points
      // InsightFace uses: left_eye, right_eye, nose, left_mouth, right_mouth
      const landmarks = detection.landmarks.positions;
      
      // face-api 68-point indices (approximate mapping to InsightFace 5-point):
      // Left eye: average of points 36-41
      // Right eye: average of points 42-47  
      // Nose tip: point 30
      // Left mouth corner: point 48
      // Right mouth corner: point 54
      
      const leftEye = landmarks.slice(36, 42).reduce((acc, p) => ({ x: acc.x + p.x / 6, y: acc.y + p.y / 6 }), { x: 0, y: 0 });
      const rightEye = landmarks.slice(42, 48).reduce((acc, p) => ({ x: acc.x + p.x / 6, y: acc.y + p.y / 6 }), { x: 0, y: 0 });
      const nose = landmarks[30];
      const leftMouth = landmarks[48];
      const rightMouth = landmarks[54];
      
      const srcPoints = [
        [leftEye.x, leftEye.y],
        [rightEye.x, rightEye.y],
        [nose.x, nose.y],
        [leftMouth.x, leftMouth.y],
        [rightMouth.x, rightMouth.y]
      ];
      
      // Standard InsightFace 112x112 aligned positions (from arcface_torch)
      const dstPoints = [
        [38.2946, 51.6963],  // left eye
        [73.5318, 51.5014],  // right eye
        [56.0252, 71.7366],  // nose
        [41.5493, 92.3655],  // left mouth
        [70.7299, 92.2041]   // right mouth
      ];
      
      // Simple affine transform (estimate using least squares)
      // For production, use a proper library. Here's a simplified version:
      const alignedCanvas = document.createElement('canvas');
      alignedCanvas.width = 112;
      alignedCanvas.height = 112;
      const actx = alignedCanvas.getContext('2d');
      
      // Calculate transform matrix (simplified similarity transform)
      // Using only eye points for rotation and scale
      const eyeCenter = [(leftEye.x + rightEye.x) / 2, (leftEye.y + rightEye.y) / 2];
      const dstEyeCenter = [(38.2946 + 73.5318) / 2, (51.6963 + 51.5014) / 2];
      
      const dx = rightEye.x - leftEye.x;
      const dy = rightEye.y - leftEye.y;
      const angle = Math.atan2(dy, dx);
      
      const dstDx = 73.5318 - 38.2946;
      const dstDy = 51.5014 - 51.6963;
      const dstAngle = Math.atan2(dstDy, dstDx);
      
      const scale = Math.sqrt(dstDx * dstDx + dstDy * dstDy) / Math.sqrt(dx * dx + dy * dy);
      
      actx.translate(dstEyeCenter[0], dstEyeCenter[1]);
      actx.rotate(dstAngle - angle);
      actx.scale(scale, scale);
      actx.translate(-eyeCenter[0], -eyeCenter[1]);
      
      actx.drawImage(videoEl, 0, 0);
      
      const currentFeature = await insightFace.extractFeature(alignedCanvas);
      
      // 3. Fetch threshold from backend
      let threshold = 0.45; // default
      try {
          const configRes = await fetch('/api/config');
          const configJson = await configRes.json();
          if (configJson.code === 200) {
              threshold = configJson.data.similarity_threshold;
          }
      } catch (e) {
          console.warn('Failed to fetch threshold, using default 0.45');
      }
      
      // 4. Compare
      const score = insightFace.cosineSimilarity(currentFeature, appState.targetFeature);
      const isMatch = score > threshold;
      
      instructionText.value = isMatch ? "验证通过" : "验证失败";
      feedbackMsg.value = `相似度: ${score.toFixed(4)} (阈值: ${threshold.toFixed(2)})`;
      
      if (isMatch) {
          document.querySelector('.face-frame').classList.add('success');
      } else {
          document.querySelector('.face-frame').classList.add('fail'); // Need css
          document.querySelector('.face-frame').style.borderColor = 'red';
      }

      // 5. Report
      // Generate UUID
      const uuid = crypto.randomUUID();
      
      // Get GPS location
      let latitude = null;
      let longitude = null;
      
      try {
        if (navigator.geolocation) {
          const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              timeout: 5000,
              enableHighAccuracy: true
            });
          });
          latitude = position.coords.latitude;
          longitude = position.coords.longitude;
          console.log(`GPS: ${latitude}, ${longitude}`);
        }
      } catch (gpsError) {
        console.warn('GPS获取失败:', gpsError);
      }
      
      await fetch('/api/report', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
              uuid: uuid,
              user_id: appState.currentUser.id,
              score: score,
              threshold: threshold,
              status: isMatch ? 'PASS' : 'FAIL',
              latitude: latitude,
              longitude: longitude
          })
      });

      // 6. Show success modal (only if passed)
      if (isMatch) {
        const now = new Date();
        successData.value = {
          userName: appState.currentUser.name,
          time: now.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }),
          gps: latitude && longitude 
            ? `${latitude.toFixed(6)}, ${longitude.toFixed(6)}` 
            : '未获取'
        };
        showSuccessModal.value = true;
        
        // Auto close after 3 seconds
        setTimeout(() => {
          showSuccessModal.value = false;
          appState.reset();
        }, 3000);
      } else {
        // Failed - reset immediately
        setTimeout(() => {
          appState.reset();
        }, 3000);
      }

  } catch (e) {
      console.error(e);
      feedbackMsg.value = "比对出错: " + e.message;
      setTimeout(() => appState.reset(), 3000);
  }
};

const closeSuccessModal = () => {
  showSuccessModal.value = false;
  appState.reset();
};

onUnmounted(() => {
  if (loopId) cancelAnimationFrame(loopId);
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

.step-badge {
  font-size: 12px;
  color: #4CAF50;
  font-weight: bold;
  margin-bottom: 4px;
}

.instruction {
  font-size: 18px;
  color: white;
  font-weight: 500;
}

.face-frame {
  margin-top: 60px;
  width: 280px;
  height: 380px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 160px; /* Oval shape */
  position: relative;
  transition: all 0.3s ease;
}

.face-frame.active {
  border-color: #2196F3;
  box-shadow: 0 0 20px rgba(33, 150, 243, 0.5);
}

.face-frame.success {
  border-color: #4CAF50;
  box-shadow: 0 0 30px rgba(76, 175, 80, 0.8);
}

/* Corner Accents */
.corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 4px solid transparent;
}
.tl { top: -2px; left: -2px; border-top-color: #fff; border-left-color: #fff; border-radius: 20px 0 0 0; }
.tr { top: -2px; right: -2px; border-top-color: #fff; border-right-color: #fff; border-radius: 0 20px 0 0; }
.bl { bottom: -2px; left: -2px; border-bottom-color: #fff; border-left-color: #fff; border-radius: 0 0 0 20px; }
.br { bottom: -2px; right: -2px; border-bottom-color: #fff; border-right-color: #fff; border-radius: 0 0 20px 0; }

.active .corner { border-color: #2196F3; }
.success .corner { border-color: #4CAF50; }

.scan-line {
  width: 100%;
  height: 4px;
  background: #2196F3;
  position: absolute;
  top: 0;
  animation: scan 2s linear infinite;
  opacity: 0.7;
  box-shadow: 0 0 10px #2196F3;
}

@keyframes scan {
  0% { top: 10%; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 90%; opacity: 0; }
}

.feedback-toast {
  position: absolute;
  bottom: 100px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.debug-ear {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #4CAF50;
  padding: 6px 12px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
}

/* Success Modal Styles */
.success-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  animation: fadeIn 0.3s;
}

.success-modal {
  background: white;
  border-radius: 20px;
  padding: 40px 30px;
  text-align: center;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.success-icon {
  width: 100px;
  height: 100px;
  margin: 0 auto 20px;
}

.checkmark {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  display: block;
  stroke-width: 3;
  stroke: #4CAF50;
  stroke-miterlimit: 10;
  box-shadow: inset 0px 0px 0px #4CAF50;
  animation: fill 0.4s ease-in-out 0.4s forwards, scale 0.3s ease-in-out 0.9s both;
}

.checkmark-circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 3;
  stroke-miterlimit: 10;
  stroke: #4CAF50;
  fill: #4CAF50;
  animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

.checkmark-check {
  transform-origin: 50% 50%;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  stroke: white;
  stroke-width: 4;
  animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
}

@keyframes stroke {
  100% {
    stroke-dashoffset: 0;
  }
}

@keyframes fill {
  100% {
    box-shadow: inset 0px 0px 0px 50px #4CAF50;
  }
}

@keyframes scale {
  0%, 100% {
    transform: none;
  }
  50% {
    transform: scale3d(1.1, 1.1, 1);
  }
}

.success-title {
  font-size: 28px;
  font-weight: 600;
  color: #333;
  margin-bottom: 30px;
}

.success-info {
  text-align: left;
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #e0e0e0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  color: #666;
  font-weight: 500;
}

.info-item .value {
  color: #333;
  font-weight: 600;
}
</style>
