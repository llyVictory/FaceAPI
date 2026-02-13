<template>
  <div class="section">
    <h2>系统配置</h2>
    <div class="form-group">
      <label>相似度阈值 (0-1)</label>
      <div class="threshold-control">
        <input 
          type="range" 
          v-model.number="threshold" 
          min="0" 
          max="1" 
          step="0.01"
          class="slider"
        >
        <input 
          type="number" 
          v-model.number="threshold" 
          min="0" 
          max="1" 
          step="0.01"
          class="number-input"
        >
        <button @click="saveConfig" class="btn btn-primary">保存</button>
      </div>
      <p class="hint">
        建议值：0.45-0.55。值越高越严格，误识率越低但拒识率越高。
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['config-updated'])
const threshold = ref(0.45)

onMounted(async () => {
  try {
    const res = await fetch('/api/config')
    const json = await res.json()
    if (json.code === 200) {
      threshold.value = json.data.similarity_threshold
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
})

async function saveConfig() {
  if (threshold.value < 0 || threshold.value > 1) {
    alert('阈值必须在 0-1 之间')
    return
  }
  
  try {
    const res = await fetch('/api/config', {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ similarity_threshold: threshold.value })
    })
    const json = await res.json()
    
    if (json.code === 200) {
      emit('config-updated')
    } else {
      alert(json.msg)
    }
  } catch (e) {
    alert('更新失败')
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

.threshold-control {
  display: flex;
  gap: 10px;
  align-items: center;
}

.slider {
  flex: 1;
  height: 8px;
  border-radius: 5px;
  background: #ddd;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
}

.number-input {
  width: 100px;
  padding: 8px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
}

.number-input:focus {
  outline: none;
  border-color: #667eea;
}

.btn {
  padding: 8px 20px;
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

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.hint {
  margin-top: 10px;
  color: #666;
  font-size: 14px;
}
</style>
