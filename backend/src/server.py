import logging
import os
from tempfile import NamedTemporaryFile

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ulid import ULID

from face_processor import FaceProcessor
from line import router as line_router

# ロギングの設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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


def process_video_task(video_path: str, process_id: str):
    """動画の処理を非同期で実行する関数"""
    try:
        face_processor = FaceProcessor(video_path, id=process_id)
        face_processor.process_video()
    except Exception as e:
        logger.error(f"動画処理中にエラーが発生: {str(e)}")
    finally:
        # 一時ファイルを削除
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"一時ファイル削除: {video_path}")
        except Exception as e:
            logger.error(f"一時ファイルの削除中にエラーが発生: {str(e)}")


@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    logger.info(
        f"ファイルアップロード開始: {file.filename}, content_type: {file.content_type}"
    )

    if not file.content_type.startswith("video/"):
        logger.error(f"不正なファイル形式: {file.content_type}")
        raise HTTPException(
            status_code=400, detail="Invalid file type. Expected video."
        )

    process_id = (str(ULID())).lower()

    # アップロードされた動画を一時ファイルに保存
    with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
        logger.info(f"一時ファイルに保存: {temp_file_path}")

    # 動画処理をバックグラウンドで実行
    background_tasks.add_task(process_video_task, temp_file_path, process_id)

    # DEBUG: バックグラウンドじゃない処理
    # face_processor = FaceProcessor(temp_file_path, id=process_id)
    # face_processor.process_video()

    # クライアントには即座にレスポンスを返す
    return JSONResponse(
        status_code=200,
        content={"process_id": process_id, "message": "Video processing started"},
    )


if __name__ == "__main__":
    logger.info("サーバーを起動します")
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True)
