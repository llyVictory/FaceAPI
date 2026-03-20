import os
import uuid
import json
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, LargeBinary, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import numpy as np

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv('DB_HOST', '172.26.70.234')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'face_attendance')

TABLE_SOURCE = os.getenv('TABLE_SOURCE', 'v_user_face_kq')
TABLE_TARGET = os.getenv('TABEL_TARGET', 'kq_face_feature') # Notice typo in env variable requested by user

# Create database URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Create engine with connection pool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Define User model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    feature_blob = Column(LargeBinary, nullable=False)
    photo_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)

# Define Log model
class Log(Base):
    __tablename__ = 'logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(String(20), nullable=False, index=True)
    user_name = Column(String(100))
    score = Column(Float)
    threshold = Column(Float)
    status = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    timestamp = Column(DateTime, default=datetime.now, index=True)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

def add_user(name, feature, photo_path=None):
    """
    Add a new user
    feature: numpy array (512,)
    """
    session = SessionLocal()
    try:
        # Convert numpy array to bytes
        feature_blob = feature.tobytes()
        
        user = User(
            name=name,
            feature_blob=feature_blob,
            photo_path=photo_path
        )
        session.add(user)
        session.commit()
        user_id = user.id
        return user_id
    finally:
        session.close()

def delete_user(user_id):
    """Delete a user by ID"""
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            session.delete(user)
            session.commit()
            return True
        return False
    finally:
        session.close()

def get_users():
    """Get all users"""
    session = SessionLocal()
    try:
        users = session.query(User).all()
        return [{"id": u.id, "name": u.name} for u in users]
    finally:
        session.close()

def get_user_feature(user_id):
    """Get user feature vector by ID"""
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            # Convert bytes back to numpy array
            feature = np.frombuffer(user.feature_blob, dtype=np.float32)
            return feature
        return None
    finally:
        session.close()

def get_user_name(user_id):
    """Get user name by ID"""
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        return user.name if user else None
    finally:
        session.close()

def add_log(uuid, user_id, user_name, score, threshold, status, latitude=None, longitude=None):
    """Add attendance log"""
    session = SessionLocal()
    try:
        log = Log(
            uuid=uuid,
            user_id=str(user_id),
            user_name=user_name,
            score=score,
            threshold=threshold,
            status=status,
            latitude=latitude,
            longitude=longitude
        )
        session.add(log)
        session.commit()
    finally:
        session.close()

def get_logs(limit=100, offset=0):
    """Get attendance logs with pagination"""
    session = SessionLocal()
    try:
        logs = session.query(Log).order_by(Log.timestamp.desc()).limit(limit).offset(offset).all()
        return [{
            "uuid": log.uuid,
            "user_id": log.user_id,
            "user_name": log.user_name,
            "score": log.score,
            "threshold": log.threshold,
            "status": log.status,
            "latitude": log.latitude,
            "longitude": log.longitude,
            "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else None
        } for log in logs]
    finally:
        session.close()

from sqlalchemy import text

def get_source_faces():
    """
    Retrieve users and their face URLs from the source table.
    Optimization: Only select users who do NOT exist in the target table (incremental update).
    """
    session = SessionLocal()
    try:
        # Use a LEFT JOIN to find users missing in the target feature table
        sql = f"""
            SELECT s.yhbh, s.face_url 
            FROM {TABLE_SOURCE} s
            LEFT JOIN {TABLE_TARGET} t ON s.yhbh = t.user_id
            WHERE s.face_url IS NOT NULL 
              AND s.face_url != ''
              AND t.user_id IS NULL
        """
        query = text(sql)
        result = session.execute(query).fetchall()
        return [{"yhbh": row[0], "face_url": row[1]} for row in result]
    finally:
        session.close()

def save_target_feature(user_id, feature, threshold=0.45):
    """
    Save or update the feature vector to the target table.
    feature: numpy array (512,)
    """
    session = SessionLocal()
    try:
        feature_blob = feature.tobytes()
        
        # We use an upsert (ON DUPLICATE KEY UPDATE) to handle both insertion and update
        query = text(f"""
            INSERT INTO {TABLE_TARGET} (user_id, threshold, feature_blob) 
            VALUES (:user_id, :threshold, :feature_blob)
            ON DUPLICATE KEY UPDATE 
            threshold = VALUES(threshold), feature_blob = VALUES(feature_blob)
        """)
        session.execute(query, {
            "user_id": user_id, 
            "threshold": threshold, 
            "feature_blob": feature_blob
        })
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_source_face_url(yhbh: str, face_url: str):
    """
    Update face_url in the source table (local database).
    """
    session = SessionLocal()
    try:
        # Executing raw SQL update to cover the local record's face_url
        query = text(f"UPDATE {TABLE_SOURCE} SET face_url = :face_url WHERE yhbh = :yhbh")
        session.execute(query, {"face_url": face_url, "yhbh": yhbh})
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def upsert_source_faces_batch(users: list) -> int:
    """
    批量将 PostgreSQL 拉取的人脸数据追加写入本地 v_user_face_kq。
    采用 INSERT ... ON DUPLICATE KEY UPDATE 追加模式，已有记录只更新 face_url。
    返回实际写入行数。
    users: [{"yhbh": "...", "face_url": "..."}]
    """
    if not users:
        return 0
    session = SessionLocal()
    try:
        for user in users:
            session.execute(
                text(f"""
                    INSERT INTO {TABLE_SOURCE} (yhbh, face_url)
                    VALUES (:yhbh, :face_url)
                    ON DUPLICATE KEY UPDATE face_url = VALUES(face_url)
                """),
                {"yhbh": user["yhbh"], "face_url": user["face_url"]}
            )
        session.commit()
        return len(users)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ----------------------------------------
# 批量任务表 BatchTask
# ----------------------------------------

class BatchTask(Base):
    __tablename__ = 'kq_batch_task'

    id = Column(String(64), primary_key=True)
    task_uuid = Column(String(64), nullable=False, unique=True, index=True)
    task_type = Column(String(32), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    failed_details = Column(Text, default='[]')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


TASK_TYPE_FACE_FEATURE_BATCH = 'FACE_FEATURE_BATCH'


def create_batch_task(task_type: str = TASK_TYPE_FACE_FEATURE_BATCH) -> str:
    """创建批量任务记录，返回 task_uuid"""
    task_uuid = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        task = BatchTask(
            id=task_id,
            task_uuid=task_uuid,
            task_type=task_type,
            status='pending',
            total_count=0,
            success_count=0,
            failed_count=0,
            failed_details='[]',
        )
        session.add(task)
        session.commit()
        return task_uuid
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_task_started(task_uuid: str, total_count: int):
    """任务开始处理时，更新总数和状态为 running"""
    session = SessionLocal()
    try:
        session.execute(
            text("UPDATE kq_batch_task SET status='running', total_count=:total WHERE task_uuid=:uuid"),
            {"total": total_count, "uuid": task_uuid}
        )
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_task_progress(task_uuid: str, success_delta: int = 0, failed_item: Optional[dict] = None):
    """
    每处理一条记录后实时更新进度。
    - success_delta: 成功时传 1
    - failed_item: 失败时传 {"yhbh": ..., "face_url": ..., "error": ...}
    """
    session = SessionLocal()
    try:
        row = session.execute(
            text("SELECT success_count, failed_count, failed_details FROM kq_batch_task WHERE task_uuid=:uuid"),
            {"uuid": task_uuid}
        ).fetchone()
        if not row:
            return

        new_success = row[0] + success_delta
        new_failed = row[1]
        details = json.loads(row[2] or '[]')

        if failed_item:
            new_failed += 1
            details.append(failed_item)

        session.execute(
            text("""
                UPDATE kq_batch_task
                SET success_count=:s, failed_count=:f, failed_details=:d
                WHERE task_uuid=:uuid
            """),
            {
                "s": new_success,
                "f": new_failed,
                "d": json.dumps(details, ensure_ascii=False),
                "uuid": task_uuid
            }
        )
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_task_finished(task_uuid: str):
    """所有记录处理完成后，更新任务状态为 completed"""
    session = SessionLocal()
    try:
        session.execute(
            text("UPDATE kq_batch_task SET status='completed' WHERE task_uuid=:uuid"),
            {"uuid": task_uuid}
        )
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_task_status(task_uuid: str) -> Optional[dict]:
    """查询单个任务状态和详情"""
    session = SessionLocal()
    try:
        row = session.execute(
            text("""
                SELECT task_uuid, task_type, status, total_count, success_count,
                       failed_count, failed_details, created_at, updated_at
                FROM kq_batch_task WHERE task_uuid=:uuid
            """),
            {"uuid": task_uuid}
        ).fetchone()
        if not row:
            return None
        return {
            "task_uuid": row[0],
            "task_type": row[1],
            "status": row[2],
            "total_count": row[3],
            "success_count": row[4],
            "failed_count": row[5],
            "failed_details": json.loads(row[6] or '[]'),
            "created_at": row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else None,
            "updated_at": row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None,
        }
    finally:
        session.close()


def list_batch_tasks(task_type: Optional[str] = None, page: int = 1, limit: int = 10) -> list:
    """分页查询历史任务列表（不返回 failed_details 避免数据过大）"""
    session = SessionLocal()
    try:
        where = "WHERE task_type=:task_type" if task_type else ""
        params: dict = {"offset": (page - 1) * limit, "limit": limit}
        if task_type:
            params["task_type"] = task_type
        rows = session.execute(
            text(f"""
                SELECT task_uuid, task_type, status, total_count, success_count,
                       failed_count, created_at, updated_at
                FROM kq_batch_task
                {where}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params
        ).fetchall()
        return [{
            "task_uuid": r[0],
            "task_type": r[1],
            "status": r[2],
            "total_count": r[3],
            "success_count": r[4],
            "failed_count": r[5],
            "created_at": r[6].strftime('%Y-%m-%d %H:%M:%S') if r[6] else None,
            "updated_at": r[7].strftime('%Y-%m-%d %H:%M:%S') if r[7] else None,
        } for r in rows]
    finally:
        session.close()


def count_batch_tasks(task_type: Optional[str] = None) -> int:
    """查询历史任务总数，用于分页"""
    session = SessionLocal()
    try:
        where = "WHERE task_type=:task_type" if task_type else ""
        params: dict = {}
        if task_type:
            params["task_type"] = task_type
        row = session.execute(
            text(f"SELECT COUNT(*) FROM kq_batch_task {where}"),
            params
        ).fetchone()
        return row[0] if row else 0
    finally:
        session.close()
