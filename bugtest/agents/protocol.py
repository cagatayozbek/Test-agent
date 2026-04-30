"""Minimal agent protocol. No graph, no edges, no framework."""

from abc import ABC, abstractmethod

from bugtest.llm import GeminiClient


class Agent(ABC):
    """Base agent interface. Each agent wraps a single LLM call."""

    def __init__(self, llm: GeminiClient, system_prompt: str):
        self._llm = llm
        self._system_prompt = system_prompt

    @property
    def name(self) -> str:
        return self.__class__.__name__.lower()
