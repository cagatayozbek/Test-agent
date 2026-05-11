"""LLM client supporting both Gemini and OpenAI-compatible APIs (NVIDIA, etc.)."""

import json
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class NvidiaClient:
    """Client for NVIDIA Build (OpenAI-compatible API)."""

    def __init__(self, model_id: str, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1", max_retries: int = 3):
        from openai import OpenAI
        # Tight timeout so a hung request doesn't stall the whole pilot.
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=60.0)
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
        return self._call_with_retry(
            messages=[
                {"role": "system", "content": json_system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_output_tokens,
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
                    timeout=60.0,  # per-call timeout regardless of TCP state
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
                wait = 15 * (attempt + 1)
                print(f"  [retry {attempt+1}/{self._max_retries}] waiting {wait}s...")
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
                wait = 15 * (attempt + 1)
                print(f"  [retry {attempt+1}/{self._max_retries}] {status} - waiting {wait}s...")
                time.sleep(wait)
        raise RuntimeError("Retry loop exited unexpectedly")


_CLAUDE_LIMIT_SIGNALS = (
    "usage limit", "rate limit", "rate_limit", "5-hour limit", "5 hour limit",
    "weekly limit", "limit_exceeded", "limit exceeded", "too many requests",
    "429", "quota", "you've reached", "you have reached", "claude usage limit",
    "max requests", "approaching usage limit",
)


def _claude_is_limit_error(stdout: str, stderr: str, returncode: int) -> bool:
    text_l = ((stdout or "") + " " + (stderr or "")).lower()
    return any(sig in text_l for sig in _CLAUDE_LIMIT_SIGNALS)


def _claude_sleep_through_limit(attempt: int, max_attempts: int = 6,
                                 wait_minutes: int = 60) -> None:
    """Sleep wait_minutes (default 60) up to max_attempts times, with progress
    prints — meant to outwait Claude Max's 5-hour rolling window."""
    import time as _time
    print(f"  !! claude limit detected — sleeping {wait_minutes}min "
          f"(limit-retry {attempt + 1}/{max_attempts})", flush=True)
    _time.sleep(wait_minutes * 60)


class ClaudeCodeClient:
    """Client that calls Claude Code CLI (claude -p) for Max subscription users."""

    def __init__(self, model_id: str = "sonnet", **kwargs):
        self._model = model_id  # sonnet, opus, haiku

    def generate(self, *, system: str, user: str, **kwargs) -> LLMResponse:
        import subprocess, json as _json, time as _time
        prompt = f"{system}\n\n{user}"
        cmd = ["claude", "-p", "--model", self._model, "--output-format", "json"]
        result = None
        for limit_attempt in range(6):
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=900,
            )
            if _claude_is_limit_error(result.stdout, result.stderr, result.returncode):
                _claude_sleep_through_limit(limit_attempt)
                continue
            break
        # Inter-call cooldown to avoid Anthropic-side queueing under Max sub
        _time.sleep(3)
        raw = (result.stdout or "").strip()
        text, p_tok, c_tok = raw, 0, 0
        try:
            wrapper = _json.loads(raw)
            if isinstance(wrapper, dict):
                text = wrapper.get("result", raw)
                usage = wrapper.get("usage") or {}
                p_tok = (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                )
                c_tok = usage.get("output_tokens", 0)
        except _json.JSONDecodeError:
            pass
        return LLMResponse(text=text, prompt_tokens=p_tok, completion_tokens=c_tok, total_tokens=p_tok + c_tok)

    def generate_json(self, *, system: str, user: str, **kwargs) -> LLMResponse:
        import subprocess, json as _json, re
        json_system = system + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences, no explanation."
        prompt = f"{json_system}\n\n{user}"
        result = subprocess.run(
            ["claude", "-p", "--model", self._model, "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
        )
        raw = result.stdout.strip()
        # --output-format json wraps response in {"result":"..."}
        try:
            wrapper = _json.loads(raw)
            text = wrapper.get("result", raw) if isinstance(wrapper, dict) else raw
        except _json.JSONDecodeError:
            text = raw
        # Extract JSON object from markdown or mixed text
        text = text.strip()
        # Try as-is first
        try:
            _json.loads(text)
            return LLMResponse(text=text, prompt_tokens=0, completion_tokens=0, total_tokens=0)
        except _json.JSONDecodeError:
            pass
        # Try extracting from markdown fences
        m = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        else:
            # Try finding first { ... last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end + 1]
        return LLMResponse(text=text, prompt_tokens=0, completion_tokens=0, total_tokens=0)


def create_client(model_id: str, api_key: str, provider: str = "auto"):
    """Factory: create the right client based on provider or api_key format."""
    if provider == "auto":
        if api_key == "claude-code":
            provider = "claude"
        elif api_key.startswith("nvapi-"):
            provider = "nvidia"
        elif api_key.startswith("AIzaSy") or api_key.startswith("AQ."):
            provider = "gemini"
        else:
            provider = "nvidia"

    if provider == "claude":
        return ClaudeCodeClient(model_id=model_id)
    elif provider == "nvidia":
        return NvidiaClient(model_id=model_id, api_key=api_key)
    else:
        return GeminiClient(model_id=model_id, api_key=api_key)
