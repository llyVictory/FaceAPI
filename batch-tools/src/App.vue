<template>
  <div class="panel">
    <div class="header">
      <h1>人脸特征批量生成 (从 v_user_face_kq 到 kq_face_feature)</h1>
      <p>执行独立的大规模照片数据拉取、解析、并提存为 512 维度特征</p>
    </div>
    
    <div class="controls">
      <button 
        @click="startBatch" 
        :disabled="isRunning"
        class="btn-primary"
      >
        <span v-if="!isRunning">一键批量完成</span>
        <span v-else>正在同步处理中...</span>
      </button>
    </div>

    <!-- 状态跑马灯和统计看板 -->
    <div class="status-dashboard" v-if="taskData.total > 0 || isRunning">
      <div class="stat-card">
        <div class="stat-value">{{ taskData.total }}</div>
        <div class="stat-label">总任务数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ taskData.processed }}</div>
        <div class="stat-label">已处理</div>
      </div>
      <div class="stat-card success">
        <div class="stat-value">{{ taskData.success }}</div>
        <div class="stat-label">成功提取</div>
      </div>
      <div class="stat-card danger">
        <div class="stat-value">{{ taskData.failed }}</div>
        <div class="stat-label">失败跳过</div>
      </div>
    </div>
    
    <!-- 实时进度条 -->
    <div class="progress-bar-container" v-if="taskData.total > 0 || isRunning">
      <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
    </div>

    <!-- 实时日志输出控制台 -->
    <div class="logs-container">
      <h3>运行日志 <span v-if="isRunning" class="pulsing-dot"></span></h3>
      <div class="logs-list" ref="logsContainer">
        <div 
          v-for="(log, index) in logsSequence" 
          :key="index"
          :class="['log-item', { 'log-error': log.includes('失败') || log.includes('错误'), 'log-success': log.includes('成功') }]"
        >
          <span class="log-time">{{ new Date().toLocaleTimeString() }}</span>
          <span class="log-msg">{{ log }}</span>
        </div>
        <div v-if="logsSequence.length === 0" class="log-empty">等待由于执行产生的实时日志流输入...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const isRunning = ref(false)
const taskData = ref({
  total: 0,
  processed: 0,
  success: 0,
  failed: 0,
})
const logsSequence = ref([])
const logsContainer = ref(null)

let eventSource = null

const progressPercent = computed(() => {
  if (taskData.value.total === 0) return 0
  return Math.min(100, Math.round((taskData.value.processed / taskData.value.total) * 100))
})

const scrollToBottom = async () => {
  await nextTick()
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
}

const startBatch = async () => {
  if (isRunning.value) return
  
  // 初始化状态
  isRunning.value = true
  taskData.value = {
    total: 0,
    processed: 0,
    success: 0,
    failed: 0,
  }
  logsSequence.value = ['初始化连接... 等待服务器响应流']
  
  // 通过 SSE (EventSource) 开启一个双向通道，阻塞等待服务端长连接推数
  eventSource = new EventSource('http://localhost:8080/api/batch_feature_stream')
  
  eventSource.onopen = () => {
    logsSequence.value.push('后端服务器已连接，执行中...');
    scrollToBottom()
  }

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      // 更新大盘统计数据
      taskData.value.total = data.total
      taskData.value.processed = data.processed
      taskData.value.success = data.success
      taskData.value.failed = data.failed
      
      // 更新单条实时日志
      if (data.latest_log) {
        logsSequence.value.push(data.latest_log)
        scrollToBottom()
      }
      
      // 处理完成或中断
      if (data.status === 'finished') {
        isRunning.value = false
        eventSource.close()
        logsSequence.value.push('流式响应连接正常关闭。')
        scrollToBottom()
      }
      
    } catch (e) {
      console.error('SSE Error parsing event', e)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE Connection Error:', error)
    if (isRunning.value) { // 意味着是非正常切断
      logsSequence.value.push('流式连接异常断开或后端未就绪。请检查后端状态。')
      isRunning.value = false
      eventSource.close()
      scrollToBottom()
    }
  }
}
</script>

<style scoped>
.panel {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}

.header {
  margin-bottom: 30px;
  border-bottom: 2px solid #edf2f7;
  padding-bottom: 20px;
}

.header h1 {
  font-size: 1.5rem;
  color: #1a202c;
  margin-bottom: 8px;
}

.header p {
  color: #718096;
  font-size: 0.95rem;
}

.controls {
  margin-bottom: 25px;
  display: flex;
  justify-content: center;
}

.btn-primary {
  background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
  color: white;
  border: none;
  padding: 14px 40px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(66, 153, 225, 0.4);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(66, 153, 225, 0.5);
}

.btn-primary:disabled {
  background: #cbd5e0;
  color: #a0aec0;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.status-dashboard {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 25px;
}

.stat-card {
  background: #f7fafc;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
  border: 1px solid #e2e8f0;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card.success {
  background: #f0fff4;
  border-color: #c6f6d5;
}

.stat-card.success .stat-value {
  color: #38a169;
}

.stat-card.danger {
  background: #fff5f5;
  border-color: #fed7d7;
}

.stat-card.danger .stat-value {
  color: #e53e3e;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: #2d3748;
  margin-bottom: 6px;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #718096;
  font-weight: 500;
}

/* 进度条 */
.progress-bar-container {
  height: 12px;
  background: #edf2f7;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 25px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #48bb78, #38a169);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 日志控制台 */
.logs-container {
  background: #0f172a;
  border-radius: 10px;
  padding: 20px;
  color: #cbd5e1;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);
}

.logs-container h3 {
  color: #f8fafc;
  margin-bottom: 15px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
}

.pulsing-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background-color: #4ade80;
  border-radius: 50%;
  margin-left: 10px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.logs-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.logs-list::-webkit-scrollbar {
  width: 8px;
}

.logs-list::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 4px;
}

.logs-list::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 4px;
}

.logs-list::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

.log-item {
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
  background: rgba(255,255,255,0.03);
  border-left: 3px solid transparent;
  display: flex;
  line-height: 1.4;
}

.log-time {
  color: #64748b;
  margin-right: 12px;
  flex-shrink: 0;
  font-size: 11px;
  margin-top: 1px;
}

.log-empty {
  color: #64748b;
  font-style: italic;
  font-size: 13px;
  padding: 10px 0;
}

.log-success {
  color: #86efac;
  background: rgba(74, 222, 128, 0.05);
  border-left-color: #4ade80;
}

.log-error {
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.05);
  border-left-color: #f87171;
}
</style>
