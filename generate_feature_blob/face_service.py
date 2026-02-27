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

    def _extract(self, img_numpy, padding_ratio=0.0):
        """内部特征提取逻辑，支持自定义补边比例"""
        if self.app is None:
            raise Exception("Model not initialized")
            
        import cv2
        if padding_ratio > 0:
            h, w = img_numpy.shape[:2]
            padding = int(max(h, w) * padding_ratio)
            img_input = cv2.copyMakeBorder(img_numpy, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=[0, 0, 0])
        else:
            img_input = img_numpy

        faces = self.app.get(img_input)
        if len(faces) == 0:
            return None, 0.0
            
        # 按面积排序取最大脸
        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        return faces[0].embedding, faces[0].det_score

    def get_feature(self, img_numpy):
        """
        降级提取逻辑:
        1. 默认不启用补边，直接拿原照片
        2. 若提取失败，尝试 15% DET_PADDING
        3. 若仍失败，尝试 30% DET_PADDING
        Returns (embedding, score, used_padding_ratio)
        """
        # 尝试不同级别的补边
        fallbacks = [0.0, 0.15, 0.30]
        
        for p in fallbacks:
            feature, score = self._extract(img_numpy, padding_ratio=p)
            if feature is not None:
                return feature, score, p
                
        return None, 0.0, None

    def draw_faces(self, img_numpy, padding_ratio=0.0):
        """
        用于诊断：在图片上画出当前模型能看到的所有人脸
        """
        import cv2
        if self.app is None:
            return img_numpy
            
        if padding_ratio > 0:
            h, w = img_numpy.shape[:2]
            padding = int(max(h, w) * padding_ratio)
            img_input = cv2.copyMakeBorder(img_numpy, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=[0, 0, 0])
        else:
            img_input = img_numpy

        faces = self.app.get(img_input)
        print(f"      [诊断调试] 检测到 {len(faces)} 个疑似目标 (补边比例: {padding_ratio:.2%})")
        out_img = img_input.copy()
        
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
