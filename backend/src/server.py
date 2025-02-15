from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import cv2
import logging
from tempfile import NamedTemporaryFile

from face_processor import FaceProcessor
from line import router as line_router
from fastapi.middleware.cors import CORSMiddleware

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
        # Save the uploaded file to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            logger.info(f"一時ファイルに保存: {temp_file_path}")

        # Open the saved video using OpenCV
        cap = cv2.VideoCapture(temp_file_path)
        if not cap.isOpened():
            logger.error("OpenCVでビデオファイルを開けませんでした")
            raise HTTPException(
                status_code=500, detail="Could not open video file with OpenCV."
            )

        # (Example) Read first frame to process
        ret, frame = cap.read()
        cap.release()
        if not ret:
            logger.error("ビデオからフレームを読み取れませんでした")
            raise HTTPException(
                status_code=500, detail="Failed to read frame from video."
            )

        logger.info("ビデオの処理を開始")
        face_processor = FaceProcessor(temp_file_path)
        face_processor.process_video()
        logger.info("ビデオの処理が完了")

        return JSONResponse(content={"message": "Video processed successfully"})
    except Exception as e:
        logger.error(f"エラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    logger.info("サーバーを起動します")
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True)
