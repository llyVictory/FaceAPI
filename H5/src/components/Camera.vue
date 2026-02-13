<template>
  <div class="camera-container">
    <video ref="video" autoplay playsinline muted class="camera-video"></video>
    <canvas ref="canvas" class="camera-overlay"></canvas>
    <div v-if="loading" class="camera-loading">
      <div class="spinner"></div>
      <p>启动摄像头...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const video = ref(null);
const canvas = ref(null);
const loading = ref(true);
const stream = ref(null);

const emit = defineEmits(['ready', 'error']);

const startCamera = async () => {
  try {
    const constraints = {
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: 'user' // Front camera
      },
      audio: false
    };
    
    stream.value = await navigator.mediaDevices.getUserMedia(constraints);
    video.value.srcObject = stream.value;
    
    // Wait for video to be ready
    await new Promise((resolve) => {
      video.value.onloadedmetadata = () => {
        resolve();
      };
    });

    video.value.play();
    loading.value = false;

    // Adjust canvas size to match video
    canvas.value.width = video.value.videoWidth;
    canvas.value.height = video.value.videoHeight;

    emit('ready', { video: video.value, canvas: canvas.value });

  } catch (err) {
    console.error('Camera Error:', err);
    loading.value = false;
    emit('error', err);
  }
};

const stopCamera = () => {
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop());
    stream.value = null;
  }
};

onMounted(() => {
  startCamera();
});

onUnmounted(() => {
  stopCamera();
});

defineExpose({
  video,
  canvas
});
</script>

<style scoped>
.camera-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.camera-video {
  /* Cover ensures it fills the container while maintaining aspect ratio via cropping */
  /* But for analysis, we might want contain to see full FOV or just mapping coordinates correctly. */
  /* For this demo, let's use object-fit: cover for full screen immersive feel, 
     but we must be careful with coordinate mapping if we do that. 
     To simplify coordinate mapping for face-api, we usually just fit the video size 
     or calculate the scale. */
  width: 100%;
  height: 100%;
  object-fit: cover; 
}

/* If object-fit is cover, the actual video pixels are cropped. 
   Drawing on top requires matching the crop.
   Simplest approach for logic is just to show the full video (object-fit: contain) 
   or accept that we analyze the full video but only show part of it.*/

/* Let's stick to contain for accuracy of debug overlay, or carefully handle resizing.
   For immersion, simple CSS tricks: center the video. */
.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover; 
  /* Mirror the video for natural selfie experience */
  transform: scaleX(-1);
}

.camera-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
  /* Mirror the canvas to match the mirrored video */
  transform: scaleX(-1);
}

.camera-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s ease-in-out infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
