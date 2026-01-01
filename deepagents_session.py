import json
import os
from dataclasses import dataclass
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_google_genai import ChatGoogleGenerativeAI

from emitter import emit_log_entry
from instrumented_tools import InstrumentedTools
from runner import build_log_entry
from schemas import EvaluationResult, Summary, SemanticHypothesis
from graph_loader import AgentGraph
from llm_client import GeminiClient


@dataclass
class RunResult:
    analysis_text: str
    critic_text: str
    executor_tool_name: str
    executor_result: str


class DeepAgentsSession:
    def __init__(
        self,
        graph: AgentGraph,
        mode: str,
        prompts: dict[str, str],
        tools: InstrumentedTools,
        log_path: Path,
        llm: GeminiClient,
    ) -> None:
        self.graph = graph
        self.mode = mode
        self.prompts = prompts
        self.tools = tools
        self.log_path = log_path
        self.llm = llm
        self.tool_map = {
            "run_tests": self.tools.run_tests,
            "read_file": self.tools.read_file,
            "read_file_window": self.tools.read_file_window,
            "list_files": self.tools.list_files,
            "log_event": self.tools.log_event_wrapped,
        }

    def run(self) -> RunResult:
        mode_def = self.graph.modes[self.mode]
        analysis_text = ""
        critic_text = ""
        executor_reply = ""
        model = ChatGoogleGenerativeAI(model=self.llm.model_id, google_api_key=os.environ["GOOGLE_API_KEY"])
        backend = FilesystemBackend(root_dir=str(self.log_path.parent.parent), virtual_mode=True)

        for agent_name in mode_def.agents:
            prompt = self.prompts[agent_name]
            emit_log_entry(self.log_path, build_log_entry(agent=agent_name, role="system", content=prompt))
            # Direct model call to avoid DeepAgents graph loops
            response = model.invoke([
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Proceed."},
            ])
            reply = response.content if hasattr(response, "content") else str(response)
            emit_log_entry(self.log_path, build_log_entry(agent=agent_name, role="assistant", content=reply))
            if agent_name == "analysis":
                analysis_text = reply
            if agent_name == "critic":
                critic_text = reply
            if agent_name == "executor":
                executor_reply = reply

        sanitized = executor_reply.replace("```", "").strip()
        payload = json.loads(sanitized)
        tool_name = payload["tool"]
        args = payload.get("args", {})
        tool_fn = self.tool_map[tool_name]
        result = tool_fn(**args)
        emit_log_entry(
            self.log_path,
            build_log_entry(agent="executor", role="assistant", content=str(result), tool_name=tool_name),
        )

        return RunResult(
            analysis_text=analysis_text,
            critic_text=critic_text,
            executor_tool_name=tool_name,
            executor_result=str(result),
        )


class SummaryBuilder:
    def __init__(self, model_id: str, tool_call_count: int, hypothesis_text: str, evaluation_text: str) -> None:
        self.model_id = model_id
        self.tool_call_count = tool_call_count
        self.hypothesis_text = hypothesis_text
        self.evaluation_text = evaluation_text

    def build(self, timestamp: str) -> Summary:
        hypothesis = SemanticHypothesis(
            hypothesis=self.hypothesis_text,
            confidence_level="LOW",
            assumptions=[],
            evidence=[],
            what_might_be_missing="",
            next_question="",
        )
        evaluation = EvaluationResult(
            behavior="reasonable",
            failure_type="",
            commentary=self.evaluation_text,
        )
        return Summary(
            hypothesis=hypothesis,
            evaluation=evaluation,
            model_id=self.model_id,
            timestamp=timestamp,
            tool_call_count=self.tool_call_count,
        )
