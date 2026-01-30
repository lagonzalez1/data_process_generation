
import os
from typing import Optional
import json
import logging
from Models.Prompts.Builder import PromptBuilder, PromptConfig
from Models.GeminiModel import GeminiModel
from Models.AmazonModel import AmazonModel
from Validation.MaterialsResponseValidation import Material
from Processors.LogUsage import LogUsage
from psycopg2.extras import Json


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class MaterialsGeneration:

    def __init__(self, organization_id: int, generate_materials: Optional[dict],  business_repository: Optional[any]):
        logger.info("[INFO] call stack init MaterialsGeneration")
        self.organization_id = organization_id
        self.business_repository = business_repository
        self.generate_materials = generate_materials
        self.prompt_builder = PromptBuilder()
        self.validator_class = Material

    def __del__(self):
        del self.prompt_builder

    """ To do: Log the LLM usage to stu_tracker.LLM_usage for both generation types """

    def retry_event(self)->bool:
        update_event = self.business_repository.update_materials_status_by_input_key(('RETRY', self.organization_id, self.generate_materials.get("s3_output_key")))
        return update_event

    def process_materials_generation(self)->bool:
        """ Main caller, returns boolean if succeded."""
        try:
            assessment_data = self.business_repository.get_assessment_by_id((self.organization_id, self.generate_materials.get("assessment_id")))
            # Fetch assessment data
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
                max_tokens=50000
            )
            prompt_data = self.prompt_builder.build(prompt_config)
            if not prompt_data:
                raise ValueError("unable to build prompt data")
            
            match prompt_data['model']:
                case "GOOGLE":
                    llm_model = GeminiModel(self.validator_class, prompt_data)
                    success = llm_model._invoke_model()
                    if not success:
                        self.retry_event()
                        return False
                    
                    usage = llm_model.get_usage()
                    if not usage:
                        return False

                    logger.info(f"[INFO GOOGLE] usage {type(usage)}")

                    self.business_repository.update_gmaterials_json_by_input_key((Json(success), self.organization_id, self.generate_materials.get("s3_output_key")))
                    self.business_repository.update_gmaterials_usage_by_input_key((usage['input_tokens'], usage['output_tokens'], self.organization_id, self.generate_materials.get("s3_output_key")))
                    return True
                case "AMAZON":
                    llm_model = AmazonModel(self.validator_class, prompt_data)
                    success = llm_model._invoke_model()
                    if not success:
                        self.retry_event()
                        return False 
                    usage = llm_model.get_usage()
                    if not usage:
                        return False
                    logger.info(f"[INFO AMAZON] usage {usage}")

                    self.business_repository.update_gmaterials_json_by_input_key((Json(success), self.organization_id, self.generate_materials.get("s3_output_key")))
                    self.business_repository.update_gmaterials_usage_by_input_key((usage['input_tokens'], usage['output_tokens'], self.organization_id, self.generate_materials.get("s3_output_key")))
                    return True
            return True
        except Exception as e:
            logger.error(f"[ERROR] unable to process_materials_generation error: {e}")
            return False