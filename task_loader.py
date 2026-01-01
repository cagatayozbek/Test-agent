"""Task context loader - loads code and test files for evaluation tasks."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TaskContext:
    """Context for an evaluation task."""
    task_id: str
    code_content: str
    test_content: str
    metadata: dict
    
    def to_prompt_context(self) -> str:
        """Format task context for LLM prompt injection."""
        lines = [
            "=== TASK CONTEXT ===",
            f"Task: {self.task_id}",
            "",
            "--- source_code.py ---",
            self.code_content,
            "",
            "--- test_code.py ---",
            self.test_content,
            "",
            "=== END CONTEXT ===",
            "",
            "Analyze the code and tests above. Identify any bugs, missing test coverage, or potential issues.",
        ]
        return "\n".join(lines)


def load_task_context(base_dir: Path, task_id: str) -> Optional[TaskContext]:
    """
    Load task context from evaluation/tasks/<task_id>/.
    
    Returns None if task doesn't exist or is a dummy task.
    """
    task_dir = base_dir / "evaluation" / "tasks" / task_id
    
    if not task_dir.exists():
        # Dummy task or legacy task - no context
        return None
    
    code_path = task_dir / "source_code.py"
    test_path = task_dir / "test_code.py"
    metadata_path = task_dir / "metadata.json"
    
    if not code_path.exists() or not test_path.exists():
        return None
    
    code_content = code_path.read_text(encoding="utf-8")
    test_content = test_path.read_text(encoding="utf-8")
    
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    
    return TaskContext(
        task_id=task_id,
        code_content=code_content,
        test_content=test_content,
        metadata=metadata,
    )
