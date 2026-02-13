<template>
  <div class="admin-container">
    <div class="header">
      <h1>人脸考勤管理系统</h1>
      <p>上传照片 · 自动提取特征 · 持久化存储</p>
    </div>
    
    <div class="content">
      <!-- System Configuration -->
      <ConfigPanel @config-updated="showToast('配置已更新', 'success')" />
      
      <!-- Upload Section -->
      <UploadPanel @user-added="handleUserAdded" />
      
      <!-- User List -->
      <UserList ref="userListRef" />
    </div>
    
    <!-- Toast Notification -->
    <div v-if="toast.show" :class="['toast', toast.type]">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import ConfigPanel from './components/ConfigPanel.vue'
import UploadPanel from './components/UploadPanel.vue'
import UserList from './components/UserList.vue'

const userListRef = ref(null)
const toast = reactive({
  show: false,
  message: '',
  type: 'success'
})

function showToast(message, type = 'success') {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 3000)
}

function handleUserAdded(userName) {
  showToast(`${userName} 添加成功！特征已提取并入库`)
  userListRef.value?.loadUsers()
}
</script>

<style scoped>
.admin-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  overflow: hidden;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  text-align: center;
}

.header h1 {
  font-size: 2rem;
  margin-bottom: 10px;
}

.header p {
  opacity: 0.9;
}

.content {
  padding: 30px;
}

.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: white;
  padding: 15px 25px;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.2);
  z-index: 1000;
  animation: slideIn 0.3s;
}

.toast.success {
  border-left: 4px solid #27ae60;
}

.toast.error {
  border-left: 4px solid #e74c3c;
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
