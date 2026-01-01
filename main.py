import argparse
import os
from pathlib import Path

from config import load_config
from graph_loader import load_agent_graph
from prompt_loader import load_prompts
from run_paths import build_run_paths
from task_loader import load_task_context
from instrumented_tools import InstrumentedTools, ToolCounter
from custom_session import CustomSession, SummaryBuilder
from runner import write_summary, iso8601_utc_timestamp
from emitter import emit_log_entry
from runner import build_log_entry
from llm_client import GeminiClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", required=True, choices=["baseline", "agentic"])
    args = parser.parse_args()

    base = Path(__file__).parent
    config = load_config(base / "config.yaml")
    graph = load_agent_graph(base / "agents" / "agent_graph.yaml")
    prompts = load_prompts(base / "prompts")
    paths = build_run_paths(base, task=args.task, run_id=args.run_id)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.tool_outputs.mkdir(parents=True, exist_ok=True)

    # Load task context if available
    task_context = load_task_context(base, args.task)

    counter = ToolCounter()
    tools = InstrumentedTools(counter)
    api_key = os.environ["GOOGLE_API_KEY"]
    llm = GeminiClient(model_id=config.model_id, api_key=api_key)
    session = CustomSession(
        graph=graph,
        mode=args.mode,
        prompts=prompts,
        tools=tools,
        log_path=paths.raw_logs,
        llm=llm,
        task_context=task_context,
    )
    run_result = session.run()

    timestamp = iso8601_utc_timestamp()
    summary = SummaryBuilder(
        model_id=config.model_id,
        tool_call_count=counter.count,
        hypothesis_text=run_result.analysis_text,
        evaluation_text=run_result.critic_text,
        parsed_hypothesis=run_result.parsed_hypothesis,
        parsed_evaluation=run_result.parsed_evaluation,
    ).build(timestamp=timestamp)
    write_summary(paths.summary, summary)
    emit_log_entry(paths.raw_logs, build_log_entry(agent="runner", role="system", content="summary_written"))


if __name__ == "__main__":
    main()
