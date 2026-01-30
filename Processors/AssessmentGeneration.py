
import os
from typing import Optional
import logging
from Models.Prompts.Builder import PromptBuilder, PromptConfig
from Models.GeminiModel import GeminiModel
from Models.AmazonModel import AmazonModel
from Validation.AssessmentResponseValidator import Assessment
from psycopg2.extras import Json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AssessmentGeneration:
    def __init__(self, organization_id: int, generate_assessment: Optional[dict],  business_repository: Optional[any]):
        logger.info("[INFO] call stack init AssessmentGeneration")
        self.organization_id = organization_id
        self.business_repository = business_repository
        self.generate_assessment = generate_assessment
        self.prompt_builder = PromptBuilder()
        self.validator_class = Assessment
    
    def __del__(self):
        pass

    """ To do: Log the LLM usage to stu_tracker.LLM_usage for both generation types """        
    def process_question_generation(self) ->bool:
        """ Main caller, returns true boolean if succeded."""
        try:
            district = self.business_repository.get_district_by_id((self.organization_id, self.generate_assessment.get("district_id")))
            subjects = self.business_repository.get_subjects_by_id((self.organization_id, self.generate_assessment.get("district_id")))

            prompt_config = PromptConfig(
                model=os.getenv("MODEL_TYPE"),
                template_name=f"Identity_questions",
                variables={
                    "grade_level": self.generate_assessment.get("grade"),
                    "difficulty": self.generate_assessment.get("difficulty"),
                    "question_count": self.generate_assessment.get("question_count"),
                    "max_points": self.generate_assessment.get("max_points"),
                    "topic": subjects['title'],
                    "district": district['name'],
                    "custom_instructions": self.generate_assessment.get("description")
                },
                temperature=0.6,
                max_tokens=50000
            )
            prompt_data = self.prompt_builder.build(prompt_config)

            if not prompt_data:
                raise ValueError("Failed to build prompt")
            
            ## Note: Create a while loop to get a N number of responses, compare pick the best. 
            ## Note: Also If any failures a retry can be usefull. 
            match prompt_data['model']:
                case "GOOGLE":
                    llm = GeminiModel(self.validator_class, prompt_data)
                    llm_response = llm._invoke_model()
                    if not llm_response:
                        update_count = self.business_repository.update_questions_status_by_input_key(('RETRY', self.organization_id, self.generate_assessment.get("s3_output_key")))
                        logger.info(f"[INFO] llm response failed, will try again, update count {update_count}.")
                        return False
                    usage = llm.get_usage()
                    if not usage:
                        return False
                    logger.info(f"[INFO AMAZON] usage {usage}")

                    self.business_repository.update_aquestion_usage_by_input_key((usage['input_tokens'], usage['output_tokens'], self.organization_id, self.generate_assessment.get("s3_output_key")))
                    self.business_repository.update_aquestion_json_by_input_key((Json(llm_response), self.organization_id, self.generate_assessment.get("s3_output_key")))
                    return True
                case "AMAZON":
                    llm = AmazonModel(self.validator_class, prompt_data)
                    llm_response = llm._invoke_model()
                    if not llm_response:
                        update_count = self.business_repository.update_questions_status_by_input_key(('RETRY', self.organization_id, self.generate_assessment.get("s3_output_key")))
                        return False
                    
                    usage = llm.get_usage()
                    if not usage:
                        return False
                    logger.info(f"[INFO AMAZON] usage {usage}")

                    self.business_repository.update_aquestion_usage_by_input_key((usage['input_tokens'], usage['output_tokens'], self.organization_id, self.generate_assessment.get("s3_output_key")))
                    self.business_repository.update_aquestion_json_by_input_key((Json(llm_response), self.organization_id, self.generate_assessment.get("s3_output_key")))
                    return True
            return True
        except Exception as e:
            logger.error("[ERROR] Questions generation", e)
            return False