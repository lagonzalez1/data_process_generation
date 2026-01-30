from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

# Enums for known values
class GuideType(str, Enum):
    STUDY_GUIDE = "study_guide"
    LESSON_PLAN = "lesson_plan"
    REVIEW_GUIDE = "review_guide"
    ACTIVITY_GUIDE = "activity_guide"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

# Nested models
class KeyConcept(BaseModel):
    title: str = Field(..., description="Title of the key concept")
    explanation: str = Field(..., description="Detailed explanation of the concept")
    examples: List[str] = Field(
        default_factory=list,
        description="Examples illustrating the concept"
    )

class ActivityStep(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the step")
    description: str = Field(..., description="Description of the step")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Step 1",
                "description": "Select a short story with a clear conflict."
            }
        }

class Activity(BaseModel):
    title: str = Field(..., description="Title of the activity")
    description: str = Field(..., description="Detailed description of the activity")
    steps: List[str] = Field(
        ..., 
        description="Step-by-step instructions for the activity",
        min_length=1
    )
    expected_outcome: str = Field(
        ..., 
        description="Expected learning outcome from the activity"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Conflict Analysis",
                "description": "In this activity, students will analyze the main conflict...",
                "steps": [
                    "Select a short story with a clear conflict.",
                    "Identify the main conflict and its type..."
                ],
                "expected_outcome": "Students will gain a deeper understanding of how conflict shapes..."
            }
        }

class AssessmentQuestion(BaseModel):
    question: str = Field(..., description="The assessment question")
    answer: str = Field(
        default="(Student's response)", 
        description="Expected answer or placeholder"
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM,
        description="Difficulty level of the question"
    )
    question_type: Optional[str] = Field(
        None,
        description="Type of question (multiple_choice, short_answer, essay, etc.)"
    )
    points: Optional[int] = Field(
        None,
        ge=0,
        description="Points allocated for this question"
    )

# Main model
class StudyGuide(BaseModel):
    """Study Guide model for educational content"""
    
    guide_type: GuideType = Field(
        default=GuideType.STUDY_GUIDE,
        description="Type of educational guide"
    )
    subject: str = Field(
        ..., 
        description="Subject area (e.g., HS ELA, Math, Science)",
        examples=["HS ELA", "Algebra I", "Biology"]
    )
    grade_level: str = Field(
        ..., 
        description="Grade level or age group",
        examples=["9", "9-10", "High School"]
    )
    duration_minutes: int = Field(
        ...,
        gt=0,
        le=480,  # 8 hours max
        description="Estimated duration in minutes"
    )
    learning_objectives: List[str] = Field(
        ...,
        min_length=1,
        description="List of learning objectives for the guide"
    )
    key_concepts: List[KeyConcept] = Field(
        ...,
        min_length=1,
        description="Key concepts covered in the guide"
    )
    activities: List[Activity] = Field(
        ...,
        min_length=1,
        description="Learning activities for students"
    )
    assessment_questions: List[AssessmentQuestion] = Field(
        ...,
        min_length=1,
        description="Assessment questions to evaluate learning"
    )
    summary: str = Field(
        ...,
        description="Summary of the study guide content"
    )
    materials_needed: List[str] = Field(
        default_factory=list,
        description="Materials required for the activities"
    )
    appendix: Optional[str] = Field(
        None,
        description="Additional resources or appendices"
    )
    
    # Optional metadata fields
    version: Optional[str] = Field(
        None,
        description="Version of the study guide"
    )
    created_by: Optional[str] = Field(
        None,
        description="Creator of the study guide"
    )
    standards_aligned: Optional[List[str]] = Field(
        None,
        description="Educational standards this guide aligns with"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "guide_type": "study_guide",
                "subject": "HS ELA",
                "grade_level": "9",
                "duration_minutes": 60,
                "learning_objectives": [
                    "To analyze the main conflict in a short story",
                    "To understand how theme is developed through characters and conflict"
                ],
                "key_concepts": [
                    {
                        "title": "Conflict",
                        "explanation": "Conflict is a crucial element...",
                        "examples": [
                            "In the short story 'The Lottery'...",
                            "'The Tell-Tale Heart' by Edgar Allan Poe..."
                        ]
                    }
                ],
                "activities": [
                    {
                        "title": "Conflict Analysis",
                        "description": "In this activity, students will analyze...",
                        "steps": [
                            "Select a short story with a clear conflict.",
                            "Identify the main conflict and its type..."
                        ],
                        "expected_outcome": "Students will gain a deeper understanding..."
                    }
                ],
                "assessment_questions": [
                    {
                        "question": "What is the main conflict in the short story you analyzed?",
                        "answer": "(Student's response)",
                        "difficulty": "medium"
                    }
                ],
                "summary": "This study guide focuses on literary analysis...",
                "materials_needed": ["Short stories for analysis", "Writing materials"],
                "appendix": "Additional resources for literary analysis..."
            }
        }
    
# Alternative simplified version without enums
class Material(BaseModel):
    """Simplified version without enums for quick validation"""
    
    guide_type: str = "study_guide"
    subject: str
    grade_level: str
    duration_minutes: int
    learning_objectives: List[str]
    key_concepts: List[KeyConcept]
    activities: List[Activity]
    assessment_questions: List[AssessmentQuestion]
    summary: str
    materials_needed: List[str]
    appendix: Optional[str] = None