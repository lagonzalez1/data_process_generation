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

bedrock = boto3.client('bedrock-runtime', region_name='us-west-1')

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
            return None
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": item['content']
                        } for item in self.prompt_data.get("messages")
                    ]
                }
            ]
            logger.info(f"[INFO AMAZON MODEL] invoked and pushing messages {messages}")
            if not messages:
                return None

            request_body = {
                "messages": messages, 
                "inferenceConfig": {
                    "maxTokens": self.prompt_data.get("max_tokens", 20000),
                    "topP" : self.prompt_data.get("top_p", 0.7),
                    "temperature": self.prompt_data.get("temperature")
                }
            }
            logger.info(f"[INFO AMAZON MODEL] request body{request_body}")

            model_id = os.getenv("MODEL_ID")
            if not model_id:
                raise AmazonModelError(
                    message="MODEL_ID environment variable is not set",
                    error_type="ConfigurationError"
                )

            logger.info(f"[INFO] Using model ID: {model_id}")
            # Invoke the model
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            logger.info(f"[INFO AMAZON] Response from bedrock model {response}")
            if not response:
                raise AmazonModelError(
                    message="Empty response from Bedrock API",
                    error_type="EmptyResponseError"
                )
            
            response_body = json.loads(response['body'].read())
            usage = response_body.get('usage', {})

            self.set_metadata(usage)    
            logger.info(f"[INFO AMAZON] Successfully invoked model '{os.getenv('MODEL_ID')}' with response type {type(response)}.")
            text = response_body['output']['message']['content'][0]['text']
            text = text.strip()
            if text.startswith('```json'):
                text = text[7:-3]
            elif text.startswith('```'):
                text = text[3:-3]
            
            logger.info(f"[INFO AMAZON] text: {text}")
            valid_response = self.response_validator.model_validate_json(text)
            return valid_response.model_dump()
        except (BotoCoreError, ClientError, ValidationError, ValueError) as e:
            logger.error(f"[ERROR] Model invocation failed: {e}", exc_info=True)
            raise 
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error: {e}", exc_info=True)
            raise AmazonModelError(
                message=f"Unexpected error: {str(e)}",
                error_type="UnexpectedError"
            )

