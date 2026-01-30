import os
import boto3
from dotenv import load_dotenv
import logging


load_dotenv()

# --- Python logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class SQS:
    def __init__(self):
        self.local =  self.is_local_env()
        self.sqs = self._sqs()
        self.url = self._sqs_url()

    def is_local_env(self):
        return bool(os.getenv("APP_MODE") == "dev")

    def _sqs(self):
        if self.is_local_env:
            sqs = boto3.client(
                "sqs",
                region_name="us-west-1",
                endpoint_url="http://localhost:4566",
                aws_access_key_id="test",
                aws_secret_access_key="test"
            )
        else:
            sqs = boto3.client(
                "sqs",
                region_name='us-west-1',
            )
        return sqs
    
    def _sqs_url(self):
        if self.local:
            return self.sqs.get_queue_url(QueueName=os.getenv("QUEUE_NAME"))["QueueUrl"]
        else:
            return os.getenv("SQS_URL")
        
    def delete_sqs_message(self, ReceiptHandle: str):
        self.sqs.delete_message(
            QueueUrl=self.url,
            ReceiptHandle=ReceiptHandle,
        )
