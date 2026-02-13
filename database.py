import sqlite3
import json
import numpy as np
import os
from datetime import datetime

DB_FILE = "face_attendance.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users table
    # Storing feature as bytes (blob)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        feature_blob BLOB NOT NULL,
        photo_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Logs table with enhanced fields
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT NOT NULL UNIQUE,
        user_id TEXT NOT NULL,
        user_name TEXT,
        score REAL,
        threshold REAL,
        status TEXT,
        latitude REAL,
        longitude REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def add_user(name, feature, photo_path=None):
    """
    feature: numpy array (512,)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Convert numpy array to bytes
    feature_blob = feature.tobytes()
    
    cursor.execute('INSERT INTO users (name, feature_blob, photo_path) VALUES (?, ?, ?)', 
                   (name, feature_blob, photo_path))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def delete_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    rows = cursor.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def get_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM users')
    rows = cursor.fetchall()
    conn.close()
    
    return [{"id": r[0], "name": r[1]} for r in rows]

def get_user_feature(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT feature_blob FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        # Convert bytes back to numpy array
        # Assuming float32 (standard for insightface)
        feature = np.frombuffer(row[0], dtype=np.float32)
        return feature
    return None

def get_user_name(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def add_log(uuid, user_id, user_name, score, threshold, status, latitude=None, longitude=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (uuid, user_id, user_name, score, threshold, status, latitude, longitude) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (uuid, user_id, user_name, score, threshold, status, latitude, longitude))
    conn.commit()
    conn.close()

def get_logs(limit=100, offset=0):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT uuid, user_id, user_name, score, threshold, status, latitude, longitude, timestamp 
        FROM logs 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "uuid": r[0],
        "user_id": r[1],
        "user_name": r[2],
        "score": r[3],
        "threshold": r[4],
        "status": r[5],
        "latitude": r[6],
        "longitude": r[7],
        "timestamp": r[8]
    } for r in rows]
