import os
import threading

from minio import Minio
from minio.error import S3Error


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


if __name__ == "__main__":
    minio_client = MinioClient(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
    )

    bucket_name = "images"
    image_path = "path/to/your/image.jpg"

    # 画像をアップロード
    err = minio_client.upload_image(bucket_name, image_path)
    if err is not None:
        print(f"Upload failed: {err}")

    # 署名付きURLを取得
    urls, err = minio_client.get_presigned_urls(bucket_name)
    if err is not None:
        print(f"Failed to get presigned URLs: {err}")

    for url in urls:
        print(url)
