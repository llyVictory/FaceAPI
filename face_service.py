import insightface
from insightface.app import FaceAnalysis
import numpy as np
import os

class FaceService:
    def __init__(self):
        self.app = None
        
    def init_model(self):
        # 'buffalo_l' is a good server-side model
        # If download fails, ensure internet access or manually place models in ~/.insightface/models/
        # providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
        # Use local models directory
        model_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
        self.app = FaceAnalysis(name='buffalo_sc', root=model_root, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        
    def get_feature(self, img_numpy):
        """
        Returns the 512-d embedding of the largest face
        """
        if self.app is None:
            raise Exception("Model not initialized")
            
        faces = self.app.get(img_numpy)
        if len(faces) == 0:
            return None
            
        # Sort by area (h*w)
        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        return faces[0].embedding
