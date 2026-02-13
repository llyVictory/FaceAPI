<template>
  <div class="qr-helper" v-if="appState.currentStep === 2 && !hidden">
    <div class="qr-box">
      <button class="close-btn" @click="hidden = true">×</button>
      <p>测试用二维码</p>
      <img :src="qrDataUrl" alt="Demo QR" />
      <p class="small">请用另一台手机拍照保存，或打印此码进行 Step 2 验证</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import QRCode from 'qrcode';
import { appState } from '../state';

const qrDataUrl = ref('');
const hidden = ref(false);

// Generate static QR for demo
QRCode.toDataURL('博文楼101', { errorCorrectionLevel: 'H' }, (err, url) => {
  if (!err) qrDataUrl.value = url;
});
</script>

<style scoped>
.qr-helper {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: white;
  padding: 10px;
  border-radius: 8px;
  z-index: 999;
  text-align: center;
  color: black;
  opacity: 0.9;
  transform: scale(0.8);
  transform-origin: bottom right;
}

.qr-box {
  position: relative;
}

.qr-box img {
  width: 120px;
  height: 120px;
}

.small {
  font-size: 10px;
  max-width: 120px;
}

.close-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: #f44336;
  color: white;
  font-size: 18px;
  line-height: 20px;
  cursor: pointer;
  padding: 0;
}
</style>
