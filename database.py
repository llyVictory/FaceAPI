import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, LargeBinary, Text
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
