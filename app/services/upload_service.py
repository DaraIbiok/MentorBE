"""
File upload service — saves files to an absolute path so they're
always found regardless of where uvicorn is launched from.
"""

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile, HTTPException

from app.core.config import settings

# Always resolve uploads relative to this file's location (the project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_BASE = BASE_DIR / settings.UPLOAD_DIR

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_DOC_EXTS = {".pdf", ".doc", ".docx", ".txt", ".md"}


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


async def upload_file(file: UploadFile, subfolder: str = "general") -> str:
    """Save file and return its relative URL path e.g. /uploads/avatars/abc.jpg"""
    ext = _ext(file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTS | ALLOWED_DOC_EXTS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MB)",
        )

    if settings.UPLOAD_PROVIDER == "s3":
        return await _upload_s3(content, subfolder, f"{uuid.uuid4().hex}{ext}", file.content_type or "application/octet-stream")

    return await _upload_local(content, subfolder, f"{uuid.uuid4().hex}{ext}")


async def _upload_local(content: bytes, subfolder: str, filename: str) -> str:
    dest_dir = UPLOAD_BASE / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    # Return relative URL path — profile.py will convert to absolute URL
    return f"/uploads/{subfolder}/{filename}"


async def _upload_s3(content: bytes, subfolder: str, filename: str, content_type: str) -> str:
    try:
        import boto3
    except ImportError:
        raise HTTPException(status_code=500, detail="boto3 not installed")

    key = f"{subfolder}/{filename}"
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )
        s3.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=content, ContentType=content_type)
        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_S3_REGION}.amazonaws.com/{key}"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}")