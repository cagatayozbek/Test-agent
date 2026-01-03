import json
import glob
import os
import io
import re
import pandas as pd
from datetime import datetime

def parse_raw_logs(logs_path):
    """Parse raw_logs.jsonl to extract token usage and timing information."""
    if not os.path.exists(logs_path):
        return {
            "total_tokens": 0,
            "total_duration": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "agent_steps": 0
        }
    
    total_tokens = 0
    total_duration = 0
    prompt_tokens = 0
    completion_tokens = 0
    agent_steps = 0
    
    try:
        with open(logs_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Count agent steps (assistant role = agent response)
                    if entry.get("role") == "assistant":
                        agent_steps += 1
                    
                    # Extract duration
                    if "duration_seconds" in entry:
                        total_duration += entry["duration_seconds"]
                    
                    # Extract token usage
                    if "token_usage" in entry:
                        tokens = entry["token_usage"]
                        total_tokens += tokens.get("total_tokens", 0)
                        prompt_tokens += tokens.get("prompt_tokens", 0)
                        completion_tokens += tokens.get("completion_tokens", 0)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error parsing raw logs {logs_path}: {e}")
    
    return {
        "total_tokens": total_tokens,
        "total_duration": total_duration,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "agent_steps": agent_steps
    }

def generate_report():
    results = []
    
    # Benchmark sonuçlarını benchmark_runs klasöründen oku
    base_dir = "benchmark_runs"
    
    if not os.path.exists(base_dir):
        print(f"❌ {base_dir} klasörü bulunamadı!")
        print("💡 Önce './run_benchmark.sh' komutunu çalıştırın.")
        return
    
    # Gerçek task'ları belirle (evaluation/tasks_v2/ klasöründeki task'lar)
    real_tasks = set()
    tasks_dir = "evaluation/tasks_v2"
    if os.path.exists(tasks_dir):
        real_tasks = set(os.listdir(tasks_dir))
        # Gizli dosyaları ve __pycache__ gibi dizinleri çıkar
        real_tasks = {t for t in real_tasks if not t.startswith('.') and t != '__pycache__'}
        print(f"📋 Gerçek task sayısı: {len(real_tasks)}")
        print(f"✅ Gerçek task'lar: {sorted(real_tasks)}\n")
    else:
        print(f"⚠️  {tasks_dir} bulunamadı, tüm task'lar dahil edilecek.\n")
    
    # Tüm run klasörlerini gez
    for task_name in os.listdir(base_dir):
        task_path = os.path.join(base_dir, task_name)
        
        # Gerçek task kontrolü
        if real_tasks and task_name not in real_tasks:
            print(f"⏭️  Atlanıyor (gerçek task değil): {task_name}")
            continue
        if not os.path.isdir(task_path):
            continue
            
        for run_id in os.listdir(task_path):
            run_path = os.path.join(task_path, run_id)
            summary_path = os.path.join(run_path, "summary.json")
            raw_logs_path = os.path.join(run_path, "raw_logs.jsonl")
            
            if not os.path.exists(summary_path):
                continue
                
            try:
                with open(summary_path, 'r') as f:
                    data = json.load(f)
                
                # Extract Mode from run_id (directory name)
                mode = "unknown"
                if run_id.startswith("agentic"):
                    mode = "agentic"
                elif run_id.startswith("baseline"):
                    mode = "baseline"
                
                # Extract Success and Attempts from hypothesis text
                hypothesis_text = data.get("hypothesis", {}).get("hypothesis", "")
                success = False
                attempts = 0
                
                if "succeeded" in hypothesis_text.lower():
                    success = True
                
                match = re.search(r"after (\d+) attempts", hypothesis_text)
                if match:
                    attempts = int(match.group(1))
                
                # Parse raw logs for detailed metrics
                log_metrics = parse_raw_logs(raw_logs_path)

                # Veriyi düzleştir
                row = {
                    "Task": task_name,
                    "Mode": mode,
                    "Model": data.get("model_id", "unknown"),
                    "Run ID": run_id,
                    "Success": success,
                    "Attempts": attempts,
                    "Tool Calls": data.get("tool_call_count", 0),
                    "Total Tokens": log_metrics["total_tokens"],
                    "Prompt Tokens": log_metrics["prompt_tokens"],
                    "Completion Tokens": log_metrics["completion_tokens"],
                    "Duration (s)": round(log_metrics["total_duration"], 2),
                    "Agent Steps": log_metrics["agent_steps"]
                }
                results.append(row)
            except Exception as e:
                print(f"Error reading {summary_path}: {e}")

    if not results:
        print("No results found.")
        return

    df = pd.read_json(io.StringIO(json.dumps(results)))
    
    # Rapor Markdown
    md = "# Benchmark Raporu: Baseline vs Agentic (Detaylı Analiz)\n\n"
    md += f"**Rapor Tarihi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # 1. Genel Özet (Model + Mode bazında)
    md += "## 1. Genel Özet (Model ve Mode Bazında)\n\n"
    summary = df.groupby(['Model', 'Mode']).agg({
        'Success': 'mean',  # Başarı oranı
        'Attempts': 'mean',
        'Tool Calls': 'mean',
        'Total Tokens': 'mean',
        'Duration (s)': 'mean',
        'Agent Steps': 'mean',
        'Run ID': 'count'  # Kaç run var
    }).reset_index()
    
    summary.columns = ['Model', 'Mode', 'Success Rate (%)', 'Avg Attempts', 
                       'Avg Tool Calls', 'Avg Total Tokens', 'Avg Duration (s)', 
                       'Avg Agent Steps', 'Run Count']
    summary['Success Rate (%)'] = (summary['Success Rate (%)'] * 100).round(1)
    
    md += summary.to_markdown(index=False, floatfmt=".1f")
    md += "\n\n"
    
    # 2. Task Bazlı Başarı Oranı
    md += "## 2. Task Bazlı Başarı Analizi\n\n"
    task_success = df.pivot_table(
        index=['Task'], 
        columns=['Model', 'Mode'], 
        values='Success',
        aggfunc='mean'  # Ortalama başarı oranı
    ) * 100  # Yüzdeye çevir
    md += task_success.to_markdown(floatfmt=".0f")
    md += "\n\n"
    
    # 3. Task Bazlı Ortalama Attempt Sayısı
    md += "## 3. Task Bazlı Ortalama Attempt Sayısı\n\n"
    task_attempts = df.pivot_table(
        index=['Task'], 
        columns=['Model', 'Mode'], 
        values='Attempts',
        aggfunc='mean'
    )
    md += task_attempts.to_markdown(floatfmt=".1f")
    md += "\n\n"
    
    # 4. Task Bazlı Ortalama Token Kullanımı
    md += "## 4. Task Bazlı Ortalama Token Kullanımı\n\n"
    task_tokens = df.pivot_table(
        index=['Task'], 
        columns=['Model', 'Mode'], 
        values='Total Tokens',
        aggfunc='mean'
    )
    md += task_tokens.to_markdown(floatfmt=".0f")
    md += "\n\n"
    
    # 5. Task Bazlı Ortalama Süre
    md += "## 5. Task Bazlı Ortalama Süre (saniye)\n\n"
    task_duration = df.pivot_table(
        index=['Task'], 
        columns=['Model', 'Mode'], 
        values='Duration (s)',
        aggfunc='mean'
    )
    md += task_duration.to_markdown(floatfmt=".1f")
    md += "\n\n"
    
    # 6. Detaylı Run Listesi (başarısız olanlar)
    md += "## 6. Başarısız Runlar (Detay)\n\n"
    failed_runs = df[df['Success'] == False][['Task', 'Model', 'Mode', 'Attempts', 
                                               'Total Tokens', 'Duration (s)', 'Run ID']]
    if not failed_runs.empty:
        md += failed_runs.to_markdown(index=False, floatfmt=".1f")
    else:
        md += "Tüm runlar başarılı! 🎉\n"
    md += "\n\n"
    
    # 7. Maliyet Analizi (Token bazlı tahmini)
    md += "## 7. Maliyet Analizi (Tahmini)\n\n"
    md += "**Not:** Maliyet hesaplamaları Gemini pricing'e göre yaklaşık değerlerdir.\n\n"
    
    # Gemini 2.0 Flash: $0.30/1M input, $1.20/1M output (128k context)
    # Gemini 2.5 Flash: $0.30/1M input, $1.20/1M output (128k context)  
    # Gemini 2.5 Pro: $3.50/1M input, $10.50/1M output (128k context)
    
    cost_data = []
    for _, row in summary.iterrows():
        model = row['Model']
        mode = row['Mode']
        avg_prompt = df[(df['Model'] == model) & (df['Mode'] == mode)]['Prompt Tokens'].mean()
        avg_completion = df[(df['Model'] == model) & (df['Mode'] == mode)]['Completion Tokens'].mean()
        
        if 'flash' in model.lower():
            input_cost = (avg_prompt / 1_000_000) * 0.30
            output_cost = (avg_completion / 1_000_000) * 1.20
        elif 'pro' in model.lower():
            input_cost = (avg_prompt / 1_000_000) * 3.50
            output_cost = (avg_completion / 1_000_000) * 10.50
        else:
            input_cost = 0
            output_cost = 0
        
        total_cost = input_cost + output_cost
        
        cost_data.append({
            'Model': model,
            'Mode': mode,
            'Avg Prompt Tokens': avg_prompt,
            'Avg Completion Tokens': avg_completion,
            'Cost per Run ($)': total_cost,
            'Run Count': row['Run Count'],
            'Total Cost ($)': total_cost * row['Run Count']
        })
    
    cost_df = pd.DataFrame(cost_data)
    md += cost_df.to_markdown(index=False, floatfmt=".4f")
    md += "\n\n"
    
    with open("benchmark_report.md", "w") as f:
        f.write(md)
    
    print("✅ Detaylı rapor oluşturuldu: benchmark_report.md")

if __name__ == "__main__":
    generate_report()
