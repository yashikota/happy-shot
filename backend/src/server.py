from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import cv2
from tempfile import NamedTemporaryFile

from face_processor import FaceProcessor

app = FastAPI()

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    print(f"{file.content_type=}")
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Expected video.")

    try:
        # Save the uploaded file to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Open the saved video using OpenCV
        cap = cv2.VideoCapture(temp_file_path)
        if not cap.isOpened():
            raise HTTPException(status_code=500, detail="Could not open video file with OpenCV.")

        # (Example) Read first frame to process
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise HTTPException(status_code=500, detail="Failed to read frame from video.")

        face_processor = FaceProcessor(temp_file_path)
        face_processor.process_video()

        return JSONResponse(content={"message": "Video processed successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5001, reload=True)
