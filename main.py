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
from face_service import FaceService
import database

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

# --- Reporting API ---

@app.post("/api/report")
async def report_log(
    user_id: str = Body(...),
    score: float = Body(...),
    status: str = Body(...),
    address: str = Body(None)
):
    try:
        # Log to DB
        # user_id might be "1" (string) from frontend
        database.add_log(user_id, score, status)
        
        logger.info(f"Report: User={user_id}, Score={score:.4f}, Status={status}, Addr={address}")
        return {"code": 200, "msg": "Log saved"}
    except Exception as e:
        logger.error(f"Report Error: {e}")
        return {"code": 500, "msg": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8070)
