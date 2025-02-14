from io import BytesIO
import os
import threading
import zipfile

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()


class MinioClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(
        cls, endpoint: str, access_key: str, secret_key: str, secure: bool = True
    ) -> "MinioClient":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_client(endpoint, access_key, secret_key, secure)
        return cls._instance

    def _init_client(
        self, endpoint: str, access_key: str, secret_key: str, secure: bool
    ) -> None:
        self.client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )

    def upload_image(self, bucket_name: str, file_path: str) -> Exception | None:
        """
        指定されたバケットに画像をアップロードする

        Args:
            bucket_name (str): アップロード先のバケット名
            file_path (str): アップロードする画像ファイルのパス

        Returns:
            Exception | None: None | エラー
        """
        try:
            # バケットが存在しない場合は作成
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)

            file_name = os.path.basename(file_path)
            self.client.fput_object(bucket_name, file_name, file_path)
            return None
        except S3Error as e:
            return e

    def get_presigned_urls(
        self, bucket_name: str
    ) -> tuple[list[str], Exception | None]:
        """
        指定されたバケット内の全オブジェクトの署名付きURLを取得する

        Args:
            bucket_name (str): バケット名

        Returns:
            tuple[list[str], Exception | None]: URLリスト | エラー
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                return [], None

            urls = [
                self.client.presigned_get_object(bucket_name, obj.object_name)
                for obj in self.client.list_objects(bucket_name)
            ]
            return urls, None
        except S3Error as e:
            return [], e

    def download_all_images(self, bucket_name: str) -> tuple[BytesIO, Exception | None]:
        """バケット内のすべての画像を ZIP に圧縮して返す"""
        try:
            if not self.client.bucket_exists(bucket_name):
                return BytesIO(), None

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for obj in self.client.list_objects(bucket_name):
                    image_data = self.client.get_object(bucket_name, obj.object_name)
                    zip_file.writestr(obj.object_name, image_data.read())

            zip_buffer.seek(0)
            return zip_buffer, None
        except S3Error as e:
            return BytesIO(), e


minio_client = MinioClient(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/images")
def get_urls(bucket: str = Query(..., description="Bucket name")):
    urls, err = minio_client.get_presigned_urls(bucket)
    if err is not None:
        raise HTTPException(status_code=500, detail=str(err))
    return {"images": urls}


@app.get("/download")
def download_all(bucket: str = Query(..., description="Bucket name")):
    try:
        if not minio_client.client.bucket_exists(bucket):
            raise HTTPException(status_code=404, detail="Bucket not found")

        objects = list(minio_client.client.list_objects(bucket))
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:

            def fetch_object(obj):
                data = minio_client.client.get_object(bucket, obj.object_name).read()
                return obj.object_name, data

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(fetch_object, obj) for obj in objects]
                for future in futures:
                    file_name, content = future.result()
                    zip_file.writestr(file_name, content)

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=images.zip"},
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("s3:app", host="0.0.0.0", port=5000, reload=True)
