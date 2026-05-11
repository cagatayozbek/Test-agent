"""Tiny settings shim used by the ported deep-test orchestrator."""

import os
from typing import Optional


class Settings:
    def __init__(self):
        self.default_model_name: str = os.getenv("DEEPTEST_DEFAULT_MODEL", "nvidia:openai/gpt-oss-120b")
        self.max_steps: int = int(os.getenv("DEEPTEST_MAX_STEPS", "8"))
        self.agent_timeout_seconds: int = int(os.getenv("DEEPTEST_AGENT_TIMEOUT_SECONDS", "180"))
        self.model_request_timeout_seconds: int = int(os.getenv("DEEPTEST_MODEL_REQUEST_TIMEOUT_SECONDS", "60"))
        self.model_retries: int = int(os.getenv("DEEPTEST_MODEL_RETRIES", "2"))
        self.debug: bool = os.getenv("DEEPTEST_DEBUG", "False").lower() in ("true", "1", "yes")


settings = Settings()
