"""Gemini LLM client wrapper with retry logic and JSON mode support.

This module provides a wrapper around Google's Generative AI SDK,
adding features like exponential backoff retry, token usage tracking,
and structured JSON output mode.

Classes:
    LLMResponse: Container for LLM response text and token usage metrics
    GeminiClient: Main client class for interacting with Gemini models

Example:
    >>> from llm_client import GeminiClient
    >>> client = GeminiClient(model_id="gemini-2.0-flash", api_key="your-key")
    >>> response = client.generate(system="You are helpful.", user="Hello")
    >>> print(response.text)
"""

from dataclasses import dataclass
from typing import Any
import time

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions


@dataclass
class LLMResponse:
    """Container for LLM response with text and token usage metrics.
    
    Attributes:
        text: Generated text content from the model
        prompt_tokens: Number of tokens in the input prompt
        completion_tokens: Number of tokens in the generated response
        total_tokens: Sum of prompt and completion tokens
    
    Example:
        >>> response = client.generate(system="...", user="...")
        >>> print(f"Response: {response.text}")
        >>> print(f"Used {response.total_tokens} tokens")
    """
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class GeminiClient:
    """Client wrapper for Google Gemini models with retry and JSON support.
    
    Provides a simplified interface for calling Gemini models with:
    - Automatic retry with exponential backoff on timeouts/rate limits
    - Token usage tracking from response metadata
    - JSON mode for structured output with optional schema validation
    
    Attributes:
        model_id: Identifier of the Gemini model being used
        max_retries: Maximum retry attempts for failed calls
        model: Configured GenerativeModel instance
    
    Example:
        >>> client = GeminiClient("gemini-2.0-flash", api_key="...")
        >>> 
        >>> # Simple generation
        >>> response = client.generate(system="Be brief.", user="What is 2+2?")
        >>> 
        >>> # JSON mode with schema
        >>> from schemas import SemanticHypothesis
        >>> response = client.generate_json(
        ...     system="Analyze the code.",
        ...     user="...",
        ...     response_schema=SemanticHypothesis
        ... )
    """
    
    def __init__(self, model_id: str, api_key: str, max_retries: int = 3):
        """Initialize the Gemini client.
        
        Args:
            model_id: Gemini model identifier (e.g., "gemini-2.0-flash")
            api_key: Google API key for authentication
            max_retries: Maximum retry attempts on timeout/rate limit (default: 3)
        """
        self.model_id = model_id
        self.max_retries = max_retries
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_id)
        # JSON model will be created per-call with specific schema
        self._base_model_id = model_id

    def _call_with_retry(self, func, *args, **kwargs) -> LLMResponse:
        """Execute a function with exponential backoff retry on failures.
        
        Handles DeadlineExceeded (timeout) and ResourceExhausted (rate limit)
        errors with increasing wait times between retries.
        
        Args:
            func: Callable to execute (typically generate_content)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            LLMResponse: Parsed response with text and token metrics
        
        Raises:
            DeadlineExceeded: If all retries fail on timeout
            ResourceExhausted: If all retries fail on rate limit
        """
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
