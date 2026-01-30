# If you don't need complex validation yet
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from uuid import UUID, uuid4
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Choice(BaseModel):
    choice_id: Optional[int]
    choice_text: str
    is_correct: bool
    order_number: int

class Question(BaseModel):
    question_id: Optional[int] 
    standard_text: str
    image_url: Optional[str] = None
    question_text: str
    question_type: Literal["multiple_choice", "multi_select_choice", "short_answer", "true_false"]
    points: float
    order_number: int
    is_required: bool = True
    choices: List[Choice] = []

class Assessment(BaseModel):
    questions: List[Question]


