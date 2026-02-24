import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import os
import database
from common import setup_logger, load_config

# Setup logger for H5 Service
logger = setup_logger("H5_Service")

app = FastAPI(title="Face Attendance H5 API")

# Serve uploaded photos
os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting H5 Backend...")
    database.init_db()
    logger.info("Database initialized.")

@app.get("/")
def read_root():
    return {"message": "Face Attendance H5 Backend is Running"}

# --- H5 Endpoints ---
@app.get("/api/config")
def get_config():
    """Return current configuration to H5 UI"""
    current_config = load_config()
    return {"code": 200, "data": current_config}

@app.get("/api/users")
def get_users():
    """List users for selection in H5 UI"""
    try:
        users = database.get_users()
        return {"code": 200, "data": users}
    except Exception as e:
        logger.error(f"Get Users Error: {e}")
        return {"code": 500, "msg": str(e)}

@app.get("/api/face/feature/{user_id}")
async def get_feature(user_id: int):
    """Provide feature vector for local comparison in H5"""
    try:
        feature = database.get_user_feature(user_id)
        if feature is not None:
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

class ReportModel(BaseModel):
    uuid: str
    user_id: int
    score: float
    threshold: float
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@app.post("/api/report")
async def report_log(report: ReportModel):
    """Save attendance result from H5"""
    try:
        user_name = database.get_user_name(str(report.user_id))
        database.add_log(
            uuid=report.uuid,
            user_id=str(report.user_id),
            user_name=user_name,
            score=report.score,
            threshold=report.threshold,
            status=report.status,
            latitude=report.latitude,
            longitude=report.longitude
        )
        logger.info(f"Report: UUID={report.uuid}, User={user_name}({report.user_id}), Score={report.score:.4f}, Status={report.status}")
        return {"code": 200, "msg": "Log saved"}
    except Exception as e:
        logger.error(f"Report Error: {e}")
        return {"code": 500, "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8070)
