# 考勤系统更新说明 v2.0

## 🎉 新增功能

### 1. GPS 位置获取（H5 端）

- ✅ 每次考勤时自动获取 GPS 坐标
- ✅ 使用浏览器 Geolocation API
- ✅ 5 秒超时保护，失败不影响考勤流程
- ✅ 高精度模式（enableHighAccuracy）

### 2. 完整考勤记录（数据库）

新增字段：

- `uuid`: 唯一标识符（每次考勤生成）
- `user_name`: 用户姓名（冗余存储，便于查询）
- `threshold`: 当次使用的相似度阈值
- `latitude`: GPS 纬度
- `longitude`: GPS 经度
- `timestamp`: 考勤时间（自动生成）

### 3. 考勤记录查看（Admin Panel）

- ✅ 表格展示所有考勤记录
- ✅ 分页功能（每页 20 条）
- ✅ 状态高亮（通过/失败）
- ✅ GPS 坐标可点击跳转 Google Maps
- ✅ 时间格式化显示

## 📊 数据库变更

### 旧表结构

```sql
logs (
    id, user_id, score, status, timestamp
)
```

### 新表结构

```sql
logs (
    id, uuid, user_id, user_name, score, threshold, 
    status, latitude, longitude, timestamp
)
```

**⚠️ 重要提示**：

- 如果已有旧数据库，需要删除 `face_attendance.db` 让系统重新创建
- 或者手动执行 SQL 迁移（添加新字段）

## 🔧 API 变更

### 1. POST /api/report（更新）

**旧格式：**

```json
{
  "user_id": 1,
  "score": 0.75,
  "status": "PASS"
}
```

**新格式：**

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "score": 0.75,
  "threshold": 0.45,
  "status": "PASS",
  "latitude": 39.9042,
  "longitude": 116.4074
}
```

### 2. GET /api/logs（新增）

**请求参数：**

- `limit`: 每页条数（默认 100）
- `offset`: 偏移量（默认 0）

**响应示例：**

```json
{
  "code": 200,
  "data": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "1",
      "user_name": "张三",
      "score": 0.7532,
      "threshold": 0.45,
      "status": "PASS",
      "latitude": 39.9042,
      "longitude": 116.4074,
      "timestamp": "2026-02-13 10:30:15"
    }
  ]
}
```

## 🚀 部署步骤

### 1. 备份旧数据（如有需要）

```bash
cd /home/lly/FaceApi
cp face_attendance.db face_attendance.db.backup
```

### 2. 删除旧数据库（重新创建表结构）

```bash
rm face_attendance.db
```

### 3. 重启后端服务

```bash
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8070
```

### 4. 重启管理后台

```bash
cd admin-panel
npm run dev
```

### 5. 刷新 H5 页面

确保浏览器加载最新的 JavaScript 代码。

## 📱 H5 端使用说明

### GPS 权限

首次使用时，浏览器会弹出位置权限请求：

- **允许**：可以记录 GPS 坐标
- **拒绝**：考勤仍可正常进行，但 GPS 字段为空

### HTTPS 要求

GPS API 仅在 HTTPS 或 localhost 环境下可用。如果通过 IP 访问（如 `http://192.168.x.x`），部分浏览器可能无法获取 GPS。

## 🎨 Admin Panel 新界面

访问 `http://192.168.137.1:5174` 可看到：

1. **系统配置**：阈值调整
2. **添加新用户**：上传照片
3. **已录入人员**：用户列表
4. **📋 考勤记录**（新增）：
   - UUID 前 8 位
   - 姓名
   - 时间
   - 相似度
   - 阈值
   - 状态（通过/失败）
   - GPS 坐标（可点击查看地图）

## ✅ 测试清单

- [ ] H5 端考勤时是否弹出 GPS 权限请求
- [ ] 后端日志是否显示 GPS 坐标
- [ ] Admin Panel 考勤记录是否正常显示
- [ ] GPS 链接是否可以跳转到 Google Maps
- [ ] 分页功能是否正常
- [ ] 阈值是否正确记录

## 🐛 常见问题

**Q: GPS 一直显示"未获取"？**
A: 检查浏览器权限设置，或使用 HTTPS 访问。

**Q: 考勤记录显示"暂无记录"？**
A: 确认后端服务已重启，数据库表结构已更新。

**Q: UUID 重复错误？**
A: 浏览器不支持 `crypto.randomUUID()`，需升级浏览器版本。
