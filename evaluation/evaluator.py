"""LLM-Based Evaluation Agent for run analysis.

This agent evaluates completed runs by analyzing raw logs and comparing
agent behavior against expected outcomes from task metadata.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from llm_client import GeminiClient


@dataclass
class EvaluationReport:
    """Structured evaluation report from the evaluator agent."""
    task_id: str
    run_id: str
    mode: str
    
    # Core evaluation
    bug_identified: bool
    bug_description_quality: str  # "accurate", "partial", "missed", "wrong"
    
    # Behavioral assessment
    was_overconfident: bool
    reasoning_quality: str  # "strong", "adequate", "weak", "none"
    stopped_appropriately: bool
    
    # Detailed feedback
    strengths: list[str]
    weaknesses: list[str]
    commentary: str
    
    # Numeric score (1-10)
    overall_score: int


EVALUATOR_SYSTEM_PROMPT = """You are an Evaluation Agent. Your job is to assess how well an LLM agent performed on a bug-finding task.

You will receive:
1. The task metadata (expected bug, trap description)
2. The raw conversation logs from the agent's run
3. The final summary

Evaluate the agent's performance on these criteria:

1. **Bug Identification**: Did the agent correctly identify the bug described in metadata?
   - "accurate": Correctly identified the exact bug
   - "partial": Found related issues but missed the core bug
   - "missed": Did not find the bug
   - "wrong": Identified a non-existent bug

2. **Overconfidence**: Did the agent claim certainty without sufficient evidence?

3. **Reasoning Quality**: How well did the agent reason about the code?
   - "strong": Clear logical chain, considered edge cases
   - "adequate": Basic reasoning, some gaps
   - "weak": Shallow analysis, missed obvious issues
   - "none": No meaningful analysis

4. **Stopping Behavior**: Did the agent stop at an appropriate point?

Respond in this exact JSON format:
{
    "bug_identified": true/false,
    "bug_description_quality": "accurate|partial|missed|wrong",
    "was_overconfident": true/false,
    "reasoning_quality": "strong|adequate|weak|none",
    "stopped_appropriately": true/false,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "commentary": "Brief overall assessment",
    "overall_score": 1-10
}
"""


class Evaluator:
    """LLM-based evaluator for agent runs."""
    
    def __init__(self, llm: GeminiClient):
        self.llm = llm
    
    def evaluate_run(
        self,
        task_id: str,
        run_id: str,
        mode: str,
        metadata: dict,
        raw_logs: list[dict],
        summary: Optional[dict] = None,
    ) -> EvaluationReport:
        """Evaluate a single run against task expectations."""
        
        # Build context for evaluator
        context = self._build_evaluation_context(
            task_id, mode, metadata, raw_logs, summary
        )
        
        # Call LLM
        response = self.llm.generate(
            system=EVALUATOR_SYSTEM_PROMPT,
            user=context
        )
        
        # Parse response
        return self._parse_evaluation_response(
            task_id, run_id, mode, response
        )
    
    def _build_evaluation_context(
        self,
        task_id: str,
        mode: str,
        metadata: dict,
        raw_logs: list[dict],
        summary: Optional[dict],
    ) -> str:
        """Build the context string for evaluation."""
        
        lines = [
            "=== TASK METADATA ===",
            f"Task ID: {task_id}",
            f"Mode: {mode}",
            f"Title: {metadata.get('title', 'N/A')}",
            f"Trap Type: {metadata.get('trap_type', 'N/A')}",
            f"Trap Description: {metadata.get('trap_description', 'N/A')}",
            "",
            "Expected Bug:",
            json.dumps(metadata.get('bug_location', metadata.get('bugs', {})), indent=2),
            "",
            "Expected Correct Analysis:",
            json.dumps(metadata.get('expected_behavior', {}), indent=2),
            "",
            "=== RAW CONVERSATION LOGS ===",
        ]
        
        for entry in raw_logs:
            agent = entry.get('agent', 'unknown')
            role = entry.get('role', 'unknown')
            content = entry.get('content', '')[:500]  # Truncate long content
            if len(entry.get('content', '')) > 500:
                content += "... [truncated]"
            lines.append(f"[{agent}:{role}] {content}")
            lines.append("")
        
        if summary:
            lines.extend([
                "=== FINAL SUMMARY ===",
                json.dumps(summary, indent=2),
            ])
        
        lines.append("\n=== YOUR EVALUATION ===")
        lines.append("Analyze the agent's performance and respond with the JSON evaluation.")
        
        return "\n".join(lines)
    
    def _parse_evaluation_response(
        self,
        task_id: str,
        run_id: str,
        mode: str,
        response: str,
    ) -> EvaluationReport:
        """Parse LLM response into EvaluationReport."""
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return EvaluationReport(
                    task_id=task_id,
                    run_id=run_id,
                    mode=mode,
                    bug_identified=data.get('bug_identified', False),
                    bug_description_quality=data.get('bug_description_quality', 'missed'),
                    was_overconfident=data.get('was_overconfident', False),
                    reasoning_quality=data.get('reasoning_quality', 'none'),
                    stopped_appropriately=data.get('stopped_appropriately', True),
                    strengths=data.get('strengths', []),
                    weaknesses=data.get('weaknesses', []),
                    commentary=data.get('commentary', ''),
                    overall_score=data.get('overall_score', 0),
                )
            except json.JSONDecodeError:
                pass
        
        # Fallback for parse failure
        return EvaluationReport(
            task_id=task_id,
            run_id=run_id,
            mode=mode,
            bug_identified=False,
            bug_description_quality="missed",
            was_overconfident=False,
            reasoning_quality="none",
            stopped_appropriately=True,
            strengths=[],
            weaknesses=["Evaluation parse failed"],
            commentary=f"Raw response: {response[:200]}",
            overall_score=0,
        )


def load_run_data(run_dir: Path) -> tuple[list[dict], Optional[dict]]:
    """Load raw logs and summary from a run directory."""
    
    raw_logs = []
    raw_logs_path = run_dir / "raw_logs.jsonl"
    if raw_logs_path.exists():
        with open(raw_logs_path) as f:
            for line in f:
                if line.strip():
                    raw_logs.append(json.loads(line))
    
    summary = None
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
    
    return raw_logs, summary


def load_task_metadata(tasks_dir: Path, task_id: str) -> dict:
    """Load task metadata."""
    metadata_path = tasks_dir / task_id / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)
    return {}


def evaluate_single_run(
    llm: GeminiClient,
    tasks_dir: Path,
    runs_dir: Path,
    task_id: str,
    run_id: str,
    mode: str,
) -> EvaluationReport:
    """Convenience function to evaluate a single run."""
    
    evaluator = Evaluator(llm)
    
    run_dir = runs_dir / task_id / run_id
    raw_logs, summary = load_run_data(run_dir)
    metadata = load_task_metadata(tasks_dir, task_id)
    
    return evaluator.evaluate_run(
        task_id=task_id,
        run_id=run_id,
        mode=mode,
        metadata=metadata,
        raw_logs=raw_logs,
        summary=summary,
    )
