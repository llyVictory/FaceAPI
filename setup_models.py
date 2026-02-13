import os
import shutil
import insightface
from insightface.app import FaceAnalysis

# 1. Initialize FaceAnalysis with buffalo_sc (sc = small/mobile version)
# This will AUTO-DOWNLOAD the models to ~/.insightface/models/buffalo_sc
print("正在自动下载/加载 buffalo_sc 模型...")
app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print("模型加载完成！")

# 2. Locate the model file
# Usually in ~/.insightface/models/buffalo_sc/w600k_mbf.onnx
user_home = os.path.expanduser('~')
source_model_path = os.path.join(user_home, '.insightface', 'models', 'buffalo_sc', 'w600k_mbf.onnx')

# 3. Define target path in H5
# Current script is in FaceApi root
target_dir = os.path.join(os.getcwd(), 'H5', 'public', 'models')
target_path = os.path.join(target_dir, 'w600k_mbf.onnx')

# 4. Copy
if os.path.exists(source_model_path):
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy2(source_model_path, target_path)
    print(f"成功复制模型到: {target_path}")
    print("您可以直接启动 H5 了！")
else:
    print(f"警告：未找到模型文件 {source_model_path}")
    print("请检查网络是否能够访问 GitHub/InsightFace 仓库。")
