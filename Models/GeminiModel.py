import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError, ValidationError
from typing import Optional
from Validation.AssessmentResponseValidator import Assessment

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

load_dotenv()

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

"""
    Gemini Model 

"""
class GeminiModel:
    def __init__(self, response_validator: Optional[BaseModel], prompt_data: Optional[dict] ):
        logger.info("[INFO] call stack init GeminiModel")
        self.prompt_data = prompt_data 
        self.response_validator = response_validator
        self.response_metadata: Optional[dict] = None

    def set_metadata(self, metadata: Optional[dict]):
        self.response_metadata = metadata
    
    def _invoke_model(self) -> dict:
        try:
            content = [item['content'] for item in self.prompt_data.get("messages")]
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=self.response_validator.model_json_schema(),
                    temperature=self.prompt_data.get("temperature")
                )
            )
            if not response:
                return None
            
            logger.info(f"[INFO GOOGLE] Successfully invoked model with response type {type(response)}'.")
            validated_data = self.response_validator.model_validate_json(response.text)
            self.set_metadata(dict(response.usage_metadata))

            return validated_data.model_dump()
        except (ValidationError, ClientError) as e:
            logger.info(f"[ERROR] Exception found:  {e}")
            raise
        except Exception as e:
            logger.info(f"[ERROR] Exception found:  {e}")
            raise
        
    """ 
        Parse the response metadata according to GeminiAPI
        link :https://ai.google.dev/api/generate-content#UsageMetadata

    """
    def get_usage(self) -> Optional[dict]:
        try:
            if self.response_metadata is None:
                return None
            usage = {
                'input_tokens': self.response_metadata['prompt_token_count'],
                'output_tokens': self.response_metadata['candidates_token_count'],
                'total_tokens': int(self.response_metadata['prompt_token_count']) + int(self.response_metadata['candidates_token_count'])
            }
            return usage
        except (AttributeError, json.JSONDecodeError) as e:
            raise Exception(f"unable to get usage {e}.")

    


