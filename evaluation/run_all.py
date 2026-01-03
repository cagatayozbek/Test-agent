#!/usr/bin/env python3
"""
evaluation/run_all.py
Tüm adversarial task'ları baseline ve agentic modda çalıştırır.
Supports both bug detection (v1) and test generation (v2) modes.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def discover_tasks(tasks_dir: Path) -> list[str]:
    """evaluation/tasks/ altındaki tüm task klasörlerini bul."""
    if not tasks_dir.exists():
        return []
    return [
        d.name for d in tasks_dir.iterdir()
        if d.is_dir() and (d / "metadata.json").exists()
    ]


def discover_tasks_v2(tasks_dir: Path) -> list[str]:
    """evaluation/tasks_v2/ altındaki tüm test generation task'larını bul."""
    if not tasks_dir.exists():
        return []
    return [
        d.name for d in tasks_dir.iterdir()
        if d.is_dir() and (d / "buggy").exists() and (d / "fixed").exists()
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


def run_test_generation_tasks(
    tasks_dir: Path,
    base_dir: Path,
    modes: list[str],
    task_filter: Optional[str] = None,
    verbose: bool = False,
    max_retries: int = 3,
) -> dict:
    """
    Run test generation evaluation on tasks_v2/ tasks with retry support.
    
    For each task:
    1. Run agent pipeline to generate a test
    2. Validate test against buggy/fixed code
    3. If not bug-revealing, retry with feedback (up to max_retries)
    4. Calculate BRTR (Bug-Revealing Test Rate)
    
    Requires GOOGLE_API_KEY environment variable for LLM evaluation.
    
    Args:
        tasks_dir: Path to tasks_v2/ directory
        base_dir: Project root directory
        modes: List of modes to run ("baseline", "agentic")
        task_filter: Optional substring filter for task IDs
        verbose: Enable verbose output
        max_retries: Maximum retry attempts per task (default: 3)
    
    Returns:
        {
            "timestamp": str,
            "evaluation_type": "test_generation",
            "results": [...],
            "brtr_summary": {"baseline": float, "agentic": float}
        }
    """
    tasks = discover_tasks_v2(tasks_dir)
    
    if task_filter:
        tasks = [t for t in tasks if task_filter in t]
    
    if not tasks:
        print("No test generation tasks found in tasks_v2/")
        return {"timestamp": datetime.now().isoformat(), "results": [], "brtr_summary": {}}
    
    print(f"🧪 Test Generation Mode (with retry)")
    print(f"Discovered {len(tasks)} task(s): {tasks}")
    print(f"Modes: {modes}")
    print(f"Max retries: {max_retries}")
    print("-" * 50)
    
    # Initialize LLM for evaluation
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("❌ GOOGLE_API_KEY is required for test evaluation")
        print("   Set it in your environment or .env file")
        sys.exit(1)
    
    from llm_client import GeminiClient
    from evaluation.test_evaluator import TestEvaluator
    from task_loader import load_task_context_v2
    from config import load_config
    from graph_loader import load_agent_graph
    from prompt_loader import load_prompts
    from run_paths import build_run_paths
    from instrumented_tools import InstrumentedTools, ToolCounter
    from custom_session import TestGenerationSession, SummaryBuilder
    from runner import write_summary, iso8601_utc_timestamp
    
    # Load configuration
    config = load_config(base_dir / "config.yaml")
    graph = load_agent_graph(base_dir / "agents" / "agent_graph.yaml")
    prompts = load_prompts(base_dir / "prompts")
    
    # Use config retry settings if available
    if config.test_generation:
        max_retries = config.test_generation.max_retry_attempts
        test_timeout = config.test_generation.test_timeout_seconds
    else:
        test_timeout = 60
    
    print(f"✓ Config loaded: max_retries={max_retries}, timeout={test_timeout}s")
    
    all_results = []
    
    for task_id in tasks:
        # Load V2 task context
        task_context = load_task_context_v2(base_dir, task_id)
        if not task_context:
            print(f"⚠️ Could not load task context for {task_id}")
            continue
        
        bug_description = task_context.get_bug_description()
        
        for mode in modes:
            run_id = generate_run_id(mode)
            print(f"\n{'='*60}")
            print(f"[{task_id}] mode={mode} run_id={run_id}")
            print(f"Bug: {bug_description[:80]}...")
            print(f"{'='*60}")
            
            # Setup paths and tools
            paths = build_run_paths(base_dir, task=task_id, run_id=run_id)
            paths.root.mkdir(parents=True, exist_ok=True)
            paths.tool_outputs.mkdir(parents=True, exist_ok=True)
            
            counter = ToolCounter()
            tools = InstrumentedTools(counter)
            
            # Create LLM clients
            llm = GeminiClient(model_id=config.model_id, api_key=api_key)
            eval_llm = GeminiClient(model_id="gemini-2.0-flash", api_key=api_key)
            test_evaluator = TestEvaluator(eval_llm)
            
            result = {
                "task_id": task_id,
                "mode": mode,
                "run_id": run_id,
                "success": False,
                "error": None,
            }
            
            try:
                # Run test generation session with retry
                session = TestGenerationSession(
                    graph=graph,
                    mode=mode,
                    prompts=prompts,
                    tools=tools,
                    log_path=paths.raw_logs,
                    llm=llm,
                    task_context=task_context,
                    test_evaluator=test_evaluator,
                    max_retries=max_retries,
                    test_timeout=test_timeout,
                )
                
                session_result = session.run()
                
                # Build result
                result["success"] = session_result.success
                result["attempts"] = session_result.attempts
                result["test_validation"] = {
                    "is_bug_revealing": session_result.success,
                    "test_file": str(session_result.final_test_file) if session_result.final_test_file else None,
                    "attempts_detail": [
                        {
                            "attempt": r.attempt,
                            "buggy_failed": r.buggy_failed,
                            "fixed_passed": r.fixed_passed,
                            "is_bug_revealing": r.is_bug_revealing,
                            "failure_category": r.evaluation.failure_category if r.evaluation else "no_test",
                        }
                        for r in session_result.results
                    ],
                }
                
                # Write summary
                timestamp = iso8601_utc_timestamp()
                if session_result.results:
                    last_result = session_result.results[-1]
                    summary = SummaryBuilder(
                        model_id=config.model_id,
                        tool_call_count=counter.count,
                        hypothesis_text=f"Test generation {'succeeded' if session_result.success else 'failed'} after {session_result.attempts} attempts",
                        evaluation_text=last_result.evaluation.commentary if last_result.evaluation else "",
                    ).build(timestamp=timestamp)
                    write_summary(paths.summary, summary)
                
                # Show result
                emoji = "🎯" if session_result.success else "❌"
                print(f"\n{emoji} Final: bug_revealing={session_result.success} "
                      f"(attempts: {session_result.attempts})")
                
            except Exception as e:
                result["error"] = str(e)
                print(f"❌ Error: {e}")
            
            all_results.append(result)
    
    # Calculate BRTR summary
    brtr_summary = {}
    for mode in modes:
        mode_results = [r for r in all_results if r["mode"] == mode]
        if mode_results:
            bug_revealing = sum(
                1 for r in mode_results 
                if r.get("test_validation", {}).get("is_bug_revealing", False)
            )
            brtr_summary[mode] = bug_revealing / len(mode_results)
        else:
            brtr_summary[mode] = 0.0
    
    # Calculate attempts stats
    attempts_stats = {}
    for mode in modes:
        mode_results = [r for r in all_results if r["mode"] == mode]
        successful = [r for r in mode_results if r.get("test_validation", {}).get("is_bug_revealing", False)]
        if successful:
            avg_attempts = sum(r.get("attempts", 1) for r in successful) / len(successful)
            attempts_stats[mode] = {
                "avg_attempts_to_success": round(avg_attempts, 2),
                "success_count": len(successful),
            }
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "evaluation_type": "test_generation",
        "max_retries": max_retries,
        "results": all_results,
        "summary": {
            "total": len(all_results),
            "passed": sum(1 for r in all_results if r["success"]),
            "bug_revealing": sum(
                1 for r in all_results 
                if r.get("test_validation", {}).get("is_bug_revealing", False)
            ),
        },
        "brtr_summary": brtr_summary,
        "attempts_stats": attempts_stats,
    }
    
    print("\n" + "-" * 50)
    print(f"Total: {report['summary']['total']} | "
          f"Passed: {report['summary']['passed']} | "
          f"Bug-Revealing: {report['summary']['bug_revealing']}")
    print("\n📊 BRTR Summary:")
    for mode, brtr in brtr_summary.items():
        attempts_info = attempts_stats.get(mode, {})
        avg = attempts_info.get("avg_attempts_to_success", "N/A")
        print(f"  {mode}: {brtr:.1%} (avg attempts: {avg})")
    
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
    parser.add_argument(
        "--test-gen",
        action="store_true",
        help="Run in test generation mode (uses tasks_v2/)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retry attempts for test generation (default: 3)"
    )
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    
    modes = ["baseline", "agentic"] if args.mode == "both" else [args.mode]
    
    if args.test_gen:
        # Test generation mode - use tasks_v2/
        tasks_dir = Path(__file__).parent / "tasks_v2"
        report = run_test_generation_tasks(
            tasks_dir=tasks_dir,
            base_dir=base_dir,
            modes=modes,
            task_filter=args.task,
            verbose=args.verbose,
            max_retries=args.max_retries,
        )
    else:
        # Bug detection mode - use tasks/
        tasks_dir = Path(__file__).parent / "tasks"
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
        from config import load_config
        
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            print("⚠️  GOOGLE_API_KEY not set, skipping evaluation")
        else:
            config = load_config(base_dir / "config.yaml")
            llm = GeminiClient(model_id=config.model_id, api_key=api_key)
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
