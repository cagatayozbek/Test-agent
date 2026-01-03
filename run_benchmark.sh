#!/bin/bash

# Hata durumunda durma
set +e

# Gerekli paketler
pip install pandas tabulate > /dev/null 2>&1

# Test edilecek Task Listesi - BugsinPy ve diğer tüm tasklar
TASKS=(
    "async_race_condition"
    "boundary_threshold"
    "bugsinpy_black_async_for_13"
    "bugsinpy_pysnooper_unicode_1"
    "bugsinpy_thefuck_fish_version_3"
    "bugsinpy_thefuck_fix_file_28"
    "bugsinpy_tqdm_enumerate_start_1"
    "cache_invalidation"
    "indirect_cause"
    "misleading_coverage"
    "null_handling_profile"
    "off_by_one_loop"
    "state_dependent_bug"
    "swallowed_exception"
    "type_coercion_price"
)

# 3 Model ile test
MODELS=("gemini-2.0-flash" "gemini-2.5-flash" "gemini-2.5-pro")

echo "🚀 Temiz Benchmark Başlıyor..."
echo "📊 Modeller: ${MODELS[@]}"
echo "📝 Task Sayısı: ${#TASKS[@]}"
echo "🎯 Her model x task için: 1 agentic + 1 baseline"
echo "--------------------------------"

# Benchmark sonuçları için klasör oluştur
mkdir -p benchmark_runs

# Mevcut config yedeği
cp config.yaml config.yaml.bak

for MODEL in "${MODELS[@]}"; do
    echo ""
    echo "=========================================="
    echo "🤖 MODEL: $MODEL"
    echo "=========================================="
    
    # Config'i güncelle
    sed -i '' "s/model_id: .*/model_id: \"$MODEL\"/" config.yaml
    
    for MODE in "agentic" "baseline"; do
        echo ""
        echo "🔄 Mod: $MODE"
        echo "--------------------------------"
        
        for TASK in "${TASKS[@]}"; do
            echo "  👉 Task: $TASK"
            
            # Çalıştır ve çıktıyı göster
            set -a && source .env && set +a && python3 evaluation/run_all.py \
                --test-gen \
                --mode "$MODE" \
                --task "$TASK" \
                --max-retries 2 \
                --verbose
            
            # Son run'ı benchmark_runs klasörüne kopyala
            LATEST_RUN=$(ls -t "runs/$TASK" | grep "^${MODE}_" | head -1)
            if [ -n "$LATEST_RUN" ]; then
                mkdir -p "benchmark_runs/$TASK"
                cp -r "runs/$TASK/$LATEST_RUN" "benchmark_runs/$TASK/"
                echo "  ✅ Run kopyalandı: benchmark_runs/$TASK/$LATEST_RUN"
            fi
            
            echo ""
        done
    done
done

# Config'i geri yükle
mv config.yaml.bak config.yaml

echo ""
echo "================================"
echo "📊 Rapor oluşturuluyor..."
echo "================================"
python3 generate_benchmark_report.py

echo ""
echo "🎉 Benchmark Tamamlandı!"
echo "📄 Rapor: benchmark_report.md"
echo "📁 Sonuçlar: benchmark_runs/"
