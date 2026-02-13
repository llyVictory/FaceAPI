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
    
    # Logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        score REAL,
        status TEXT,
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

def add_log(user_id, score, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO logs (user_id, score, status) VALUES (?, ?, ?)', 
                   (user_id, score, status))
    conn.commit()
    conn.close()
