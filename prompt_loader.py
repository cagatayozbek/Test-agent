from pathlib import Path


PROMPT_FILES = [
    "planner",
    "analysis",
    "testwriter",
    "critic",
    "reflection",
    "executor",
]


def load_prompts(root: Path) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for name in PROMPT_FILES:
        prompts[name] = (root / f"{name}.txt").read_text(encoding="utf-8")
    return prompts
