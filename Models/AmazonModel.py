import os
import json
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel, ValidationError, ValidationError
import logging
load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = Config(
    region_name="us-west-1",
    connect_timeout=3600, 
    read_timeout=3600
)
bedrock = boto3.client(
    "bedrock-runtime", 
    config=config
)
class AmazonModelError(Exception):
    """Custom exception for Amazon Model errors"""
    def __init__(self, message: str, error_type: str = None, original_error: Exception = None):
        self.message = message
        self.error_type = error_type
        self.original_error = original_error
        super().__init__(self.message)

class AmazonModel:
    def __init__(self, response_validator: Optional[BaseModel], prompt_data: Optional[dict]):
        self.response_validator = response_validator
        self.prompt_data = prompt_data
        self.metadata = None

    def set_metadata(self, meta: Optional[dict]):
        self.metadata = meta

    def get_usage(self) -> Optional[dict]: 
        try:
            usage  = {
                'input_tokens': self.metadata['inputTokens'],
                'output_tokens': self.metadata['outputTokens'],
                'total_tokens': self.metadata['totalTokens']
            }
            return usage
        except Exception as e:
            raise Exception(f"Unable to find metatdata for amazon invoke call.: {e}")
        
    """ 
        Response varies by model so using Nova or claude ... will change the response dict
        To have a window of deterministic responses, models must be tracker of their response types and logged.
        
    """
    def _invoke_model(self) -> dict:
        if not self.prompt_data:
            raise RuntimeError("no prompting data found")
        try:
            messages = [dict({"role": item["role"], "content": [dict({"text": item['content']})]}) for item in self.prompt_data.get("messages")]
            messages = messages[::-1]
            if not messages:
                raise ValueError("No messages found in prompt_data")

            request_body = {
                "messages": messages, 
                "inferenceConfig": {
                    "maxTokens": self.prompt_data.get("max_tokens", 65536),
                    "topP" : self.prompt_data.get("top_p", 0.7),
                    "temperature": self.prompt_data.get("temperature")
                }
            }
            # Invoke the model
            response = bedrock.invoke_model(
                modelId=os.getenv("MODEL_ID"),
                body=json.dumps(request_body)
            )
            if not response:
                raise AmazonModelError(
                    message="Empty response from Bedrock API",
                    error_type="EmptyResponseError"
                )
            
            response_body = json.loads(response['body'].read())
            usage = response_body.get('usage', {})
            self.set_metadata(usage)    
            logger.info(f"[INFO AMAZON] Successfully invoked model '{os.getenv("MODEL_ID")} with response type {type(response)}'.")
            text = response_body['output']['message']['content'][0]['text']
            text = text.strip()
            if text.startswith('```json'):
                text = text[7:-3]
            elif text.startswith('```'):
                text = text[3:-3]
            
            logger.info(f"[INFO AMAZON] text: {text}")
            valid_response = self.response_validator.model_validate_json(text)
            return valid_response.model_dump()

        except BotoCoreError as e:
            logger.info(f"[ERROR AMAZON BEDROCK] BotoCoreError invoked:  {e}")
            return None
        except (ClientError, Exception) as e:
            logger.info(f"[ERROR AMAZON BEDROCK] Client error invoked:  {e}")
            return None
        except ValidationError as e:
            logger.info(f"[ERROR AMAZON BEDROCK] ValidationError found:  {e}")
            return None
        except ValueError as e:
            logger.error(f"[ERROR AMAZON BEDROCK] ValueError while invoking model: {e}")
            return None

