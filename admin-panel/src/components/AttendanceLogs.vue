<template>
  <div class="section">
    <h2>考勤记录</h2>
    
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>UUID</th>
            <th>姓名</th>
            <th>时间</th>
            <th>相似度</th>
            <th>阈值</th>
            <th>状态</th>
            <th>纬度</th>
            <th>经度</th>
            <th>地图</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="logs.length === 0">
            <td colspan="9" class="empty">暂无记录</td>
          </tr>
          <tr v-for="log in logs" :key="log.uuid" :class="{ 'pass': log.status === 'PASS', 'fail': log.status === 'FAIL' }">
            <td class="uuid">{{ log.uuid.substring(0, 8) }}...</td>
            <td class="name">{{ log.user_name || `用户${log.user_id}` }}</td>
            <td class="time">{{ formatTime(log.timestamp) }}</td>
            <td class="score">{{ log.score?.toFixed(4) || 'N/A' }}</td>
            <td class="threshold">{{ log.threshold?.toFixed(2) || 'N/A' }}</td>
            <td class="status">
              <span :class="['badge', log.status.toLowerCase()]">
                {{ log.status === 'PASS' ? '通过' : '失败' }}
              </span>
            </td>
            <td class="gps-coord">
              <span v-if="log.latitude">{{ log.latitude.toFixed(6) }}</span>
              <span v-else class="no-gps">-</span>
            </td>
            <td class="gps-coord">
              <span v-if="log.longitude">{{ log.longitude.toFixed(6) }}</span>
              <span v-else class="no-gps">-</span>
            </td>
            <td class="gps-map">
              <span v-if="log.latitude && log.longitude">
                <a :href="`https://www.google.com/maps?q=${log.latitude},${log.longitude}`" target="_blank" class="map-link">
                  📍 查看
                </a>
              </span>
              <span v-else class="no-gps">-</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div class="pagination">
      <button @click="prevPage" :disabled="currentPage === 0" class="btn btn-secondary">
        ← 上一页
      </button>
      <span class="page-info">第 {{ currentPage + 1 }} 页</span>
      <button @click="nextPage" :disabled="logs.length < pageSize" class="btn btn-secondary">
        下一页 →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const logs = ref([])
const currentPage = ref(0)
const pageSize = 20

async function loadLogs() {
  try {
    const res = await fetch(`/api/logs?limit=${pageSize}&offset=${currentPage.value * pageSize}`)
    const json = await res.json()
    if (json.code === 200) {
      logs.value = json.data
    }
  } catch (e) {
    console.error('Failed to load logs:', e)
  }
}

function formatTime(timestamp) {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function prevPage() {
  if (currentPage.value > 0) {
    currentPage.value--
    loadLogs()
  }
}

function nextPage() {
  currentPage.value++
  loadLogs()
}

onMounted(() => {
  loadLogs()
})

defineExpose({ loadLogs })
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

.table-container {
  overflow-x: auto;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

th {
  padding: 15px;
  text-align: left;
  font-weight: 600;
  font-size: 14px;
}

tbody tr {
  border-bottom: 1px solid #e0e0e0;
  transition: background 0.2s;
}

tbody tr:hover {
  background: #f8f9fa;
}

tbody tr.pass {
  background: rgba(39, 174, 96, 0.05);
}

tbody tr.fail {
  background: rgba(231, 76, 60, 0.05);
}

td {
  padding: 12px 15px;
  font-size: 14px;
  color: #555;
}

.empty {
  text-align: center;
  color: #999;
  padding: 40px;
}

.uuid {
  font-family: monospace;
  color: #999;
  font-size: 12px;
}

.name {
  font-weight: 600;
  color: #333;
}

.time {
  color: #666;
  font-size: 13px;
}

.score, .threshold {
  font-family: monospace;
  color: #667eea;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.badge.pass {
  background: #d4edda;
  color: #155724;
}

.badge.fail {
  background: #f8d7da;
  color: #721c24;
}

.gps-coord {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.gps-map .map-link {
  color: #667eea;
  text-decoration: none;
  font-size: 13px;
}

.gps-map .map-link:hover {
  text-decoration: underline;
}

.no-gps {
  color: #999;
  font-size: 13px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 20px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: #666;
  font-size: 14px;
}
</style>
