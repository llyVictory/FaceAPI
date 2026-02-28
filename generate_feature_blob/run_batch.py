import os
import cv2
import numpy as np
import urllib.request
import traceback
import warnings
import time
import database
from face_service import FaceService
from common import setup_logger, load_config

# Suppress Deprecation/Future warnings from third-party libraries (especially insightface/skimage)
warnings.filterwarnings("ignore", category=FutureWarning)

# Initialize Logger
logger = setup_logger("Batch_Feature_Generator")

def run_batch_generation():
    """Standalone script to batch generate face features and save to DB"""
    logger.info("="*50)
    logger.info("开始执行人脸特征批量生成脚本")
    logger.info("="*50)
    
    # 获取当前时间后缀 (月日时分)
    time_suffix = time.strftime("%m%d%H%M")
    
    # Initialize services
    face_service = FaceService()
    try:
        logger.info("正在初始化人脸识别模型...")
        face_service.init_model()
        logger.info("模型初始化完成。")
        
        database.init_db()
        logger.info("数据库连接已就绪。")
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        return

    # Statistics
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0
    }

    try:
        logger.info("正在从源表获取待处理数据...")
        users = database.get_source_faces()
        stats["total"] = len(users)
        
        if stats["total"] == 0:
            logger.info("源表中没有待处理的数据。")
            return

        logger.info(f"拉取成功，共需处理 {stats['total']} 条记录。")
        
        for index, user in enumerate(users):
            yhbh = user.get("yhbh", "未知")
            url = user.get("face_url", "")
            
            logger.info(f"[{index+1}/{stats['total']}] 正在处理学号: {yhbh}")
            
            try:
                # 1. Download image
                image_bytes = None
                if not url:
                    raise Exception("URL为空")
                    
                logger.debug(f"正在重新下载图片 -> {url}")
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    resp = urllib.request.urlopen(req, timeout=10)
                    image_bytes = resp.read()
                except Exception as download_err:
                    raise Exception(f"下载失败: {str(download_err)}")
                
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise Exception("无法解析图片（格式错误或内容为空）")
                
                # 2. Extract feature
                feature, score, padding = face_service.get_feature(img)
                logger.info(f"   [检测结果] 置信度得分: {score:.4f} (补边比例: {padding:.2%})")
                
                if feature is None:
                    raise Exception("图片中尝试所有补边方案后均未检测到有效人脸")
                
                # 3. Save to database
                database.save_target_feature(user_id=yhbh, feature=feature, threshold=0.45)
                
                stats["success"] += 1
                logger.info(f"   [成功] 学号: {yhbh} 特征已保存")

                # 4. 可视化保存逻辑 (仅保存 15% 和 30% 补边的情况用于 debug)
                if padding > 0:
                    try:
                        base_name = "padding_15" if padding == 0.15 else "padding_30"
                        sub_dir = f"{base_name}_{time_suffix}"
                        success_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_batch", "success", sub_dir)
                        if not os.path.exists(success_dir):
                            os.makedirs(success_dir)
                        
                        # 调用 face_service 生成带红框和置信度的图
                        vis_img = face_service.draw_faces(img, padding_ratio=padding)
                        save_path = os.path.join(success_dir, f"{yhbh}.jpg")
                        cv2.imwrite(save_path, vis_img)
                        logger.info(f"   [已存证] 补边可视化结果已保存至: output_batch/success/{sub_dir}/{yhbh}.jpg")
                    except Exception as vis_err:
                        logger.warning(f"   [警告] 无法保存可视化图片: {str(vis_err)}")
                
            except Exception as e:
                stats["failed"] += 1
                error_msg = str(e)
                logger.error(f"   [失败] 学号: {yhbh} -> {error_msg}")
                
                # 保存失败的照片以便人工核查
                try:
                    fail_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_batch", "fail", f"fail_{time_suffix}")
                    if not os.path.exists(fail_dir):
                        os.makedirs(fail_dir)
                    
                    if image_bytes:
                        # 尝试从 URL 推断后缀名
                        ext = ".jpg"
                        try:
                            potential_ext = os.path.splitext(url.split('?')[0])[1].lower()
                            if potential_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                                ext = potential_ext
                        except:
                            pass
                        
                        fail_path = os.path.join(fail_dir, f"{yhbh}{ext}")
                        with open(fail_path, "wb") as f:
                            f.write(image_bytes)
                        logger.warning(f"   [已存证] 失败照片已保存至: output_batch/fail/fail_{time_suffix}/{yhbh}{ext}")
                    else:
                        logger.warning(f"   [跳过保存] 无法保存照片，因为下载已失败且未获取到内容")
                except Exception as save_err:
                    logger.error(f"   [警告] 无法保存失败照片: {str(save_err)}")

    except Exception as e:
        logger.error(f"批量处理过程中遇到严重错误: {traceback.format_exc()}")
    
    finally:
        logger.info("="*50)
        logger.info("批量任务执行完毕。")
        logger.info(f"统计概览 - 总数: {stats['total']}, 成功: {stats['success']}, 失败: {stats['failed']}")
        logger.info("="*50)

if __name__ == "__main__":
    run_batch_generation()
