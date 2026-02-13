import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import shutil
import os
import cv2
import numpy as np
import logging
import sys
import json
from face_service import FaceService
import database

# Global configuration
CONFIG = {
    "similarity_threshold": 0.45
}
CONFIG_FILE = "config.json"

def load_config():
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            CONFIG.update(json.load(f))

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(CONFIG, f, indent=2)

# --- Logging Configuration ---
logger = logging.getLogger("FaceService")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("log.file", mode='a', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

app = FastAPI(title="Face Recognition Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (uploaded photos + frontend models)
os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")
# If we want to serve models from backend too
# app.mount("/models", StaticFiles(directory="H5/public/models"), name="models") 

# Initialize Services
face_service = FaceService()

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Face Model...")
    face_service.init_model()
    logger.info("Initializing Database...")
    database.init_db()
    logger.info("Loading Configuration...")
    load_config()
    logger.info(f"Similarity Threshold: {CONFIG['similarity_threshold']}")

@app.get("/")
def read_root():
    return {"message": "Face Recognition Backend (SQLite) is Running"}

# --- User Management API ---

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
        # 1. Read Image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"code": 400, "msg": "Invalid Image"}
            
        # 2. Extract Feature
        feature = face_service.get_feature(img)
        if feature is None:
            return {"code": 400, "msg": "No face detected"}
            
        # 3. Save Image locally
        file_ext = os.path.splitext(file.filename)[1]
        timestamp = int(os.times()[4] * 10000) # Simple unique suffix
        filename = f"{name}_{timestamp}{file_ext}"
        file_path = os.path.join("uploads", filename)
        
        with open(file_path, "wb") as f:
            f.write(contents)
            
        # 4. Save to DB
        user_id = database.add_user(name, feature, file_path)
        logger.info(f"Added user: {name} (ID: {user_id})")
        
        return {"code": 200, "msg": "Success", "data": {"id": user_id, "name": name}}
        
    except Exception as e:
        logger.error(f"Add User Error: {e}")
        return {"code": 500, "msg": str(e)}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    try:
        success = database.delete_user(user_id)
        if success:
            logger.info(f"Deleted user ID: {user_id}")
            return {"code": 200, "msg": "Deleted successfully"}
        else:
            return {"code": 404, "msg": "User not found"}
    except Exception as e:
        logger.error(f"Delete User Error: {e}")
        return {"code": 500, "msg": str(e)}

# --- Feature Sync API (For H5) ---

@app.get("/api/face/feature/{user_id}")
async def get_feature(user_id: int):
    """
    Get 512-d feature vector for a specific user ID
    """
    try:
        feature = database.get_user_feature(user_id)
        if feature is not None:
             # Identify current user by ID, need name too? 
             # For 1:1, we just need feature.
             return {
                "code": 200,
                "userId": user_id,
                "feature": feature.tolist() 
             }
        else:
            return {"code": 404, "msg": "User feature not found"}
    except Exception as e:
        logger.error(f"Get Feature Error: {e}")
        return {"code": 500, "msg": str(e)}

from pydantic import BaseModel

class ReportModel(BaseModel):
    user_id: int
    score: float
    status: str
    address: Optional[str] = None

@app.post("/api/report")
async def report_log(report: ReportModel):
    try:
        database.add_log(str(report.user_id), report.score, report.status)
        logger.info(f"Report: User={report.user_id}, Score={report.score:.4f}, Status={report.status}")
        return {"code": 200, "msg": "Log saved"}
    except Exception as e:
        logger.error(f"Report Error: {e}")
        return {"code": 500, "msg": str(e)}

# --- Configuration API ---

class ConfigUpdateModel(BaseModel):
    similarity_threshold: float

@app.get("/api/config")
def get_config():
    return {"code": 200, "data": CONFIG}

@app.put("/api/config")
async def update_config(config: ConfigUpdateModel):
    try:
        if not 0 <= config.similarity_threshold <= 1:
            return {"code": 400, "msg": "Threshold must be between 0 and 1"}
        
        CONFIG["similarity_threshold"] = config.similarity_threshold
        save_config()
        logger.info(f"Updated similarity threshold to {config.similarity_threshold}")
        return {"code": 200, "msg": "Config updated"}
    except Exception as e:
        logger.error(f"Update Config Error: {e}")
        return {"code": 500, "msg": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8070)
