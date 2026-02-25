import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import shutil
import os
import cv2
import numpy as np
import urllib.request
import traceback
import json
import database
from face_service import FaceService
from common import setup_logger, load_config, save_config

# Setup logger for Admin Service
logger = setup_logger("Admin_Service")

app = FastAPI(title="Face Attendance Admin API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded photos
os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Initialize Services (Only Admin needs FaceService for registration)
face_service = FaceService()
config = load_config()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Admin Backend...")
    logger.info("Initializing Face Model for registration...")
    face_service.init_model()
    database.init_db()
    logger.info("Admin Backend Ready.")

@app.get("/")
def read_root():
    return {"message": "Face Attendance Admin Backend is Running"}

# --- Admin Endpoints ---

@app.get("/api/users")
def get_users():
    try:
        users = database.get_users()
        return {"code": 200, "data": users}
    except Exception as e:
        logger.error(f"Get Users Error: {e}")
        return {"code": 500, "msg": str(e)}

@app.post("/api/users")
async def add_user(
    name: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"code": 400, "msg": "Invalid Image"}
            
        feature = face_service.get_feature(img)
        if feature is None:
            return {"code": 400, "msg": "No face detected"}
            
        file_ext = os.path.splitext(file.filename)[1]
        import time
        timestamp = int(time.time() * 1000)
        filename = f"{name}_{timestamp}{file_ext}"
        file_path = os.path.join("uploads", filename)
        
        with open(file_path, "wb") as f:
            f.write(contents)
            
        user_id = database.add_user(name, feature, file_path)
        logger.info(f"Admin: Added user {name} (ID: {user_id})")
        
        return {"code": 200, "msg": "Success", "data": {"id": user_id, "name": name}}
    except Exception as e:
        logger.error(f"Add User Error: {e}")
        return {"code": 500, "msg": str(e)}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    try:
        success = database.delete_user(user_id)
        if success:
            logger.info(f"Admin: Deleted user ID: {user_id}")
            return {"code": 200, "msg": "Deleted successfully"}
        else:
            return {"code": 404, "msg": "User not found"}
    except Exception as e:
        logger.error(f"Delete User Error: {e}")
        return {"code": 500, "msg": str(e)}

@app.get("/api/logs")
def get_logs(limit: int = 100, offset: int = 0):
    try:
        logs = database.get_logs(limit=limit, offset=offset)
        return {"code": 200, "data": logs}
    except Exception as e:
        logger.error(f"Get Logs Error: {e}")
        return {"code": 500, "msg": str(e)}

@app.get("/api/config")
def get_config():
    current_config = load_config()
    return {"code": 200, "data": current_config}

class ConfigUpdateModel(BaseModel):
    similarity_threshold: float

@app.put("/api/config")
async def update_config(config_in: ConfigUpdateModel):
    try:
        if not 0 <= config_in.similarity_threshold <= 1:
            return {"code": 400, "msg": "Threshold must be between 0 and 1"}
        
        current_config = load_config()
        current_config["similarity_threshold"] = config_in.similarity_threshold
        save_config(current_config)
        logger.info(f"Admin: Updated similarity threshold to {config_in.similarity_threshold}")
        return {"code": 200, "msg": "Config updated"}
    except Exception as e:
        logger.error(f"Update Config Error: {e}")
        return {"code": 500, "msg": str(e)}

def feature_generation_stream():
    """Generator for SSE that streams the processing state"""
    state_data = {
        "status": "running",
        "total": 0,
        "processed": 0,
        "success": 0,
        "failed": 0,
        "latest_log": ""
    }
    
    def format_sse(data_dict):
        # Format the event for SSE
        return f"data: {json.dumps(data_dict, ensure_ascii=False)}\n\n"
        
    try:
        users = database.get_source_faces()
        state_data["total"] = len(users)
        state_data["latest_log"] = f"开始处理，共需处理 {state_data['total']} 条数据..."
        yield format_sse(state_data)
        
        for user in users:
            try:
                yhbh = user["yhbh"]
                url = user["face_url"]
                
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=10)
                image_bytes = resp.read()
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise Exception("无法解析图片")
                
                feature = face_service.get_feature(img)
                if feature is None:
                    raise Exception("未检测到人脸")
                
                database.save_target_feature(user_id=yhbh, feature=feature, threshold=0.45)
                
                state_data["success"] += 1
                state_data["processed"] += 1
                state_data["latest_log"] = f"成功: 学号 {yhbh} 提取并保存成功"
                yield format_sse(state_data)
                
            except Exception as e:
                state_data["failed"] += 1
                state_data["processed"] += 1
                yhbh = user.get('yhbh', '未知学号')
                state_data["latest_log"] = f"失败: 学号 {yhbh} 提取失败 -> {str(e)}"
                yield format_sse(state_data)
                
    except Exception as e:
        logger.error(f"Batch Feature Stream Error: {traceback.format_exc()}")
        state_data["latest_log"] = f"系统致命错误: {str(e)}"
        yield format_sse(state_data)
        
    finally:
        state_data["status"] = "finished"
        state_data["latest_log"] = "所有任务处理完成"
        yield format_sse(state_data)


@app.get("/api/batch_feature_stream")
def get_batch_feature_stream():
    """SSE endpoint for batch feature generation"""
    return StreamingResponse(
        feature_generation_stream(), 
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
