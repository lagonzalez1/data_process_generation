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
        logger.info("[DEBUG MATERIALS] ========================================")
        logger.info("[DEBUG MATERIALS] === MaterialsGeneration.__init__ ===")
        logger.info("[DEBUG MATERIALS] ========================================")
        logger.info(f"[DEBUG MATERIALS] organization_id: {organization_id}")
        logger.info(f"[DEBUG MATERIALS] generate_materials type: {type(generate_materials)}")
        logger.info(f"[DEBUG MATERIALS] generate_materials: {generate_materials}")
        logger.info(f"[DEBUG MATERIALS] business_repository type: {type(business_repository)}")
        
        self.organization_id = organization_id
        self.business_repository = business_repository
        self.generate_materials = generate_materials
        self.prompt_builder = PromptBuilder()
        self.validator_class = Material
        
        logger.info(f"[DEBUG MATERIALS] ✓ Initialized with validator_class: {self.validator_class}")

    """ To do: Log the LLM usage to stu_tracker.LLM_usage for both generation types """

    def retry_event(self)->bool:
        logger.info("[DEBUG MATERIALS] === retry_event called ===")
        logger.info(f"[DEBUG MATERIALS] s3_output_key: {self.generate_materials.get('s3_output_key')}")
        update_event = self.business_repository.update_materials_status_by_input_key(('RETRY', self.organization_id, self.generate_materials.get("s3_output_key")))
        logger.info(f"[DEBUG MATERIALS] retry_event result: {update_event}")
        return update_event

    def process_materials_generation(self)->bool:
        """ Main caller, returns boolean if succeded."""
        logger.info("[DEBUG MATERIALS] ========================================")
        logger.info("[DEBUG MATERIALS] === process_materials_generation CALLED ===")
        logger.info("[DEBUG MATERIALS] ========================================")
        
        try:
            logger.info("[DEBUG MATERIALS] === STEP 1: Fetching assessment data ===")
            assessment_id = self.generate_materials.get("assessment_id")
            logger.info(f"[DEBUG MATERIALS] assessment_id from generate_materials: {assessment_id}")
            
            assessment_data = self.business_repository.get_assessment_by_id((self.organization_id, assessment_id))
            logger.info(f"[DEBUG MATERIALS] assessment_data type: {type(assessment_data)}")
            logger.info(f"[DEBUG MATERIALS] assessment_data: {assessment_data}")
            
            if assessment_data is None:
                logger.error("[ERROR MATERIALS] !!! assessment_data is None - ABORTING !!!")
                logger.error(f"[ERROR MATERIALS] organization_id: {self.organization_id}")
                logger.error(f"[ERROR MATERIALS] assessment_id: {assessment_id}")
                return False

            logger.info(f"[DEBUG MATERIALS] ✓ Assessment data retrieved successfully")
            logger.info(f"[DEBUG MATERIALS] assessment_data keys: {list(assessment_data.keys()) if isinstance(assessment_data, dict) else 'N/A'}")

            # Fetch assessment data
            logger.info("[DEBUG MATERIALS] === STEP 2: Creating PromptConfig ===")
            
            grade_val = self.generate_materials.get("grade")
            subject_title_val = assessment_data.get('subject_title')
            assessment_title_val = assessment_data.get('assessment_title')
            assessment_desc_val = assessment_data.get('assessment_description')
            subject_desc_val = assessment_data.get('subject_description')
            custom_inst_val = self.generate_materials.get("custom_instructions")
            model_type_val = os.getenv("MODEL_TYPE")
            
            logger.info(f"[DEBUG MATERIALS] Variables for PromptConfig:")
            logger.info(f"[DEBUG MATERIALS]   - grade_level: {grade_val}")
            logger.info(f"[DEBUG MATERIALS]   - subject: {subject_title_val}")
            logger.info(f"[DEBUG MATERIALS]   - assessment_title: {assessment_title_val}")
            logger.info(f"[DEBUG MATERIALS]   - assessment_description: {assessment_desc_val}")
            logger.info(f"[DEBUG MATERIALS]   - subject_description: {subject_desc_val}")
            logger.info(f"[DEBUG MATERIALS]   - custom_instructions: {custom_inst_val}")
            logger.info(f"[DEBUG MATERIALS]   - MODEL_TYPE from env: {model_type_val}")
            
            try:
                logger.info("[DEBUG MATERIALS] Calling PromptConfig constructor...")
                prompt_config = PromptConfig(
                    model=model_type_val,
                    template_name=f"Identity_materials",
                    variables={
                        "grade_level": grade_val, 
                        "subject": subject_title_val,
                        "assessment_title": assessment_title_val,
                        "assessment_description": assessment_desc_val,
                        "subject_description": subject_desc_val,
                        "custom_instructions": custom_inst_val
                    },
                    temperature=0.6,
                    top_p=0.8,
                    max_tokens=20000
                )
                logger.info(f"[DEBUG MATERIALS] ✓ PromptConfig created successfully")
                logger.info(f"[DEBUG MATERIALS] PromptConfig type: {type(prompt_config)}")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! Failed to create PromptConfig !!!")
                logger.error(f"[ERROR MATERIALS] Error type: {type(e).__name__}")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                return False

            if prompt_config is None:
                logger.error("[ERROR MATERIALS] !!! prompt_config is None after creation !!!")
                return False

            logger.info("[DEBUG MATERIALS] === STEP 3: Building prompt_data ===")
            logger.info(f"[DEBUG MATERIALS] Using prompt_builder: {type(self.prompt_builder)}")
            
            try:
                logger.info("[DEBUG MATERIALS] Calling prompt_builder.build()...")
                prompt_data = self.prompt_builder.build(prompt_config)
                logger.info(f"[DEBUG MATERIALS] ✓ prompt_data built")
                logger.info(f"[DEBUG MATERIALS] prompt_data type: {type(prompt_data)}")
                logger.info(f"[DEBUG MATERIALS] prompt_data is None: {prompt_data is None}")
                logger.info(f"[DEBUG MATERIALS] prompt_data is empty: {not prompt_data}")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! Failed to build prompt_data !!!")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                return False
            
            if not prompt_data:
                logger.error("[ERROR MATERIALS] !!! prompt_data is empty or None after build !!!")
                logger.error(f"[ERROR MATERIALS] prompt_data value: {prompt_data}")
                return False
            
            logger.info(f"[DEBUG MATERIALS] prompt_data keys: {list(prompt_data.keys()) if isinstance(prompt_data, dict) else 'N/A'}")
            logger.info(f"[DEBUG MATERIALS] prompt_data.get('model'): {prompt_data.get('model')}")
            
            logger.info("[DEBUG MATERIALS] === STEP 4: Invoking LLM model ===")
            logger.info("[DEBUG MATERIALS] About to call _invoke_llm_model()...")
            
            try:
                model_result, usage = self._invoke_llm_model(prompt_data)
                logger.info("[DEBUG MATERIALS] ✓ _invoke_llm_model() returned")
                logger.info(f"[DEBUG MATERIALS] model_result type: {type(model_result)}")
                logger.info(f"[DEBUG MATERIALS] model_result is None: {model_result is None}")
                logger.info(f"[DEBUG MATERIALS] usage: {usage}")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! _invoke_llm_model() raised exception !!!")
                logger.error(f"[ERROR MATERIALS] Error type: {type(e).__name__}")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                raise
        
            logger.info("[DEBUG MATERIALS] === STEP 5: Saving results ===")
            logger.info("[DEBUG MATERIALS] About to call _save_generation_results()...")
            
            try:
                success = self._save_generation_results(model_result, usage)
                logger.info(f"[DEBUG MATERIALS] ✓ _save_generation_results() returned: {success}")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! _save_generation_results() raised exception !!!")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                return False
            
            logger.info("[DEBUG MATERIALS] ========================================")
            logger.info(f"[DEBUG MATERIALS] === process_materials_generation COMPLETED: {success} ===")
            logger.info("[DEBUG MATERIALS] ========================================")
            
            return success
            
        except Exception as e:
            logger.error("[ERROR MATERIALS] ========================================")
            logger.error("[ERROR MATERIALS] !!! UNCAUGHT EXCEPTION in process_materials_generation !!!")
            logger.error("[ERROR MATERIALS] ========================================")
            logger.error(f"[ERROR MATERIALS] Error type: {type(e).__name__}")
            logger.error(f"[ERROR MATERIALS] Failed in process_materials_generation: {e}", exc_info=True)
            return False
        
                
    def _invoke_llm_model(self, prompt_data: Dict[str, Any]) -> tuple:
        """Invoke appropriate LLM model based on configuration."""
        logger.info("[DEBUG MATERIALS] ========================================")
        logger.info("[DEBUG MATERIALS] === _invoke_llm_model CALLED ===")
        logger.info("[DEBUG MATERIALS] ========================================")
        
        try:
            logger.info(f"[DEBUG MATERIALS] prompt_data type: {type(prompt_data)}")
            logger.info(f"[DEBUG MATERIALS] prompt_data keys: {list(prompt_data.keys()) if isinstance(prompt_data, dict) else 'N/A'}")
            
            model_type = prompt_data.get('model', 'GOOGLE').upper()
            logger.info(f"[DEBUG MATERIALS] model_type extracted: '{model_type}'")
            logger.info(f"[DEBUG MATERIALS] model_type (raw): '{prompt_data.get('model')}'")
            
            logger.info("[DEBUG MATERIALS] === Entering model type match/case ===")
            
            match model_type:
                case "GOOGLE":
                    logger.info("[DEBUG MATERIALS] *** MATCHED: GOOGLE ***")
                    logger.info("[DEBUG MATERIALS] Creating GeminiModel instance...")
                    llm_model = GeminiModel(self.validator_class, prompt_data)
                    logger.info(f"[DEBUG MATERIALS] ✓ GeminiModel created: {type(llm_model)}")
                    
                case "AMAZON":
                    logger.info("[DEBUG MATERIALS] *** MATCHED: AMAZON ***")
                    logger.info(f"[DEBUG MATERIALS] Creating AmazonModel instance...")
                    logger.info(f"[DEBUG MATERIALS]   - validator_class: {self.validator_class}")
                    logger.info(f"[DEBUG MATERIALS]   - prompt_data type: {type(prompt_data)}")
                    logger.info(f"[DEBUG MATERIALS]   - prompt_data keys: {list(prompt_data.keys())}")
                    
                    llm_model = AmazonModel(self.validator_class, prompt_data)
                    logger.info(f"[DEBUG MATERIALS] ✓ AmazonModel created: {type(llm_model)}")
                    
                case _:
                    logger.error(f"[ERROR MATERIALS] !!! UNSUPPORTED MODEL TYPE: {model_type} !!!")
                    logger.error(f"[ERROR MATERIALS] Expected 'GOOGLE' or 'AMAZON', got '{model_type}'")
                    logger.error(f"[ERROR MATERIALS] prompt_data.get('model'): {prompt_data.get('model')}")
                    return None, None

            logger.info("[DEBUG MATERIALS] === Invoking model ===")
            logger.info(f"[DEBUG MATERIALS] Calling {model_type} llm_model._invoke_model()...")
            
            try:
                success = llm_model._invoke_model()
                logger.info(f"[DEBUG MATERIALS] ✓ {model_type} model invoked successfully")
                logger.info(f"[DEBUG MATERIALS] Success result type: {type(success)}")
                logger.info(f"[DEBUG MATERIALS] Success result: {success}")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! {model_type} model._invoke_model() raised exception !!!")
                logger.error(f"[ERROR MATERIALS] Error type: {type(e).__name__}")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                raise

            logger.info("[DEBUG MATERIALS] === Getting usage metrics ===")
            logger.info(f"[DEBUG MATERIALS] Calling {model_type} llm_model.get_usage()...")
            
            try:
                usage = llm_model.get_usage()
                logger.info(f"[DEBUG MATERIALS] ✓ Usage retrieved")
                logger.info(f"[DEBUG MATERIALS] Usage type: {type(usage)}")
                logger.info(f"[DEBUG MATERIALS] Usage: {usage}")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! Failed to get usage from {model_type} model !!!")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                return None, None
            
            if not usage:
                logger.error(f"[ERROR MATERIALS] !!! No usage metrics returned from {model_type} model !!!")
                logger.error(f"[ERROR MATERIALS] usage value: {usage}")
                return None, None

            logger.info(f"[DEBUG MATERIALS {model_type}] Final usage: {usage}")
            logger.info("[DEBUG MATERIALS] ========================================")
            logger.info(f"[DEBUG MATERIALS] === _invoke_llm_model COMPLETED ===")
            logger.info("[DEBUG MATERIALS] ========================================")
            
            return success, usage

        except Exception as e:
            logger.error("[ERROR MATERIALS] ========================================")
            logger.error("[ERROR MATERIALS] !!! EXCEPTION in _invoke_llm_model !!!")
            logger.error("[ERROR MATERIALS] ========================================")
            logger.error(f"[ERROR MATERIALS] Error type: {type(e).__name__}")
            logger.error(f"[ERROR MATERIALS] Failed in _invoke_llm_model: {e}", exc_info=True)
            raise
    
    def _save_generation_results(self, model_result, usage) -> bool:
        """Save generation results to database."""
        logger.info("[DEBUG MATERIALS] ========================================")
        logger.info("[DEBUG MATERIALS] === _save_generation_results CALLED ===")
        logger.info("[DEBUG MATERIALS] ========================================")
        
        try:
            logger.info(f"[DEBUG MATERIALS] model_result type: {type(model_result)}")
            logger.info(f"[DEBUG MATERIALS] model_result: {model_result}")
            logger.info(f"[DEBUG MATERIALS] usage type: {type(usage)}")
            logger.info(f"[DEBUG MATERIALS] usage: {usage}")
            
            s3_key = self.generate_materials.get("s3_output_key")
            logger.info(f"[DEBUG MATERIALS] s3_output_key: {s3_key}")
            
            logger.info("[DEBUG MATERIALS] === Updating materials JSON ===")
            logger.info(f"[DEBUG MATERIALS] Calling update_gmaterials_json_by_input_key()...")
            
            try:
                self.business_repository.update_gmaterials_json_by_input_key(
                    (Json(model_result), self.organization_id, s3_key)
                )
                logger.info("[DEBUG MATERIALS] ✓ Materials JSON updated")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! Failed to update materials JSON !!!")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                raise
            
            logger.info("[DEBUG MATERIALS] === Updating usage metrics ===")
            logger.info(f"[DEBUG MATERIALS] Calling update_gmaterials_usage_by_input_key()...")
            
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            logger.info(f"[DEBUG MATERIALS] input_tokens: {input_tokens}")
            logger.info(f"[DEBUG MATERIALS] output_tokens: {output_tokens}")
            
            try:
                self.business_repository.update_gmaterials_usage_by_input_key(
                    (input_tokens, output_tokens, self.organization_id, s3_key)
                )
                logger.info("[DEBUG MATERIALS] ✓ Usage metrics updated")
            except Exception as e:
                logger.error(f"[ERROR MATERIALS] !!! Failed to update usage metrics !!!")
                logger.error(f"[ERROR MATERIALS] Error: {e}", exc_info=True)
                raise
            
            logger.info("[DEBUG MATERIALS] ========================================")
            logger.info("[DEBUG MATERIALS] === Successfully saved generation results ===")
            logger.info("[DEBUG MATERIALS] ========================================")
            return True
            
        except Exception as e:
            logger.error("[ERROR MATERIALS] ========================================")
            logger.error("[ERROR MATERIALS] !!! EXCEPTION in _save_generation_results !!!")
            logger.error("[ERROR MATERIALS] ========================================")
            logger.error(f"[ERROR MATERIALS] Failed to save generation results: {e}", exc_info=True)
            return False