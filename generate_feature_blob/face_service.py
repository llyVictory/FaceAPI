import insightface
from insightface.app import FaceAnalysis
import numpy as np
import os
import warnings

# Suppress warnings from insightface's usage of deprecated skimage methods
warnings.filterwarnings("ignore", category=FutureWarning)

class FaceService:
    def __init__(self):
        self.app = None
        self.det_padding = 0.15
        
    def init_model(self, det_thresh=None, det_size=None, det_padding=None):
        # 从环境变量读取配置
        if det_thresh is None:
            det_thresh = float(os.getenv('DET_THRESH', '0.2'))
        if det_size is None:
            det_size = int(os.getenv('DET_SIZE', '640'))
        if det_padding is None:
            self.det_padding = float(os.getenv('DET_PADDING', '0.15'))
        else:
            self.det_padding = det_padding
            
        model_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
        self.app = FaceAnalysis(name='buffalo_sc', root=model_root, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(det_size, det_size), det_thresh=det_thresh)

    def get_feature(self, img_numpy):
        """
        Returns (embedding, score) of the largest face
        """
        if self.app is None:
            raise Exception("Model not initialized")
            
        import cv2
        # 自动补边 (Auto Padding): 为防止人脸太靠近边缘导致识别率下降，根据配置增加黑边
        h, w = img_numpy.shape[:2]
        padding = int(max(h, w) * self.det_padding)
        top = bottom = left = right = padding
        img_padded = cv2.copyMakeBorder(img_numpy, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        faces = self.app.get(img_padded)
        if len(faces) == 0:
            return None, 0.0
            
        # Sort by area (h*w)
        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        return faces[0].embedding, faces[0].det_score

    def draw_faces(self, img_numpy):
        """
        用于诊断：在图片上画出当前模型能看到的所有人脸
        """
        import cv2
        if self.app is None:
            return img_numpy
            
        import cv2
        # 同步增加自动补边的诊断显示
        h, w = img_numpy.shape[:2]
        padding = int(max(h, w) * self.det_padding)
        top = bottom = left = right = padding
        img_padded = cv2.copyMakeBorder(img_numpy, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        faces = self.app.get(img_padded)
        print(f"      [诊断调试] 模型检测到 {len(faces)} 个疑似人脸目标 (边缘增强系数: {self.det_padding})")
        out_img = img_padded.copy()
        
        for i, face in enumerate(faces):
            box = face.bbox.astype(int)
            color = (0, 0, 255) # Red
            cv2.rectangle(out_img, (box[0], box[1]), (box[2], box[3]), color, 2)
            
            # 写上置信度
            score = face.det_score
            text = f"{score:.2f}"
            print(f"      [诊断调试] 目标 {i+1}: 置信度={text}, 坐标={box}")
            cv2.putText(out_img, text, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        return out_img
