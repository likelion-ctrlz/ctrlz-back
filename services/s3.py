import os

import boto3

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
)


def upload_file(file_bytes: bytes, key: str, content_type: str) -> str:
    """S3에 파일 업로드 후 URL 반환"""
    s3_client.put_object(
        Bucket=AWS_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
