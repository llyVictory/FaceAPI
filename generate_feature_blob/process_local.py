import os
import cv2
import argparse
import shutil
import traceback
import database
from face_service import FaceService
from common import setup_logger

# Initialize Logger
logger = setup_logger("Local_Feature_Importer")

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
SUCCESS_DIR = os.path.join(BASE_DIR, "output", "success")
FAIL_DIR = os.path.join(BASE_DIR, "output", "fail")
DEBUG_DIR = os.path.join(BASE_DIR, "output", "debug")

def init_env():
    """确保所有文件夹存在"""
    for d in [INPUT_DIR, SUCCESS_DIR, FAIL_DIR, DEBUG_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def process_single_photo(user_id, image_path, move_after=False):
    """
    Process a local photo and save its feature to the database.
    """
    logger.info(f"正在分析照片: {os.path.basename(image_path)} (识别学号: {user_id})")
    
    if not os.path.exists(image_path):
        logger.error(f"错误: 文件不存在 -> {image_path}")
        return False

    face_service = FaceService()
    try:
        face_service.init_model()
        database.init_db()
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        return False

    file_name = os.path.basename(image_path)
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("无法解析图片（格式错误或路径非法）")
            
        feature, score = face_service.get_feature(img)
        logger.info(f"   [检测结果] 置信度得分: {score:.4f}")
        
        if feature is None:
            raise Exception("图片中未检测到有效人脸")
            
        database.save_target_feature(user_id=user_id, feature=feature, threshold=0.45)
        logger.info(f"✅ 成功: 学号 {user_id} 录入完成。")
        
        if move_after:
            # 生成带红框和置信度的可视化图片
            vis_img = face_service.draw_faces(img)
            target = os.path.join(SUCCESS_DIR, file_name)
            cv2.imwrite(target, vis_img)
            
            # 删除原始文件
            if os.path.exists(image_path):
                os.remove(image_path)
            logger.info(f"   [已归档] 可视化结果已保存至 output/success")
        return True

    except Exception as e:
        logger.error(f"❌ 失败: {str(e)}")
        if move_after:
            # 诊断逻辑：保存一份可视化检测图
            try:
                # 为了诊断，我们需要重新初始化一个极低阈值的 service
                diagnostic_service = FaceService()
                diagnostic_service.init_model(det_thresh=0.1) # 诊断时强制极低阈值
                debug_img = diagnostic_service.draw_faces(img) 
                debug_file_name = f"DEBUG_{user_id}.jpg"
                debug_path = os.path.join(DEBUG_DIR, debug_file_name)
                cv2.imwrite(debug_path, debug_img)
                logger.warning(f"   [诊断完成] 已生成调试图片查看检测细节: output/debug/{debug_file_name}")
            except Exception as diag_err:
                logger.debug(f"诊断失败: {str(diag_err)}")

            target = os.path.join(FAIL_DIR, file_name)
            shutil.move(image_path, target)
            logger.info(f"   [已归档] 原始文件已移动至 output/fail")
        return False

def interactive_mode():
    """交互式选择模式"""
    init_env()
    while True:
        # 获取待处理文件
        files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        
        print("\n" + "="*40)
        print("      人脸特征交互录入系统")
        print("="*40)
        print(f"当前 input 目录照片数量: {len(files)}")
        
        if not files:
            print("提示: 没有任何待处理照片。请将照片放在 input/ 文件夹下。")
            input("\n按回车键重新扫描，或按 Ctrl+C 退出...")
            continue
            
        for i, f in enumerate(files):
            print(f" [{i+1}] {f}")
        
        print("-" * 40)
        choice = input(f"请输入序号开始录入 (1-{len(files)}，或输入 'q' 退出): ").strip()
        
        if choice.lower() == 'q':
            break
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                selected_file = files[idx]
                user_id = os.path.splitext(selected_file)[0]
                full_path = os.path.join(INPUT_DIR, selected_file)
                
                # 开始处理
                process_single_photo(user_id, full_path, move_after=True)
                input("\n处理完成，按回车返回菜单...")
            else:
                print("❌ 序号超出范围，请重新选择。")
        except ValueError:
            print("❌ 输入非法，请输入数字。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="手工录入本地照片人脸特征到数据库")
    parser.add_argument("--user_id", help="对应系统的学号/用户ID (yhbh)")
    parser.add_argument("--path", help="本地照片文件的绝对或相对路径")
    
    args = parser.parse_args()
    
    if args.user_id and args.path:
        process_single_photo(args.user_id, args.path)
    else:
        # 进入傻瓜化交互模式
        try:
            interactive_mode()
        except KeyboardInterrupt:
            print("\n程序已退出。")
