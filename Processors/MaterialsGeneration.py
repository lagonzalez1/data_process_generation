
import os
from typing import Optional
import logging
from Models.Prompts.Builder import PromptBuilder, PromptConfig
from Models.GeminiModel import GeminiModel
from Models.AmazonModel import AmazonModel
from Validation.MaterialsResponseValidation import Material
from psycopg2.extras import Json
from typing import Dict, Any, Optional, List



logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Test they exist
logger.info(f"[INFO] PromptBuilder: {PromptBuilder}")
logger.info(f"[INFO] PromptConfig: {PromptConfig}")


class MaterialsGeneration:

    def __init__(self, organization_id: int, generate_materials: Optional[dict],  business_repository: Optional[any]):
        logger.info("[INFO] call stack init MaterialsGeneration")
        self.organization_id = organization_id
        self.business_repository = business_repository
        self.generate_materials = generate_materials
        self.prompt_builder = PromptBuilder()
        self.validator_class = Material

    """ To do: Log the LLM usage to stu_tracker.LLM_usage for both generation types """

    def retry_event(self)->bool:
        update_event = self.business_repository.update_materials_status_by_input_key(('RETRY', self.organization_id, self.generate_materials.get("s3_output_key")))
        return update_event

    def process_materials_generation(self)->bool:
        """ Main caller, returns boolean if succeded."""
        try:
            assessment_data = self.business_repository.get_assessment_by_id((self.organization_id, self.generate_materials.get("assessment_id")))
            if assessment_data is None:
                logger.info(f"[INFO] assessment_data {assessment_data}")
                return False

            logger.info(f"[INFO] assessment_data {assessment_data}")
            # Fetch assessment data
            try:
                prompt_config = PromptConfig(
                    model=os.getenv("MODEL_TYPE"),
                    template_name=f"Identity_materials",
                    variables={
                        "grade_level": self.generate_materials.get("grade"), 
                        "subject": assessment_data['subject_title'],
                        "assessment_title":  assessment_data['assessment_title'],
                        "assessment_description": assessment_data['assessment_description'],
                        "subject_description": assessment_data['subject_description'],
                        "custom_instructions": self.generate_materials.get("custom_instructions")
                    },
                    temperature=0.6,
                    top_p=0.8,
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
            
            logger.info(f"[INFO] Step 5: Invoking {type(model_result)} model")
        
            success = self._save_generation_results(model_result, usage)
            return success
        except Exception as e:
            logger.error(f"[ERROR] Failed in process_materials_generation: {e}", exc_info=True)
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

            # Get usage metrics
            usage = llm_model.get_usage()
            if not usage:
                logger.error(f"[ERROR] No usage metrics returned from {model_type} model")
                return None, None

            logger.info(f"[INFO {model_type}] Usage: {usage}")
            return success, usage

        except Exception as e:
            logger.error(f"[ERROR] Failed in _invoke_llm_model: {e}")
            raise
    
    def _save_generation_results(self, model_result, usage) -> bool:
        """Save generation results to database."""
        try:
            
            # Update materials JSON
            self.business_repository.update_gmaterials_json_by_input_key(
                (Json(model_result), self.organization_id, self.generate_materials.get("s3_output_key"))
            )
            
            # Update usage metrics
            self.business_repository.update_gmaterials_usage_by_input_key(
                (usage.get('input_tokens', 0), 
                usage.get('output_tokens', 0), 
                self.organization_id, 
                self.generate_materials.get("s3_output_key"))
            )
            
            logger.info("[INFO] Successfully saved generation results")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to save generation results: {e}")
            return False