#!/usr/bin/env python3
"""
Eksik benchmark runlarını tespit edip tamamlayan script.
Her task için 3 model x 2 mod = 6 run olmalı.
"""

import os
import subprocess
import json
from pathlib import Path

# Beklenen konfigürasyon
TASKS = [
    "async_race_condition",
    "boundary_threshold",
    "bugsinpy_black_async_for_13",
    "bugsinpy_pysnooper_unicode_1",
    "bugsinpy_thefuck_fish_version_3",
    "bugsinpy_thefuck_fix_file_28",
    "bugsinpy_tqdm_enumerate_start_1",
    "cache_invalidation",
    "indirect_cause",
    "misleading_coverage",
    "null_handling_profile",
    "off_by_one_loop",
    "state_dependent_bug",
    "swallowed_exception",
    "type_coercion_price"
]

MODELS = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
MODES = ["agentic", "baseline"]

def get_completed_runs():
    """benchmark_runs klasöründeki tamamlanmış runları analiz et."""
    completed = {}
    benchmark_dir = Path("benchmark_runs")
    
    if not benchmark_dir.exists():
        return completed
    
    for task in TASKS:
        task_dir = benchmark_dir / task
        if not task_dir.exists():
            completed[task] = []
            continue
        
        task_runs = []
        for run_dir in task_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            summary_file = run_dir / "summary.json"
            if not summary_file.exists():
                continue
            
            try:
                with open(summary_file) as f:
                    data = json.load(f)
                    model = data.get("model_id", "unknown")
                    
                    # Mode'u run_dir isminden çıkar
                    mode = "unknown"
                    if run_dir.name.startswith("agentic"):
                        mode = "agentic"
                    elif run_dir.name.startswith("baseline"):
                        mode = "baseline"
                    
                    task_runs.append((model, mode))
            except:
                continue
        
        completed[task] = task_runs
    
    return completed

def find_missing_runs():
    """Eksik runları tespit et."""
    completed = get_completed_runs()
    missing = []
    
    for task in TASKS:
        completed_runs = completed.get(task, [])
        
        for model in MODELS:
            for mode in MODES:
                if (model, mode) not in completed_runs:
                    missing.append((task, model, mode))
    
    return missing

def run_task(task, model, mode):
    """Tek bir task'ı çalıştır."""
    print(f"  🔄 {task} - {model} - {mode}")
    
    # config.yaml'ı güncelle
    os.system(f"sed -i '' 's/model_id: .*/model_id: \"{model}\"/' config.yaml")
    
    # run_all.py'yi çalıştır
    cmd = [
        "python3", "evaluation/run_all.py",
        "--test-gen",
        "--mode", mode,
        "--task", task,
        "--max-retries", "2",
        "--verbose"
    ]
    
    # .env dosyasını source et
    env = os.environ.copy()
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Tırnakları kaldır
                value = value.strip().strip('"').strip("'")
                env[key] = value
    
    result = subprocess.run(cmd, env=env, capture_output=False)
    
    # En son run'ı benchmark_runs'a kopyala
    import time
    time.sleep(1)  # Dosya sisteminin güncellenmesi için kısa bir bekleme
    
    latest_run_cmd = f"ls -t runs/{task} | grep '^{mode}_' | head -1"
    latest_run = subprocess.run(latest_run_cmd, shell=True, capture_output=True, text=True).stdout.strip()
    
    if latest_run:
        os.makedirs(f"benchmark_runs/{task}", exist_ok=True)
        os.system(f"cp -r runs/{task}/{latest_run} benchmark_runs/{task}/")
        print(f"  ✅ Kopyalandı: {latest_run}")
    
    return result.returncode == 0

def main():
    print("🔍 Eksik runlar analiz ediliyor...")
    print()
    
    missing = find_missing_runs()
    
    if not missing:
        print("✅ Tüm runlar tamamlanmış!")
        return
    
    print(f"📋 Eksik run sayısı: {len(missing)}")
    print()
    
    # Model bazında grupla
    by_model = {}
    for task, model, mode in missing:
        if model not in by_model:
            by_model[model] = []
        by_model[model].append((task, mode))
    
    for model in MODELS:
        if model not in by_model:
            continue
        
        print(f"\n{'='*60}")
        print(f"🤖 MODEL: {model}")
        print(f"{'='*60}")
        
        runs = by_model[model]
        print(f"Eksik run sayısı: {len(runs)}")
        print()
        
        for task, mode in runs:
            success = run_task(task, model, mode)
            if not success:
                print(f"  ⚠️  Hata oluştu, devam ediliyor...")
            print()
    
    # Config'i geri yükle
    if os.path.exists("config.yaml.bak"):
        os.system("mv config.yaml.bak config.yaml")
    
    print("\n" + "="*60)
    print("🎉 Eksik runlar tamamlandı!")
    print("📊 Rapor oluşturuluyor...")
    print("="*60)
    
    subprocess.run(["python3", "generate_benchmark_report.py"])

if __name__ == "__main__":
    # Config yedeği al
    os.system("cp config.yaml config.yaml.bak")
    
    try:
        main()
    finally:
        # Config'i geri yükle
        if os.path.exists("config.yaml.bak"):
            os.system("mv config.yaml.bak config.yaml")
