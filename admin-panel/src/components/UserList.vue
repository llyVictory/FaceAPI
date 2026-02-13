<template>
  <div class="user-list">
    <h2>已录入人员 ({{ users.length }})</h2>
    <div class="user-grid">
      <div v-if="users.length === 0" class="empty">
        暂无用户
      </div>
      <div v-for="user in users" :key="user.id" class="user-card">
        <div class="user-avatar">{{ user.name.charAt(0) }}</div>
        <div class="user-name">{{ user.name }}</div>
        <div class="user-id">ID: {{ user.id }}</div>
        <button @click="deleteUser(user)" class="btn btn-danger">
          删除
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const users = ref([])

async function loadUsers() {
  try {
    const res = await fetch('/api/users')
    const json = await res.json()
    if (json.code === 200) {
      users.value = json.data
    }
  } catch (e) {
    console.error('Failed to load users:', e)
  }
}

async function deleteUser(user) {
  if (!confirm(`确定要删除 ${user.name} 吗？`)) return
  
  try {
    const res = await fetch(`/api/users/${user.id}`, { method: 'DELETE' })
    const json = await res.json()
    if (json.code === 200) {
      loadUsers()
    } else {
      alert(json.msg)
    }
  } catch (e) {
    alert('删除失败')
  }
}

onMounted(() => {
  loadUsers()
})

defineExpose({ loadUsers })
</script>

<style scoped>
.user-list h2 {
  margin-bottom: 20px;
  color: #333;
}

.user-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
}

.empty {
  grid-column: 1 / -1;
  text-align: center;
  color: #999;
  padding: 40px;
}

.user-card {
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s;
}

.user-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
  transform: translateY(-5px);
}

.user-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
  margin: 0 auto 15px;
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 5px;
}

.user-id {
  font-size: 14px;
  color: #999;
  margin-bottom: 15px;
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

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-danger:hover {
  background: #c0392b;
}
</style>
