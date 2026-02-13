#!/bin/bash
# 修复文件权限脚本

cd /home/lly/FaceApi

# 修复数据库文件权限
if [ -f "face_attendance.db" ]; then
    sudo chown lly:lly face_attendance.db
    sudo chmod 664 face_attendance.db
    echo "✓ 数据库权限已修复"
fi

# 修复 uploads 目录权限
if [ -d "uploads" ]; then
    sudo chown -R lly:lly uploads
    sudo chmod 775 uploads
    echo "✓ uploads 目录权限已修复"
fi

# 如果 uploads 不存在，创建它
if [ ! -d "uploads" ]; then
    mkdir -p uploads
    chmod 775 uploads
    echo "✓ uploads 目录已创建"
fi

echo "✓ 权限修复完成！"
