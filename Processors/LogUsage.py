import os
from pydantic import BaseModel
from typing import Optional

""" Log usage of LLM models """
class LogUsage:

    def __init__(self, organization_id: int,  business_repository: Optional[any], usage_metrics: Optional[dict]):
        self.organization_id = organization_id
        self.usage_metrics = usage_metrics
        self.business_repository = business_repository

    def __del__(self):
        pass

    def _log_llm_usage(self) ->Optional[bool]:
        try:
            if not self.usage_metrics:
                return False
        except Exception as e:
            return False

    