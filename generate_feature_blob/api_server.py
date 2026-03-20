import os
import requests
import cv2
import numpy as np
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import database
from face_service import FaceService
from common import setup_logger

# 初始化 Logger
logger = setup_logger("API_Server")

load_dotenv()

app = FastAPI(
    title="Face Feature Update API",
    description="提供接口供Java调用进行人脸特征值同步和更新"
)

# Initialize InsightFace model
face_service = FaceService()
try:
    logger.info("Initializing FaceService...")
    face_service.init_model()
    logger.info("FaceService initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize FaceService: {str(e)}")

class UpdateFeatureRequest(BaseModel):
    yhbh: str

def get_pg_connection():
    """获取 PostgreSQL 连接"""
    schema = os.getenv("PG_SCHEMA", "views")
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "172.18.177.40"),
        port=os.getenv("PG_PORT", "15400"),
        user=os.getenv("PG_USER", "wgkq"),
        password=os.getenv("PG_PASSWORD", "Sdpei#@2026$#"),
        dbname=os.getenv("PG_DB", "cloudtop"),
        options=f"-c search_path={schema}"
    )

@app.post("/api/update_feature")
def update_feature(req: UpdateFeatureRequest):
    yhbh = req.yhbh
    logger.info(f"收到更新特征请求，学号/工号: {yhbh}")
    
    # 1. 查询 PostgreSQL 获取最新的 face_url
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        query = "SELECT face_url FROM v_user_face_kq WHERE yhbh = %s LIMIT 1"
        cursor.execute(query, (yhbh,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            logger.warning(f"找不到学号为 {yhbh} 的数据")
            raise HTTPException(status_code=404, detail=f"找不到学号为 {yhbh} 的人脸数据")
            
        new_face_url = result[0]
        if not new_face_url:
            logger.warning(f"学号 {yhbh} 的 face_url 为空")
            raise HTTPException(status_code=400, detail=f"学号 {yhbh} 在PostgreSQL中的 face_url 为空")
            
        logger.info(f"成功从 PostgreSQL 获取 face_url: {new_face_url}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"连接或查询 PostgreSQL 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"连接或查询 PostgreSQL 失败: {str(e)}")

    # 2. 覆盖本地 sch_kq 库的 v_user_face_kq 的 face_url
    try:
        database.update_source_face_url(yhbh, new_face_url)
        logger.info(f"成功更新本地库 {database.TABLE_SOURCE} 的 face_url")
    except Exception as e:
        logger.error(f"更新本地库 face_url 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新本地库 face_url 失败: {str(e)}")
        
    # 3. 下载这张人脸图片
    try:
        logger.info(f"开始下载人脸图片...")
        resp = requests.get(new_face_url, timeout=15)
        resp.raise_for_status()
        image_bytes = resp.content
    except Exception as e:
        logger.error(f"下载人脸图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载人脸图片失败: {str(e)}")
        
    # 转换为 cv2 格式图片 ( numpy 数组 )
    try:
        img_array = np.frombuffer(image_bytes, np.uint8)
        img_cv2 = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img_cv2 is None:
            raise ValueError("cv2无法解析下载的图片")
    except Exception as e:
        logger.error(f"图片数据转换失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片数据转换失败: {str(e)}")

    # 4. 生成人脸特征值
    logger.info("开始提取人脸特征...")
    feature, score, padding = face_service.get_feature(img_cv2)
    if feature is None:
        logger.error("照片尝试所有补边方案后均未检测到有效人脸")
        raise HTTPException(status_code=400, detail="提取失败：照片中未能检测到有效人脸")
        
    logger.info(f"特征提取成功, 置信度: {score:.4f}, 补边比例: {padding}")

    # 5. 根据学号把特征值更新到 kq_face_feature
    try:
        # database.save_target_feature 本身使用 INSERT ON DUPLICATE KEY UPDATE 实现覆盖/插入
        database.save_target_feature(user_id=yhbh, feature=feature, threshold=0.45)
        logger.info(f"成功将特征值保存到目标表 {database.TABLE_TARGET}")
    except Exception as e:
        logger.error(f"保存特征值到 kq_face_feature 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存特征值到目标库表失败: {str(e)}")
        
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "yhbh": yhbh,
            # "face_url": new_face_url,
            # "score": float(score),
            # "padding": float(padding)
        }
    }

if __name__ == "__main__":
    import uvicorn
    # 为了方便测试直接运行
    uvicorn.run("api_server:app", host="0.0.0.0", port=8071, reload=True)
