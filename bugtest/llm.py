"""LLM client supporting Gemini, Claude Code CLI, and OpenAI-compatible APIs (NVIDIA, Together)."""

import json
import random
import time
from dataclasses import dataclass
from typing import Optional


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with jitter to reduce thundering herd under concurrency."""
    base = min(60.0, 5.0 * (2 ** attempt))  # 5, 10, 20, 40, 60, 60, ...
    jitter = random.uniform(0, base * 0.5)
    return base + jitter


def _extract_json_object(text: str) -> str:
    """Strip markdown fences and trailing prose so small LLMs' replies parse.

    Smaller chat models often ignore "respond with JSON only" and wrap the
    object in ```json fences or add explanatory text. Pull out the first
    `{...}` substring whose braces balance.
    """
    import re
    text = text.strip()
    # Try as-is first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    # Strip ```json ... ``` or ``` ... ``` fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            text = candidate  # fall through to brace scan
    # Find first '{' and matching close
    start = text.find("{")
    if start < 0:
        return text
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    return candidate  # let caller surface the error
    return text


@dataclass(frozen=True)
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAICompatibleClient:
    """Client for any OpenAI-compatible chat.completions endpoint.

    Tested with NVIDIA Build (https://integrate.api.nvidia.com/v1) and
    Together.ai (https://api.together.xyz/v1). Same protocol on both.
    """

    def __init__(self, model_id: str, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1", max_retries: int = 5):
        from openai import OpenAI
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model_id = model_id
        self._max_retries = max_retries

    def generate(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate text with system/user separation."""
        return self._call_with_retry(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_output_tokens,
        )

    def generate_json(
        self,
        *,
        system: str,
        user: str,
        response_schema=None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate JSON output. Instructs model via prompt to return JSON."""
        json_system = system + "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation."
        resp = self._call_with_retry(
            messages=[
                {"role": "system", "content": json_system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_output_tokens,
        )
        # Smaller chat models (e.g. llama-3.1-8b) often ignore "JSON only" and
        # wrap output in markdown fences or trail prose. Extract the JSON object
        # so downstream pydantic validation succeeds.
        return LLMResponse(
            text=_extract_json_object(resp.text),
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            total_tokens=resp.total_tokens,
        )

    def _call_with_retry(self, messages, temperature, max_tokens) -> LLMResponse:
        """Call with exponential backoff on rate limits."""
        for attempt in range(self._max_retries):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                usage = resp.usage
                return LLMResponse(
                    text=resp.choices[0].message.content or "",
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                )
            except Exception as e:
                err_str = str(e)
                retryable = any(k in err_str.lower() for k in ["429", "rate", "limit", "500", "503", "overloaded"])
                if not retryable or attempt == self._max_retries - 1:
                    raise
                wait = _backoff_seconds(attempt)
                print(f"  [retry {attempt+1}/{self._max_retries}] waiting {wait:.1f}s...")
                time.sleep(wait)
        raise RuntimeError("Retry loop exited unexpectedly")


class GeminiClient:
    """Client for Google Gemini API."""

    def __init__(self, model_id: str, api_key: str, max_retries: int = 5):
        from google import genai
        from google.genai import types
        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=api_key)
        self._model_id = model_id
        self._max_retries = max_retries

    def generate(self, *, system: str, user: str, temperature: float = 1.0, max_output_tokens: int = 8192) -> LLMResponse:
        config = self._types.GenerateContentConfig(
            system_instruction=system, temperature=temperature, max_output_tokens=max_output_tokens,
        )
        return self._call_with_retry(model=self._model_id, contents=user, config=config)

    def generate_json(self, *, system: str, user: str, response_schema=None, temperature: float = 1.0, max_output_tokens: int = 8192) -> LLMResponse:
        config = self._types.GenerateContentConfig(
            system_instruction=system, temperature=temperature, max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
        )
        return self._call_with_retry(model=self._model_id, contents=user, config=config)

    def _call_with_retry(self, **kwargs) -> LLMResponse:
        from google.genai import errors as genai_errors
        for attempt in range(self._max_retries):
            try:
                response = self._client.models.generate_content(**kwargs)
                usage = response.usage_metadata
                return LLMResponse(
                    text=response.text,
                    prompt_tokens=getattr(usage, "prompt_token_count", 0),
                    completion_tokens=getattr(usage, "candidates_token_count", 0),
                    total_tokens=getattr(usage, "total_token_count", 0),
                )
            except (genai_errors.ServerError, genai_errors.ClientError) as e:
                status = getattr(e, "status_code", 500)
                retryable = status in (429, 500, 503)
                if not retryable or attempt == self._max_retries - 1:
                    raise
                wait = _backoff_seconds(attempt)
                print(f"  [retry {attempt+1}/{self._max_retries}] {status} - waiting {wait:.1f}s...")
                time.sleep(wait)
        raise RuntimeError("Retry loop exited unexpectedly")


class ClaudeCodeClient:
    """Client that calls Claude Code CLI (claude -p) for Max subscription users."""

    def __init__(self, model_id: str = "sonnet", **kwargs):
        self._model = model_id  # sonnet, opus, haiku

    def generate(self, *, system: str, user: str, **kwargs) -> LLMResponse:
        import subprocess
        prompt = f"{system}\n\n{user}"
        result = subprocess.run(
            ["claude", "-p", "--model", self._model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
        text = result.stdout.strip()
        return LLMResponse(text=text, prompt_tokens=0, completion_tokens=0, total_tokens=0)

    def generate_json(self, *, system: str, user: str, **kwargs) -> LLMResponse:
        import subprocess
        json_system = system + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences, no explanation."
        prompt = f"{json_system}\n\n{user}"
        result = subprocess.run(
            ["claude", "-p", "--model", self._model, "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
        raw = result.stdout.strip()
        # --output-format json wraps response in {"result": "..."}
        try:
            wrapper = json.loads(raw)
            text = wrapper.get("result", raw) if isinstance(wrapper, dict) else raw
        except json.JSONDecodeError:
            text = raw
        return LLMResponse(
            text=_extract_json_object(text),
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
TOGETHER_BASE_URL = "https://api.together.xyz/v1"

# Backward-compat alias: existing imports (`pipeline.py`, `protocol.py`,
# scripts) still work, but new code should prefer OpenAICompatibleClient.
NvidiaClient = OpenAICompatibleClient


def create_client(
    model_id: str,
    api_key: str,
    base_url: Optional[str] = None,
    provider: str = "auto",
):
    """Factory: create the right client based on provider, api_key, or base_url.

    Resolution order:
      1. If `base_url` is given → OpenAI-compatible (NVIDIA / Together / any).
      2. If `provider != "auto"` → use that provider directly.
      3. Otherwise infer from api_key prefix.
    """
    if base_url is not None:
        return OpenAICompatibleClient(
            model_id=model_id, api_key=api_key, base_url=base_url
        )

    if provider == "auto":
        if api_key == "claude-code":
            provider = "claude"
        elif api_key.startswith("nvapi-"):
            provider = "nvidia"
        elif api_key.startswith("tgp_v1_") or api_key.startswith("tgp_"):
            provider = "together"
        elif api_key.startswith("AIzaSy") or api_key.startswith("AQ."):
            provider = "gemini"
        else:
            provider = "nvidia"

    if provider == "claude":
        return ClaudeCodeClient(model_id=model_id)
    elif provider == "nvidia":
        return OpenAICompatibleClient(
            model_id=model_id, api_key=api_key, base_url=NVIDIA_BASE_URL
        )
    elif provider == "together":
        return OpenAICompatibleClient(
            model_id=model_id, api_key=api_key, base_url=TOGETHER_BASE_URL
        )
    else:
        return GeminiClient(model_id=model_id, api_key=api_key)
