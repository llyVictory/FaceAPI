import numpy as np
import pickle
import os

DB_FILE = "face_db.pkl"

class VectorDB:
    def __init__(self):
        self.features = [] # List of np.array
        self.user_ids = [] # List of strings
        
    def load_db(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.features = data.get('features', [])
                    self.user_ids = data.get('user_ids', [])
                print(f"Loaded {len(self.user_ids)} users from DB.")
            except Exception as e:
                print(f"Failed to load DB: {e}")
        else:
            print("No existing DB found. Starting fresh.")
            
    def save_db(self):
        with open(DB_FILE, 'wb') as f:
            pickle.dump({
                'features': self.features,
                'user_ids': self.user_ids
            }, f)
            
    def add(self, user_id, feature):
        self.user_ids.append(user_id)
        self.features.append(feature)
        
    def search(self, feature, top_k=1):
        if not self.features:
            return None, 0.0
            
        # Convert to matrix
        db_matrix = np.array(self.features) # (N, 512)
        target = np.array(feature)          # (512,)
        
        # Normalize
        norm_db = np.linalg.norm(db_matrix, axis=1, keepdims=True)
        norm_target = np.linalg.norm(target)
        
        # Avoid division by zero
        if norm_target == 0: 
            return None, 0.0
            
        sims = np.dot(db_matrix, target) / (norm_db.flatten() * norm_target)
        
        # Get max
        idx = np.argsort(sims)[-1]
        score = sims[idx]
        
        return self.user_ids[idx], score
