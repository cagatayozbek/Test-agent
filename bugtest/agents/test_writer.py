"""TestWriter agent: generates pytest test code targeting a specific bug."""

import re

from bugtest.agents.protocol import Agent
from bugtest.llm import GeminiClient, LLMResponse

# v2.0: the TestWriter prompt is sourced from bugtest.deep.prompts so the
# non-deep modes (baseline / agentic / adaptive) share the same failure-mode
# taxonomy (TEST_PASSES_ON_BUG, OVERFIT_TO_BUG) as the deep mode's CRITIC.
from bugtest.deep.prompts import TEST_WRITER_SYSTEM_PROMPT as SYSTEM_PROMPT  # noqa: E402, F401

_RETRY_TEMPLATE = """
=== PREVIOUS ATTEMPTS (fix these issues) ===
{retry_context}
=== END PREVIOUS ATTEMPTS ===

Write a NEW test that avoids the problems listed above."""


class TestWriter(Agent):
    """Generates pytest test code targeting a specific bug."""

    def __init__(self, llm: GeminiClient):
        super().__init__(llm, SYSTEM_PROMPT)

    def run(self, user_message: str) -> tuple[str, LLMResponse]:
        response = self._llm.generate(
            system=self._system_prompt,
            user=user_message,
        )
        return _extract_code(response.text), response

    def run_with_retry_context(
        self, user_message: str, retry_context: str
    ) -> tuple[str, LLMResponse]:
        """Generate test with feedback from previous failed attempts.

        Retry context is appended to user message, NOT injected into
        system prompt — system prompt stays identical between modes.
        """
        augmented = user_message + _RETRY_TEMPLATE.format(retry_context=retry_context)
        response = self._llm.generate(
            system=self._system_prompt,
            user=augmented,
        )
        return _extract_code(response.text), response


def _extract_code(text: str) -> str:
    """Strip markdown code fences if present."""
    text = text.strip()
    # Try to extract from ```python ... ``` or ``` ... ```
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
