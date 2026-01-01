from dataclasses import dataclass
from typing import Any
import time

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions


@dataclass
class LLMResponse:
    """Response from LLM containing text and token usage."""
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class GeminiClient:
    def __init__(self, model_id: str, api_key: str, max_retries: int = 3):
        self.model_id = model_id
        self.max_retries = max_retries
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_id)
        # JSON model will be created per-call with specific schema
        self._base_model_id = model_id

    def _call_with_retry(self, func, *args, **kwargs) -> LLMResponse:
        """Call a function with exponential backoff retry on timeout."""
        for attempt in range(self.max_retries):
            try:
                response = func(*args, **kwargs)
                # Extract token usage from response metadata
                usage = getattr(response, 'usage_metadata', None)
                if usage:
                    prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                    completion_tokens = getattr(usage, 'candidates_token_count', 0)
                    total_tokens = getattr(usage, 'total_token_count', 0)
                else:
                    prompt_tokens = completion_tokens = total_tokens = 0
                
                return LLMResponse(
                    text=response.text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
            except google_exceptions.DeadlineExceeded as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 1, 2, 4 seconds
                    print(f"⏳ API timeout, retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    raise e
            except google_exceptions.ResourceExhausted as e:
                if attempt < self.max_retries - 1:
                    wait_time = 5 * (attempt + 1)  # 5, 10, 15 seconds for rate limit
                    print(f"⏳ Rate limited, waiting {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    raise e
        return LLMResponse(text="", prompt_tokens=0, completion_tokens=0, total_tokens=0)

    def complete(self, messages: list[dict[str, Any]]) -> LLMResponse:
        text = "\n".join(item.get("content", "") for item in messages)
        return self._call_with_retry(self.model.generate_content, text)

    def generate(self, system: str, user: str) -> LLMResponse:
        """Simple system+user prompt call."""
        prompt = f"{system}\n\nUser: {user}"
        return self._call_with_retry(self.model.generate_content, prompt)

    def generate_json(self, system: str, user: str, response_schema: type | dict | None = None) -> LLMResponse:
        """Generate structured JSON output using Gemini's JSON mode.
        
        Uses response_mime_type='application/json' and optionally a response_schema
        to force valid, schema-conformant JSON output.
        
        Args:
            system: System prompt
            user: User prompt  
            response_schema: Optional Pydantic class or dict schema for validation.
                           If a Pydantic class is provided, its JSON schema will be extracted.
                           Gemini will enforce the output matches this schema.
        
        Returns:
            LLMResponse: Response with valid JSON string and token usage
        """
        generation_config: dict = {"response_mime_type": "application/json"}
        
        if response_schema is not None:
            # Check if it's a Pydantic model class
            if hasattr(response_schema, "model_json_schema"):
                # Convert Pydantic model to JSON schema dict
                generation_config["response_schema"] = response_schema.model_json_schema()
            else:
                generation_config["response_schema"] = response_schema
        
        json_model = genai.GenerativeModel(
            self._base_model_id,
            generation_config=generation_config
        )
        prompt = f"{system}\n\nUser: {user}"
        return self._call_with_retry(json_model.generate_content, prompt)
