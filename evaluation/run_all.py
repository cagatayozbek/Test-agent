#!/usr/bin/env python3
"""
evaluation/run_all.py
Tüm adversarial task'ları baseline ve agentic modda çalıştırır.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def discover_tasks(tasks_dir: Path) -> list[str]:
    """evaluation/tasks/ altındaki tüm task klasörlerini bul."""
    if not tasks_dir.exists():
        return []
    return [
        d.name for d in tasks_dir.iterdir()
        if d.is_dir() and (d / "metadata.json").exists()
    ]


def run_single_task(
    task_id: str,
    run_id: str,
    mode: str,
    base_dir: Path,
    verbose: bool = False
) -> dict:
    """
    Tek bir task'ı çalıştır.
    
    Returns:
        {"task_id": str, "mode": str, "run_id": str, "success": bool, "error": str|None}
    """
    result = {
        "task_id": task_id,
        "mode": mode,
        "run_id": run_id,
        "success": False,
        "error": None,
        "summary_path": None,
    }
    
    main_py = base_dir / "main.py"
    if not main_py.exists():
        result["error"] = "main.py not found"
        return result
    
    cmd = [
        sys.executable,
        str(main_py),
        "--task", task_id,
        "--run-id", run_id,
        "--mode", mode,
    ]
    
    env = os.environ.copy()
    
    try:
        if verbose:
            print(f"  Running: {' '.join(cmd)}")
            print("-" * 40)
            # Live output mode - don't capture
            proc = subprocess.run(
                cmd,
                cwd=str(base_dir),
                env=env,
                timeout=300,
            )
            print("-" * 40)
        else:
            # Quiet mode - capture output
            proc = subprocess.run(
                cmd,
                cwd=str(base_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
        
        if proc.returncode == 0:
            result["success"] = True
            summary_path = base_dir / "runs" / task_id / run_id / "summary.json"
            if summary_path.exists():
                result["summary_path"] = str(summary_path)
        else:
            stderr_text = getattr(proc, 'stderr', '') or ''
            result["error"] = stderr_text[:500] if stderr_text else f"Exit code: {proc.returncode}"
                
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout (300s)"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def generate_run_id(mode: str) -> str:
    """Unique run ID oluştur."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{mode}_{ts}"


def run_all_tasks(
    tasks_dir: Path,
    base_dir: Path,
    modes: list[str],
    task_filter: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Tüm task'ları belirtilen modlarda çalıştır.
    
    Returns:
        {
            "timestamp": str,
            "results": [{"task_id": ..., "mode": ..., ...}, ...],
            "summary": {"total": int, "passed": int, "failed": int}
        }
    """
    tasks = discover_tasks(tasks_dir)
    
    if task_filter:
        tasks = [t for t in tasks if task_filter in t]
    
    if not tasks:
        print("No tasks found.")
        return {"timestamp": datetime.now().isoformat(), "results": [], "summary": {}}
    
    print(f"Discovered {len(tasks)} task(s): {tasks}")
    print(f"Modes: {modes}")
    print("-" * 50)
    
    all_results = []
    
    for task_id in tasks:
        for mode in modes:
            run_id = generate_run_id(mode)
            print(f"[{task_id}] mode={mode} run_id={run_id}")
            
            result = run_single_task(
                task_id=task_id,
                run_id=run_id,
                mode=mode,
                base_dir=base_dir,
                verbose=verbose,
            )
            
            status = "✓" if result["success"] else "✗"
            print(f"  {status} {'OK' if result['success'] else result['error']}")
            
            all_results.append(result)
    
    passed = sum(1 for r in all_results if r["success"])
    failed = len(all_results) - passed
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": all_results,
        "summary": {
            "total": len(all_results),
            "passed": passed,
            "failed": failed,
        }
    }
    
    print("-" * 50)
    print(f"Total: {report['summary']['total']} | Passed: {passed} | Failed: {failed}")
    
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run adversarial evaluation tasks")
    parser.add_argument(
        "--mode",
        choices=["baseline", "agentic", "both"],
        default="both",
        help="Which mode(s) to run (default: both)"
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Filter to specific task (substring match)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output JSON report path"
    )
    parser.add_argument(
        "--evaluate", "-e",
        action="store_true",
        help="Run LLM-based evaluation after each task"
    )
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    tasks_dir = Path(__file__).parent / "tasks"
    
    modes = ["baseline", "agentic"] if args.mode == "both" else [args.mode]
    
    report = run_all_tasks(
        tasks_dir=tasks_dir,
        base_dir=base_dir,
        modes=modes,
        task_filter=args.task,
        verbose=args.verbose,
    )
    
    # Run evaluations if requested
    if args.evaluate:
        print("\n" + "=" * 50)
        print("🔍 Running LLM-based evaluations...")
        print("=" * 50)
        
        # Import from same directory
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from evaluator import Evaluator, load_run_data, load_task_metadata
        from llm_client import GeminiClient
        
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            print("⚠️  GOOGLE_API_KEY not set, skipping evaluation")
        else:
            llm = GeminiClient(model_id="gemini-2.5-pro", api_key=api_key)
            evaluator = Evaluator(llm)
            
            evaluations = []
            for result in report["results"]:
                if not result["success"]:
                    continue
                
                task_id = result["task_id"]
                run_id = result["run_id"]
                mode = result["mode"]
                
                print(f"\n📊 Evaluating [{task_id}] {mode}...")
                
                run_dir = base_dir / "runs" / task_id / run_id
                raw_logs, summary = load_run_data(run_dir)
                metadata = load_task_metadata(tasks_dir, task_id)
                
                eval_report = evaluator.evaluate_run(
                    task_id=task_id,
                    run_id=run_id,
                    mode=mode,
                    metadata=metadata,
                    raw_logs=raw_logs,
                    summary=summary,
                )
                
                evaluations.append({
                    "task_id": task_id,
                    "run_id": run_id,
                    "mode": mode,
                    "bug_identified": eval_report.bug_identified,
                    "quality": eval_report.bug_description_quality,
                    "reasoning": eval_report.reasoning_quality,
                    "score": eval_report.overall_score,
                    "commentary": eval_report.commentary,
                })
                
                emoji = "✅" if eval_report.bug_identified else "❌"
                print(f"  {emoji} Bug: {eval_report.bug_description_quality} | "
                      f"Reasoning: {eval_report.reasoning_quality} | "
                      f"Score: {eval_report.overall_score}/10")
            
            report["evaluations"] = evaluations
            
            # Print summary
            print("\n" + "-" * 50)
            print("📈 Evaluation Summary:")
            for mode in modes:
                mode_evals = [e for e in evaluations if e["mode"] == mode]
                if mode_evals:
                    avg_score = sum(e["score"] for e in mode_evals) / len(mode_evals)
                    bug_found = sum(1 for e in mode_evals if e["bug_identified"])
                    print(f"  {mode}: avg_score={avg_score:.1f}/10, bugs_found={bug_found}/{len(mode_evals)}")
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
