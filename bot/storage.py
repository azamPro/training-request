"""
PDF storage — local disk or S3, depending on USE_S3 config flag.
"""

import logging
import os
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from bot.config import (
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    AWS_S3_BUCKET, AWS_REGION,
    GENERATED_PDF_DIR, USE_S3,
)

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
    return _s3_client


def save_pdf(pdf_bytes: bytes, telegram_id: int, request_id: int) -> str:
    """
    Persist a PDF and return a storage path/URL string.
    Uses S3 when USE_S3 is true, otherwise saves to local disk.
    """
    filename = f"{telegram_id}_{request_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

    if USE_S3:
        key = f"pdfs/{telegram_id}/{filename}"
        try:
            _get_s3().put_object(
                Bucket=AWS_S3_BUCKET,
                Key=key,
                Body=pdf_bytes,
                ContentType="application/pdf",
            )
            path = f"s3://{AWS_S3_BUCKET}/{key}"
            logger.info("PDF uploaded to S3: %s", path)
            return path
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3 upload failed, falling back to local disk: %s", exc)

    # Local disk fallback
    os.makedirs(GENERATED_PDF_DIR, exist_ok=True)
    local_path = os.path.join(GENERATED_PDF_DIR, filename)
    with open(local_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info("PDF saved locally: %s", local_path)
    return local_path
