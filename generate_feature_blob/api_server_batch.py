import os
import psycopg2
import urllib.request
import cv2
import numpy as np
import warnings
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import database
from face_service import FaceService
from common import setup_logger

# 抑制第三方库的 FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# 初始化 Logger
logger = setup_logger("Batch_API")

load_dotenv()

app = FastAPI(
    title="Face Feature Batch API",
    description="批量人脸特征提取任务接口，供 Java 业务端调用"
)

# 初始化人脸识别模型（全局共享）
face_service = FaceService()
try:
    logger.info("正在初始化 FaceService...")
    face_service.init_model()
    logger.info("FaceService 初始化完成。")
except Exception as e:
    logger.error(f"FaceService 初始化失败: {str(e)}")


# ----------------------------------------
# PostgreSQL 连接
# ----------------------------------------

def get_pg_connection():
    """获取 PostgreSQL 连接"""
    schema = os.getenv("PG_SCHEMA", "views")
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "172.18.177.40"),
        port=os.getenv("PG_PORT", "15400"),
        user=os.getenv("PG_USER", "wgkq"),
        password=os.getenv("PG_PASSWORD", "Sdpei#@2026$#"),
        dbname=os.getenv("PG_DB", "cloudtop"),
        options=f"-c search_path={schema}"
    )


# ----------------------------------------
# 请求体模型
# ----------------------------------------

class RunBatchByGradeRequest(BaseModel):
    DQSZJ: str  # 所属年级，必传，如 "2022"


# ----------------------------------------
# 后台任务函数
# ----------------------------------------

def bg_run_face_feature_batch_by_grade(task_uuid: str, dqszj: str):
    """
    按年级批量任务：
    1. 从 PostgreSQL 按 DQSZJ（yhbh 前四位）拉取指定年级数据
    2. 追加 UPSERT 到本地 v_user_face_kq（原有数据不动）
    3. 对这批数据提取人脸特征，写入 kq_face_feature
    """
    logger.info(f"[{task_uuid}] 年级批量任务启动，DQSZJ={dqszj}")
    try:
        # 第一步：从 PostgreSQL 拉取指定年级数据
        logger.info(f"[{task_uuid}] 正在连接 PostgreSQL 查询年级 {dqszj} 的数据...")
        try:
            conn = get_pg_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT yhbh, face_url
                FROM v_user_face_kq
                WHERE LEFT(yhbh, 4) = %s
                  AND face_url IS NOT NULL
                  AND face_url != ''
                """,
                (dqszj,)
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"[{task_uuid}] 连接 PostgreSQL 失败: {str(e)}")
            raise

        pg_users = [{"yhbh": row[0], "face_url": row[1]} for row in rows]
        total = len(pg_users)
        logger.info(f"[{task_uuid}] PostgreSQL 共查询到 {total} 条年级 {dqszj} 的记录")

        if total == 0:
            database.update_task_started(task_uuid, 0)
            database.update_task_finished(task_uuid)
            logger.warning(f"[{task_uuid}] 无待处理数据，任务结束")
            return

        # 第二步：追加 UPSERT 到本地 v_user_face_kq（原有其他数据不动）
        logger.info(f"[{task_uuid}] 正在写入本地 v_user_face_kq...")
        synced = database.upsert_source_faces_batch(pg_users)
        logger.info(f"[{task_uuid}] 本地 v_user_face_kq 已追加/更新 {synced} 条数据")

        # 第三步：对这批数据提取人脸特征，写入 kq_face_feature
        database.update_task_started(task_uuid, total)

        for index, user in enumerate(pg_users):
            yhbh = user.get("yhbh", "")
            url = user.get("face_url", "")
            logger.info(f"[{task_uuid}] [{index+1}/{total}] 处理学号: {yhbh}")
            try:
                if not url:
                    raise Exception("face_url 为空")

                # 下载图片
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=10)
                image_bytes = resp.read()

                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    raise Exception("无法解析图片（格式错误或内容为空）")

                # 提取人脸特征向量
                feature, score, padding = face_service.get_feature(img)
                if feature is None:
                    raise Exception("尝试所有补边方案后均未检测到有效人脸")

                database.save_target_feature(user_id=yhbh, feature=feature, threshold=0.45)
                logger.info(f"   [成功] 学号: {yhbh}, 置信度: {score:.4f}")
                database.update_task_progress(task_uuid, success_delta=1)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"   [失败] 学号: {yhbh} -> {error_msg}")
                database.update_task_progress(
                    task_uuid,
                    failed_item={"yhbh": yhbh, "face_url": url, "error": error_msg}
                )

        database.update_task_finished(task_uuid)
        logger.info(f"[{task_uuid}] 年级批量任务全部完成，DQSZJ={dqszj}")

    except Exception as e:
        logger.error(f"[{task_uuid}] 任务异常终止: {str(e)}")


# ----------------------------------------
# 接口端点
# ----------------------------------------

@app.post("/api/face_feature/run_batch_by_grade")
def run_batch_by_grade(req: RunBatchByGradeRequest, background_tasks: BackgroundTasks):
    """
    按年级批量触发人脸特征提取（必传 DQSZJ）：
    1. 从 PostgreSQL 拉取指定年级数据追加到本地
    2. 提取人脸特征写入 kq_face_feature
    立即返回 task_uuid，后台异步执行
    """
    dqszj = req.DQSZJ.strip()
    if not dqszj or len(dqszj) != 4 or not dqszj.isdigit():
        raise HTTPException(status_code=400, detail="DQSZJ 参数格式错误，应为 4 位年份数字，如 '2022'")

    task_uuid = database.create_batch_task(task_type=f"FACE_FEATURE_BATCH_GRADE")
    background_tasks.add_task(bg_run_face_feature_batch_by_grade, task_uuid, dqszj)
    logger.info(f"年级批量任务已创建，DQSZJ={dqszj}，task_uuid={task_uuid}")
    return {
        "code": 200,
        "message": f"年级 {dqszj} 的批量任务已启动",
        "data": {"task_uuid": task_uuid, "DQSZJ": dqszj}
    }


@app.get("/api/face_feature/batch_status/{task_uuid}")
def batch_status(task_uuid: str):
    """查询单个批量任务实时进度"""
    result = database.get_task_status(task_uuid)
    if not result:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_uuid}")
    return {"code": 200, "data": result}


class BatchTasksRequest(BaseModel):
    task_type: Optional[str] = None
    page: int = 1
    limit: int = 10


@app.post("/api/face_feature/batch_tasks")
def batch_tasks(req: BatchTasksRequest):
    """查看历史批量任务列表（支持按类型过滤、分页）"""
    total = database.count_batch_tasks(task_type=req.task_type)
    tasks = database.list_batch_tasks(task_type=req.task_type, page=req.page, limit=req.limit)
    return {"code": 200, "total": total, "data": tasks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server_batch:app", host="0.0.0.0", port=8072, reload=True)
