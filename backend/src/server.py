from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import cv2
import logging
from tempfile import NamedTemporaryFile
from ulid import ULID
from enum import Enum
from datetime import datetime
from typing import Dict, Optional
import asyncio
import os

from face_processor import FaceProcessor
from line import router as line_router
from fastapi.middleware.cors import CORSMiddleware

# ロギングの設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    def __init__(self, job_id: str, file_path: str):
        self.job_id = job_id
        self.file_path = file_path
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.result: Optional[Dict] = None


# ジョブを保持する辞書
jobs: Dict[str, Job] = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# LINE Bot
app.include_router(line_router)


async def process_video_job(job: Job, job_id: str):
    try:
        job.status = JobStatus.PROCESSING

        # Open the saved video using OpenCV
        cap = cv2.VideoCapture(job.file_path)
        if not cap.isOpened():
            raise Exception("Could not open video file with OpenCV.")

        # Process video
        face_processor = FaceProcessor(job.file_path, job_id)
        result = face_processor.process_video()

        cap.release()

        # Update job status
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.result = result

    except Exception as e:
        logger.error(f"ジョブ処理中にエラーが発生: {str(e)}")
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()

    finally:
        # Cleanup temporary file
        try:
            if os.path.exists(job.file_path):
                os.remove(job.file_path)
        except Exception as e:
            logger.error(f"一時ファイルの削除中にエラーが発生: {str(e)}")


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    logger.info(
        f"ファイルアップロード開始: {file.filename}, content_type: {file.content_type}"
    )

    if not file.content_type.startswith("video/"):
        logger.error(f"不正なファイル形式: {file.content_type}")
        raise HTTPException(
            status_code=400, detail="Invalid file type. Expected video."
        )

    try:
        job_id = str(ULID())

        # Save the uploaded file to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            logger.info(f"一時ファイルに保存: {temp_file_path}")

        # Create new job
        job = Job(job_id, temp_file_path)
        jobs[job_id] = job

        # Start processing in background
        asyncio.create_task(process_video_job(job, job_id))

        return JSONResponse(
            content={
                "job_id": job_id,
                "status": job.status.value,
                "message": "Video upload successful. Processing started.",
            }
        )
    except Exception as e:
        logger.error(f"エラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    response = {
        "job_id": job.job_id,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }

    if job.status == JobStatus.FAILED:
        response["error"] = job.error_message
    elif job.status == JobStatus.COMPLETED:
        response["result"] = job.result

    return JSONResponse(content=response)


if __name__ == "__main__":
    import uvicorn

    logger.info("サーバーを起動します")
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True)
