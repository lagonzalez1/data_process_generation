from pydantic import BaseModel, Field
from typing import Optional
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class GenerateQuestions(BaseModel):
    s3_output_key: str = Field(alias="s3_output_key")
    district_id: int = Field(alias="district_id")
    subject_id: int = Field(alias="subject_id")
    description: str
    difficulty: str
    grade: int = Field(alias="grade_level")
    max_points: int
    question_count: int = Field(alias="question_count")
    custom_instructions: Optional[str] = Field(alias="custom_instructions")

class GenerateMaterials(BaseModel):
    s3_output_key: Optional[str] = Field(alias="s3_output_key")
    assessment_id: Optional[int] = Field(alias="assessment_id")
    custom_instructions: Optional[str] = Field(alias="custom_instructions")
    bias_type: Optional[str] = Field(alias="bias_type")
    
class Message(BaseModel):
    generate_type: str = Field(alias="generate_type")
    generate_questions: Optional[GenerateQuestions] = Field(default=None, alias="generate_questions")
    generate_materials: Optional[GenerateMaterials] = Field(default=None, alias="generate_materials")
    organization_id: int = Field(alias="organization_id")

class Payload(BaseModel):
    Task: str = Field(default=None, alias="task")
    Body: Message = Field(default=None, alias="body")

""" Parse the body of the incomming SQS message queue"""
class ParseClient:
    def __init__(self, body: str):
        logger.info("[INFO] call stack init ParseClient")
        self.body = body

    def parse_body(self) -> Optional[dict]:
        try:
            # This returns a Payload object
            payload_obj = Payload.model_validate_json(self.body)
            
            # Access the Message object
            message_obj = payload_obj.Body  # Note: capital B
            
            # Convert Message object to dictionary WITH ALIASES
            return message_obj.model_dump(by_alias=True)  # Add by_alias=True
                
        except Exception as e:
            logging.error(f"[ERROR] unable to parse with pydantic {e}")
            return None