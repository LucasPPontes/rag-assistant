import io
from typing import List, Dict, Any
from minio import Minio
from minio.error import S3Error
from config import settings

class MinIOService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME

    def ensure_bucket_exists(self) -> None:
        """Garante que o bucket configurado existe no MinIO."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"[MinIO] Bucket '{self.bucket_name}' criado com sucesso.")
            else:
                print(f"[MinIO] Bucket '{self.bucket_name}' verificado.")
        except S3Error as err:
            print(f"[MinIO Error] Falha ao verificar/criar bucket: {err}")
            raise err

    def upload_file(self, filename: str, content: bytes, content_type: str = "application/pdf") -> str:
        """Faz upload de um arquivo para o MinIO."""
        self.ensure_bucket_exists()
        file_stream = io.BytesIO(content)
        size = len(content)
        
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=filename,
            data=file_stream,
            length=size,
            content_type=content_type
        )
        print(f"[MinIO] Arquivo '{filename}' enviado com sucesso ({size} bytes).")
        return filename

    def get_file_bytes(self, filename: str) -> bytes:
        """Obtém os bytes de um arquivo armazenado no MinIO."""
        try:
            response = self.client.get_object(self.bucket_name, filename)
            content = response.read()
            response.close()
            response.release_conn()
            return content
        except S3Error as err:
            print(f"[MinIO Error] Erro ao baixar '{filename}': {err}")
            raise err

    def list_files(self) -> List[Dict[str, Any]]:
        """Lista todos os arquivos no bucket do MinIO."""
        self.ensure_bucket_exists()
        objects = self.client.list_objects(self.bucket_name)
        result = []
        for obj in objects:
            result.append({
                "filename": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
            })
        return result

    def delete_file(self, filename: str) -> bool:
        """Deleta um arquivo do MinIO."""
        try:
            self.client.remove_object(self.bucket_name, filename)
            print(f"[MinIO] Arquivo '{filename}' removido.")
            return True
        except S3Error as err:
            print(f"[MinIO Error] Erro ao remover '{filename}': {err}")
            return False

minio_service = MinIOService()
