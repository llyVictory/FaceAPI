<template>
  <div class="app-container">
    <transition name="fade" mode="out-in">
      <div v-if="appState.currentStep === 0" class="welcome-screen" key="step0">
        <div class="hero-content">
          <h1>人脸考勤终端</h1>
          <p class="subtitle">Step 1: 活体检测 &nbsp; -> &nbsp; Step 2: 本地比对</p>
          
          <div class="custom-select-wrapper">
              <div class="custom-select" :class="{ 'active': showDropdown }">
                  <div class="select-trigger" @click.stop="toggleDropdown">
                      <span v-if="appState.currentUser" class="selected-user">
                          <span class="user-avatar">{{ appState.currentUser.name.charAt(0) }}</span>
                          {{ appState.currentUser.name }}
                      </span>
                      <span v-else class="placeholder">👤 请选择需要验证的人员</span>
                      <span class="arrow">▼</span>
                  </div>
                  <div v-if="showDropdown" class="select-options">
                      <div 
                          v-for="user in users" 
                          :key="user.id" 
                          class="select-option"
                          @click.stop="selectUser(user.id)"
                      >
                          <span class="user-avatar">{{ user.name.charAt(0) }}</span>
                          <span class="user-info">
                              <span class="user-name">{{ user.name }}</span>
                              <span class="user-id">ID: {{ user.id }}</span>
                          </span>
                      </div>
                      <div v-if="users.length === 0" class="select-option empty">
                          暂无用户，请先在管理系统中添加
                      </div>
                  </div>
              </div>
          </div>

          <button class="start-btn" @click="startDemo" :disabled="loading || !appState.currentUser">
            {{ loading ? '准备中...' : '开始考勤' }}
          </button>
          
          <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        </div>
      </div>

      <Step1_Liveness v-else-if="appState.currentStep === 1" key="step1" />
      
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { appState } from './state';
import Step1_Liveness from './views/Step1_Liveness.vue';
import { faceEngine } from './logic/face';
import { insightFace } from './logic/insightface';

const loading = ref(false);
const errorMsg = ref("");
const users = ref([]);
const showDropdown = ref(false);

// Close dropdown when clicking outside
onMounted(() => {
    window.addEventListener('click', () => {
        showDropdown.value = false;
    });
});
const selectedUserId = ref("");

// Load Users on Mount
onMounted(async () => {
    try {
        const res = await fetch('/api/users');
        const json = await res.json();
        if (json.code === 200) {
            users.value = json.data;
        }
    } catch (e) {
        errorMsg.value = "无法获取用户列表";
    }
});

const toggleDropdown = () => {
    showDropdown.value = !showDropdown.value;
};

const selectUser = async (userId) => {
    showDropdown.value = false;
    loading.value = true;
    try {
        // Fetch feature
        const res = await fetch(`/api/face/feature/${userId}`);
        const json = await res.json();
        if (json.code === 200) {
            appState.currentUser = users.value.find(u => u.id == userId);
            appState.targetFeature = new Float32Array(json.feature);
            errorMsg.value = "";
        } else {
             errorMsg.value = "获取特征失败: " + json.msg;
             appState.currentUser = null;
        }
    } catch(e) {
        errorMsg.value = "网络错误";
    } finally {
        loading.value = false;
    }
};

const startDemo = async () => {
  if (!appState.currentUser || !appState.targetFeature) {
      errorMsg.value = "请先选择需要验证的人员";
      return;
  }

  loading.value = true;
  errorMsg.value = "";
  try {
    // Load Face API models (Liveness)
    await faceEngine.loadModels();
    
    // Load InsightFace model (Verification)
    // Ensure 'w600k_mbf.onnx' is in public/models/
    await insightFace.loadModel('/models/w600k_mbf.onnx'); 

    appState.currentStep = 1;
  } catch (err) {
    errorMsg.value = "模型加载失败: " + err.message;
  } finally {
    loading.value = false;
  }
};
</script>

<style>
/* Global Resets */
:root {
  font-family: 'Inter', system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  color-scheme: dark;
}

body {
  margin: 0;
  background: #111;
  color: #fff;
  overflow: hidden; /* Prevent scrolling during camera view */
}

.app-container {
  width: 100vw;
  height: 100vh;
}

.welcome-screen {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
}

.hero-content {
  text-align: center;
  padding: 20px;
}

h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  background: -webkit-linear-gradient(#eee, #333);
  -webkit-background-clip: text;
  /* -webkit-text-fill-color: transparent; */
  color: white;
  text-shadow: 0 0 20px rgba(255,255,255,0.3);
}

.subtitle {
  color: #88bece;
  margin-bottom: 2rem;
  font-weight: 300;
}

/* Custom Select Styles */
.custom-select-wrapper {
  margin-bottom: 3rem;
  width: 100%;
  max-width: 400px;
}

.custom-select {
  position: relative;
  cursor: pointer;
}

.select-trigger {
  background: rgba(255,255,255,0.1);
  border: 2px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
}

.custom-select.active .select-trigger {
  border-color: #2196F3;
  background: rgba(33, 150, 243, 0.1);
}

.placeholder {
  color: #88bece;
  font-size: 1rem;
}

.selected-user {
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
  font-weight: 500;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2196F3, #1976D2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}

.arrow {
  color: #88bece;
  transition: transform 0.3s;
  font-size: 12px;
}

.custom-select.active .arrow {
  transform: rotate(180deg);
}

.select-options {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  right: 0;
  background: rgba(20, 30, 40, 0.95);
  border: 2px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  backdrop-filter: blur(20px);
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.select-option {
  padding: 15px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.select-option:last-child {
  border-bottom: none;
}

.select-option:hover {
  background: rgba(33, 150, 243, 0.2);
}

.select-option.empty {
  color: #88bece;
  justify-content: center;
  cursor: default;
}

.select-option.empty:hover {
  background: transparent;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  color: white;
  font-weight: 500;
  font-size: 1rem;
}

.user-id {
  color: #88bece;
  font-size: 0.85rem;
}

.start-btn {
  background: #2196F3;
  color: white;
  border: none;
  padding: 16px 40px;
  font-size: 1.2rem;
  font-weight: 600;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 0 20px rgba(33, 150, 243, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
}

.start-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 0 30px rgba(33, 150, 243, 0.6);
}

.start-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  margin-top: 20px;
  color: #ff6b6b;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
