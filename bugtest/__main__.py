"""CLI entry point: python -m bugtest [config.yaml]"""

import sys
from pathlib import Path

from bugtest.experiment import run_experiment


def main() -> None:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("bugtest_config.yaml")
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        sys.exit(1)
    run_experiment(config_path)


if __name__ == "__main__":
    main()
