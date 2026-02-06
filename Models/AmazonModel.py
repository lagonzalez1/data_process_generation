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

custom_config = Config(
    connect_timeout=10,
    read_timeout=3600,
    retries={'max_attempts': 2}
)

bedrock = boto3.client('bedrock-runtime', region_name='us-west-1', config=custom_config)

class AmazonModelError(Exception):
    """Custom exception for Amazon Model errors"""
    def __init__(self, message: str, error_type: str = None, original_error: Exception = None):
        self.message = message
        self.error_type = error_type
        self.original_error = original_error
        super().__init__(self.message)

class AmazonModel:
    def __init__(self, response_validator: Optional[BaseModel], prompt_data: Optional[dict]):
        logger.info("[DEBUG AMAZON] === AmazonModel.__init__ called ===")
        logger.info(f"[DEBUG AMAZON] response_validator type: {type(response_validator)}")
        logger.info(f"[DEBUG AMAZON] prompt_data type: {type(prompt_data)}")
        logger.info(f"[DEBUG AMAZON] prompt_data: {prompt_data}")
        
        self.response_validator = response_validator
        self.prompt_data = prompt_data
        self.metadata = None

    def set_metadata(self, meta: Optional[dict]):
        logger.info(f"[DEBUG AMAZON] set_metadata called with: {meta}")
        self.metadata = meta

    def get_usage(self) -> Optional[dict]: 
        logger.info("[DEBUG AMAZON] get_usage called")
        try:
            logger.info(f"[DEBUG AMAZON] Current metadata: {self.metadata}")
            usage  = {
                'input_tokens': self.metadata['inputTokens'],
                'output_tokens': self.metadata['outputTokens'],
                'total_tokens': self.metadata['totalTokens']
            }
            logger.info(f"[DEBUG AMAZON] Returning usage: {usage}")
            return usage
        except Exception as e:
            logger.error(f"[ERROR AMAZON] get_usage failed: {e}")
            raise Exception(f"Unable to find metatdata for amazon invoke call.: {e}")
        
    """ 
        Response varies by model so using Nova or claude ... will change the response dict
        To have a window of deterministic responses, models must be tracker of their response types and logged.
        
    """
    def _invoke_model(self) -> dict:
        logger.info("[DEBUG AMAZON] ========================================")
        logger.info("[DEBUG AMAZON] === _invoke_model CALLED ===")
        logger.info("[DEBUG AMAZON] ========================================")
        
        logger.info(f"[DEBUG AMAZON] prompt_data exists: {self.prompt_data is not None}")
        logger.info(f"[DEBUG AMAZON] prompt_data type: {type(self.prompt_data)}")
        logger.info(f"[DEBUG AMAZON] prompt_data value: {self.prompt_data}")
        
        if not self.prompt_data:
            logger.error("[ERROR AMAZON] !!! prompt_data is None or empty - ABORTING !!!")
            logger.error(f"[ERROR AMAZON] prompt_data value was: {self.prompt_data}")
            return None
        
        logger.info(f"[DEBUG AMAZON] prompt_data keys: {list(self.prompt_data.keys()) if isinstance(self.prompt_data, dict) else 'N/A'}")
        
        try:
            logger.info("[DEBUG AMAZON] ===== STEP 1: Extracting messages from prompt_data =====")
            raw_messages = self.prompt_data.get("messages")
            logger.info(f"[DEBUG AMAZON] Raw messages from prompt_data.get('messages'): {raw_messages}")
            logger.info(f"[DEBUG AMAZON] Raw messages type: {type(raw_messages)}")
            logger.info(f"[DEBUG AMAZON] Raw messages is None: {raw_messages is None}")
            logger.info(f"[DEBUG AMAZON] Raw messages length: {len(raw_messages) if raw_messages else 'N/A'}")
            
            if raw_messages:
                logger.info(f"[DEBUG AMAZON] First message sample: {raw_messages[0] if len(raw_messages) > 0 else 'EMPTY'}")
            
            logger.info("[DEBUG AMAZON] Constructing messages list for Bedrock...")
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
            logger.info(f"[DEBUG AMAZON] ✓ Messages constructed successfully")
            logger.info(f"[DEBUG AMAZON] Messages structure: {json.dumps(messages, indent=2)}")
            logger.info(f"[DEBUG AMAZON] Messages length: {len(messages)}")
            
            if not messages:
                logger.error("[ERROR AMAZON] !!! Messages list is empty after construction - ABORTING !!!")
                return None

            logger.info("[DEBUG AMAZON] ===== STEP 2: Building request body =====")
            max_tokens_val = self.prompt_data.get("max_tokens", 20000)
            top_p_val = self.prompt_data.get("top_p", 0.7)
            temperature_val = self.prompt_data.get("temperature")
            
            logger.info(f"[DEBUG AMAZON] Extracted max_tokens: {max_tokens_val}")
            logger.info(f"[DEBUG AMAZON] Extracted top_p: {top_p_val}")
            logger.info(f"[DEBUG AMAZON] Extracted temperature: {temperature_val}")
            
            request_body = {
                "messages": messages, 
                "inferenceConfig": {
                    "maxTokens": max_tokens_val,
                    "topP": top_p_val,
                    "temperature": temperature_val
                }
            }
            logger.info(f"[DEBUG AMAZON] ✓ Request body constructed")
            logger.info(f"[DEBUG AMAZON] Request body: {json.dumps(request_body, indent=2)}")

            logger.info("[DEBUG AMAZON] ===== STEP 3: Getting MODEL_ID from environment =====")
            model_id = os.getenv("MODEL_ID")
            logger.info(f"[DEBUG AMAZON] MODEL_ID from env: {model_id}")
            logger.info(f"[DEBUG AMAZON] MODEL_ID is None: {model_id is None}")
            logger.info(f"[DEBUG AMAZON] MODEL_ID is empty: {model_id == ''}")
            
            if not model_id:
                logger.error("[ERROR AMAZON] !!! MODEL_ID environment variable is NOT SET !!!")
                logger.error(f"[ERROR AMAZON] All env vars starting with MODEL: {[k for k in os.environ.keys() if 'MODEL' in k]}")
                raise AmazonModelError(
                    message="MODEL_ID environment variable is not set",
                    error_type="ConfigurationError"
                )

            logger.info(f"[DEBUG AMAZON] ✓ Using model ID: {model_id}")
            
            logger.info("[DEBUG AMAZON] ===== STEP 4: Checking Bedrock client =====")
            logger.info(f"[DEBUG AMAZON] Bedrock client type: {type(bedrock)}")
            logger.info(f"[DEBUG AMAZON] Bedrock client region: {bedrock.meta.region_name}")
            
            logger.info("[DEBUG AMAZON] ===== STEP 5: Invoking Bedrock model =====")
            logger.info(f"[DEBUG AMAZON] About to call bedrock.invoke_model with:")
            logger.info(f"[DEBUG AMAZON]   - modelId: {model_id}")
            logger.info(f"[DEBUG AMAZON]   - body length: {len(json.dumps(request_body))} chars")
            
            try:
                logger.info("[DEBUG AMAZON] >>> CALLING bedrock.invoke_model() NOW <<<")
                response = bedrock.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body)
                )
                logger.info("[DEBUG AMAZON] ✓✓✓ bedrock.invoke_model() RETURNED SUCCESSFULLY ✓✓✓")
            except ClientError as ce:
                logger.error("[ERROR AMAZON] !!! ClientError during bedrock.invoke_model !!!")
                logger.error(f"[ERROR AMAZON] Error Code: {ce.response.get('Error', {}).get('Code', 'N/A')}")
                logger.error(f"[ERROR AMAZON] Error Message: {ce.response.get('Error', {}).get('Message', 'N/A')}")
                logger.error(f"[ERROR AMAZON] HTTP Status Code: {ce.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'N/A')}")
                logger.error(f"[ERROR AMAZON] Full error: {ce}", exc_info=True)
                raise
            except BotoCoreError as bce:
                logger.error("[ERROR AMAZON] !!! BotoCoreError during bedrock.invoke_model !!!")
                logger.error(f"[ERROR AMAZON] Error: {bce}", exc_info=True)
                raise
            except Exception as e:
                logger.error("[ERROR AMAZON] !!! Unexpected error during bedrock.invoke_model !!!")
                logger.error(f"[ERROR AMAZON] Error type: {type(e)}")
                logger.error(f"[ERROR AMAZON] Error: {e}", exc_info=True)
                raise

            logger.info(f"[DEBUG AMAZON] Response type: {type(response)}")
            logger.info(f"[DEBUG AMAZON] Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
            
            if not response:
                logger.error("[ERROR AMAZON] !!! Empty response from Bedrock API !!!")
                raise AmazonModelError(
                    message="Empty response from Bedrock API",
                    error_type="EmptyResponseError"
                )
            
            logger.info("[DEBUG AMAZON] ===== STEP 6: Parsing response body =====")
            logger.info("[DEBUG AMAZON] Reading response body...")
            response_body = json.loads(response['body'].read())
            logger.info(f"[DEBUG AMAZON] ✓ Response body parsed")
            logger.info(f"[DEBUG AMAZON] Response body keys: {list(response_body.keys())}")
            logger.info(f"[DEBUG AMAZON] Response body: {json.dumps(response_body, indent=2)}")
            
            logger.info("[DEBUG AMAZON] ===== STEP 7: Extracting usage metadata =====")
            usage = response_body.get('usage', {})
            logger.info(f"[DEBUG AMAZON] Usage metadata: {usage}")

            self.set_metadata(usage)    
            logger.info(f"[DEBUG AMAZON] ✓ Successfully invoked model '{model_id}'")
            
            logger.info("[DEBUG AMAZON] ===== STEP 8: Extracting text from response =====")
            logger.info(f"[DEBUG AMAZON] Response body structure: {list(response_body.keys())}")
            
            text = response_body['output']['message']['content'][0]['text']
            logger.info(f"[DEBUG AMAZON] Raw text extracted (length: {len(text)})")
            logger.info(f"[DEBUG AMAZON] Raw text first 200 chars: {text[:200]}")
            
            text = text.strip()
            logger.info(f"[DEBUG AMAZON] Text after strip (length: {len(text)})")
            
            logger.info("[DEBUG AMAZON] ===== STEP 9: Cleaning code fences from text =====")
            if text.startswith('```json'):
                logger.info("[DEBUG AMAZON] Removing ```json fence")
                text = text[7:-3]
            elif text.startswith('```'):
                logger.info("[DEBUG AMAZON] Removing ``` fence")
                text = text[3:-3]
            else:
                logger.info("[DEBUG AMAZON] No code fence detected")
            
            logger.info(f"[DEBUG AMAZON] Cleaned text (length: {len(text)})")
            logger.info(f"[DEBUG AMAZON] Cleaned text first 500 chars: {text[:500]}")
            
            logger.info("[DEBUG AMAZON] ===== STEP 10: Validating response with Pydantic =====")
            logger.info(f"[DEBUG AMAZON] Validator class: {self.response_validator}")
            
            try:
                logger.info("[DEBUG AMAZON] Calling model_validate_json()...")
                valid_response = self.response_validator.model_validate_json(text)
                logger.info("[DEBUG AMAZON] ✓ Validation successful")
            except ValidationError as ve:
                logger.error("[ERROR AMAZON] !!! Pydantic validation failed !!!")
                logger.error(f"[ERROR AMAZON] Validation errors: {ve.errors()}")
                logger.error(f"[ERROR AMAZON] Failed text: {text}")
                raise
            
            logger.info(f"[DEBUG AMAZON] Valid response type: {type(valid_response)}")
            result = valid_response.model_dump()
            logger.info(f"[DEBUG AMAZON] Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            logger.info("[DEBUG AMAZON] ========================================")
            logger.info("[DEBUG AMAZON] === _invoke_model COMPLETED SUCCESSFULLY ===")
            logger.info("[DEBUG AMAZON] ========================================")
            
            return result
            
        except (BotoCoreError, ClientError, ValidationError, ValueError) as e:
            logger.error(f"[ERROR AMAZON] !!! Known error type caught: {type(e).__name__} !!!")
            logger.error(f"[ERROR AMAZON] Model invocation failed: {e}", exc_info=True)
            raise 
        except Exception as e:
            logger.error(f"[ERROR AMAZON] !!! Unexpected error caught !!!")
            logger.error(f"[ERROR AMAZON] Error type: {type(e).__name__}")
            logger.error(f"[ERROR AMAZON] Unexpected error: {e}", exc_info=True)
            raise AmazonModelError(
                message=f"Unexpected error: {str(e)}",
                error_type="UnexpectedError"
            )