<template>
  <div class="section">
    <h2>添加新用户</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label>姓名</label>
        <input type="text" v-model="userName" placeholder="请输入姓名" required>
      </div>
      <div class="form-group">
        <label>上传照片</label>
        <div class="file-input-wrapper">
          <input 
            type="file" 
            ref="fileInput"
            @change="handleFileChange" 
            accept="image/*" 
            required
          >
          <div class="file-input-label">
            <span>{{ fileName }}</span>
          </div>
        </div>
      </div>
      <button type="submit" class="btn btn-primary" :disabled="uploading">
        {{ uploading ? '上传中...' : '提取特征并入库' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['user-added'])

const userName = ref('')
const fileName = ref('点击选择照片或拖拽到此处')
const fileInput = ref(null)
const uploading = ref(false)

function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    fileName.value = file.name
  }
}

async function handleSubmit() {
  const file = fileInput.value.files[0]
  if (!file) {
    alert('请选择照片')
    return
  }
  
  uploading.value = true
  const formData = new FormData()
  formData.append('name', userName.value)
  formData.append('file', file)
  
  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      body: formData
    })
    const json = await res.json()
    
    if (json.code === 200) {
      emit('user-added', userName.value)
      userName.value = ''
      fileName.value = '点击选择照片或拖拽到此处'
      fileInput.value.value = ''
    } else {
      alert(json.msg)
    }
  } catch (e) {
    alert('上传失败，请检查服务器连接')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.section {
  background: #f8f9fa;
  padding: 30px;
  border-radius: 12px;
  margin-bottom: 30px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
  color: #555;
}

input[type="text"] {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s;
}

input[type="text"]:focus {
  outline: none;
  border-color: #667eea;
}

.file-input-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
}

.file-input-wrapper input[type="file"] {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.file-input-label {
  display: block;
  padding: 12px;
  background: white;
  border: 2px dashed #667eea;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.file-input-label:hover {
  background: #f0f4ff;
  border-color: #764ba2;
}

.btn {
  padding: 12px 30px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
