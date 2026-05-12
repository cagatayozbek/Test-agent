"""Analyzer agent: reads buggy code, produces structured CodeAnalysis."""

import json
import re

from bugtest.agents.protocol import Agent
from bugtest.llm import LLMResponse
from bugtest.models import CodeAnalysis

# v2.0: shared with the deep-mode subagent prompt for cross-mode consistency.
from bugtest.deep.prompts import ANALYZER_SYSTEM_PROMPT as SYSTEM_PROMPT  # noqa: E402, F401


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
