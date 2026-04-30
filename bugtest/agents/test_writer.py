"""TestWriter agent: generates pytest test code targeting a specific bug."""

import re

from bugtest.agents.protocol import Agent
from bugtest.llm import GeminiClient, LLMResponse

SYSTEM_PROMPT = """\
You are a test engineer. Write a pytest test that REVEALS a specific bug.

REQUIREMENTS:
1. The test MUST FAIL on the buggy code (expose the bug)
2. The test MUST PASS on the fixed code (confirm the fix works)
3. Import from the local file: `from source import <symbols>`
4. Use exact boundary values / edge cases that trigger the bug
5. Include a clear assertion with a descriptive message
6. Return ONLY the Python test code — no explanation, no markdown fences

GUIDELINES:
- Focus on the SPECIFIC bug, not general correctness
- Use the exact values that trigger the bug condition
- One focused test function is better than many unfocused ones
- Name the test descriptively: test_<what_it_checks>"""

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
