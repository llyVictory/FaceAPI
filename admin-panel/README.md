# 人脸考勤管理后台 (Vue)

## 项目结构

```
admin-panel/
├── src/
│   ├── components/
│   │   ├── ConfigPanel.vue    # 系统配置（阈值管理）
│   │   ├── UploadPanel.vue    # 用户上传
│   │   └── UserList.vue       # 用户列表
│   ├── App.vue                # 主组件
│   ├── main.js                # 入口文件
│   └── style.css              # 全局样式
├── index.html
├── vite.config.js             # Vite 配置（含后端代理）
└── package.json
```

## 启动方式

### 1. 启动后端（Python）

```bash
cd /home/lly/FaceApi
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8070
```

### 2. 启动管理后台（Vue）

```bash
cd /home/lly/FaceApi/admin-panel
npm run dev
```

访问地址：`http://192.168.137.1:5174`（Windows 热点 IP）

## 功能特性

✅ **系统配置**

- 动态调整相似度阈值（0-1）
- 实时保存到后端 `config.json`
- 滑块 + 数字输入双向绑定

✅ **用户管理**

- 上传照片自动提取 512 维特征
- 特征持久化到 SQLite 数据库
- 用户列表展示与删除

✅ **响应式设计**

- 卡片式布局
- 渐变色主题
- Toast 通知

## 注意事项

1. **端口转发**：确保 Windows 已配置端口转发（5174 和 8070）
2. **阈值持久化**：已在后端实现，保存到 `config.json`
3. **网络访问**：Vite 已配置 `--host 0.0.0.0`，手机可访问
