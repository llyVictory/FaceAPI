import csv
import os
from datetime import datetime

LOG_FILE = "attendance_log.csv"

def log_attendance(user_id, status, address="Unknown"):
    """
    Appends an attendance record to the CSV file.
    Format: Timestamp, UserID, Status, Address
    """
    file_exists = os.path.exists(LOG_FILE)
    
    try:
        with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header if new file
            if not file_exists:
                writer.writerow(["Timestamp", "UserID", "Status", "Address"])
            
            # Write record
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([timestamp, user_id, status, address])
    except Exception as e:
        print(f"Error logging attendance: {e}")
