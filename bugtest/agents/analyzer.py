"""Analyzer agent: reads buggy code, produces structured CodeAnalysis."""

import json
import re

from bugtest.agents.protocol import Agent
from bugtest.llm import LLMResponse
from bugtest.models import CodeAnalysis

SYSTEM_PROMPT = """\
You are a code analysis expert. You will receive source code that contains a known bug.

Your job:
1. Identify the most likely bug in the code
2. Determine exactly what input/condition triggers it
3. Explain expected vs actual behavior
4. Suggest a concrete test strategy to reveal the bug

Respond with ONLY valid JSON (no markdown fences, no explanation) matching this schema:
{
  "bug_hypothesis": "your theory about the bug",
  "bug_location": "function name, line number",
  "trigger_condition": "what input triggers the bug",
  "expected_vs_actual": "what SHOULD vs DOES happen",
  "suggested_test_strategy": "how to test for this bug",
  "confidence": "low" | "medium" | "high"
}

Be concrete. Reference specific functions, values, and operators."""


class Analyzer(Agent):
    """Analyzes source code to produce structured bug hypothesis."""

    def __init__(self, llm):
        super().__init__(llm, SYSTEM_PROMPT)

    def run(self, user_message: str) -> tuple[CodeAnalysis, LLMResponse]:
        response = self._llm.generate_json(
            system=self._system_prompt,
            user=user_message,
            response_schema=CodeAnalysis,
        )
        # Strip markdown fences if present
        text = response.text.strip()
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

        analysis = CodeAnalysis.model_validate_json(text)
        return analysis, response
