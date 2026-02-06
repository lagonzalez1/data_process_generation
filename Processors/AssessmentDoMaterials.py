
import os
from typing import Optional
import logging
from Models.Prompts.Builder import PromptBuilder, PromptConfig
from Models.GeminiModel import GeminiModel
from Models.AmazonModel import AmazonModel
from Validation.AssessmentResponseValidator import Assessment
from psycopg2.extras import Json
from typing import Dict, Any, Optional, List


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Test they exist
logger.info(f"[INFO] PromptBuilder: {PromptBuilder}")
logger.info(f"[INFO] PromptConfig: {PromptConfig}")


""" Use the materails provided for additional targeted assessments"""
class AssessmentDoMaterials:
    def __init__(self, organization_id: int, generate_assessment: Optional[dict],  business_repository: Optional[any]):
        logger.info("[INFO] call stack init AssessmentDoMaterials")
        self.organization_id = organization_id
        self.business_repository = business_repository
        self.generate_assessment = generate_assessment
        self.prompt_builder = PromptBuilder()
        self.validator_class = Assessment
    

    """ To do: Log the LLM usage to stu_tracker.LLM_usage for both generation types """        
    def process_question_generation(self) ->bool:
        """ Main caller, returns true boolean if succeded."""
        try:
            district = self.business_repository.get_district_by_id((self.organization_id, self.generate_assessment.get("district_id")))
            if district is None:
                logger.info(f"[INFO] unable to get get_district_by_id")
                return False
            subjects = self.business_repository.get_subjects_by_id((self.organization_id, self.generate_assessment.get("district_id")))
            if subjects is None:
                logger.info(f"[INFO] unable to get get_district_by_id")
                return False


            logger.info(f"[INFO] district data:  {district}")
            logger.info(f"[INFO] subjects data:  {subjects}")
            try:
                prompt_config = PromptConfig(
                    model=os.getenv("MODEL_TYPE"),
                    template_name=f"Identity_question_given_materials",
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
                        max_tokens=20000
                )
                logger.info(f"[INFO] Step 3: Created prompt_config")
            except Exception as e:
                logger.error(f"[ERROR] Failed to create PromptConfig: {e}")
                return False

            if prompt_config is None:
                logger.info(f"[INFO] unable to create prompt_config {prompt_config}")
                return False

            prompt_data = self.prompt_builder.build(prompt_config)
            if not prompt_data:
                logger.info(f"[INFO] unable to get prompt data")
                return False
            
            logger.info(f"[INFO] Step 4: Built prompt_data for model: {prompt_data.get('model')}")

            model_result, usage = self._invoke_llm_model(prompt_data)
            if model_result is None:
                return False

            logger.info(f"[INFO] Step 5: Invoking {type(model_result)} model")
            
            success = self._save_generation_results(model_result, usage)
            return success
        except Exception as e:
            logger.error("[ERROR] Questions generation", e)
            return False
    
    def _invoke_llm_model(self, prompt_data: Dict[str, Any]) -> tuple:
        """Invoke appropriate LLM model based on configuration."""
        try:
            model_type = prompt_data.get('model', 'GOOGLE').upper()
            match model_type:
                case "GOOGLE":
                    llm_model = GeminiModel(self.validator_class, prompt_data)
                case "AMAZON":
                    llm_model = AmazonModel(self.validator_class, prompt_data)
                case _:
                    logger.error(f"[ERROR] Unsupported model type: {model_type}")
                    return None, None

            # Invoke model
            success = llm_model._invoke_model()
            if not success:
                logger.warning(f"[WARN] Model invocation failed for {model_type}, triggering retry")
                self.retry_event()
                return None, None

            # Get usage metrics
            usage = llm_model.get_usage()
            if not usage:
                logger.error(f"[ERROR] No usage metrics returned from {model_type} model")
                return None, None

            logger.info(f"[INFO {model_type}] Usage: {usage}")
            return success, usage

        except Exception as e:
            logger.error(f"[ERROR] Failed in _invoke_llm_model: {e}")
            return None, None
    
    def _save_generation_results(self, model_result, usage) -> bool:
        """Save generation results to database."""
        try:
            self.business_repository.update_aquestion_usage_by_input_key((usage['input_tokens'], usage['output_tokens'], self.organization_id, self.generate_assessment.get("s3_output_key")))
            self.business_repository.update_aquestion_json_by_input_key((Json(model_result), self.organization_id, self.generate_assessment.get("s3_output_key")))
            
            logger.info("[INFO] Successfully saved generation results")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to save generation results: {e}")
            return False