import os
import cv2
import argparse
import traceback
import database
from face_service import FaceService
from common import setup_logger

# Initialize Logger
logger = setup_logger("Local_Feature_Importer")

def process_single_photo(user_id, image_path):
    """
    Process a local photo and save its feature to the database.
    """
    logger.info(f"开始手工处理本地照片: {image_path} (学号: {user_id})")
    
    # 1. Check if file exists
    if not os.path.exists(image_path):
        logger.error(f"错误: 文件不存在 -> {image_path}")
        return False

    # 2. Initialize services
    face_service = FaceService()
    try:
        logger.info("系统初始化...")
        face_service.init_model()
        database.init_db()
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        return False

    try:
        # 3. Read image
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("无法解析本地图片（格式错误或路径非法）")
            
        # 4. Extract feature
        logger.info("正在提取人脸特征...")
        feature = face_service.get_feature(img)
        if feature is None:
            raise Exception("图片中未检测到有效人脸")
            
        # 5. Save to database
        logger.info(f"正在存入数据库表 (user_id={user_id})...")
        database.save_target_feature(user_id=user_id, feature=feature, threshold=0.45)
        
        logger.info(f"🎉 成功: 学号 {user_id} 的特征已从本地照片录入完成。")
        return True

    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="手工录入本地照片人脸特征到数据库")
    parser.add_argument("--user_id", required=True, help="对应系统的学号/用户ID (yhbh)")
    parser.add_argument("--path", required=True, help="本地照片文件的绝对或相对路径")
    
    args = parser.parse_args()
    
    process_single_photo(args.user_id, args.path)
