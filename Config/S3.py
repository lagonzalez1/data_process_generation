import os
import boto3
from dotenv import load_dotenv
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3:
    def __init__(self):
        self.s3 = self._connect_s3()
    
    def _connect_s3(self):
        return boto3.client('s3')

    def put_object(self, payload: any, bucket: str, full_key: str, content_type: str) -> bool:
        """ Put object method for s3"""
        try:
            logger.info(f"[INFO S3]Starting S3 upload: s3://{bucket}/{full_key}", exc_info=True)
            response = self.s3.put_object(
                Bucket=bucket,
                Key=full_key,
                Body=payload,
                ContentType=content_type
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                logger.info(f"[INFO S3] upload successful: s3://{bucket}/{full_key}", exc_info=True)
                return True
            else:
                logger.error(f"[ERROR S3] upload failed with status: {response['ResponseMetadata']['HTTPStatusCode']}", exc_info=True)
                return False
        except RuntimeError as e:
            logging.error("[ERROR] unable to push to s3")