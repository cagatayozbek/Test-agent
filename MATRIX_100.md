# 100-Task BRTR Matrix — baseline × adaptive × deep (5 models)

Özet matris. Tüm sayılar ilgili `results/benchmark_v2_*_100*/summary.json`
dosyalarından okunmuştur. Detaylı analiz için bkz. `EXPERIMENT_REPORT.md`
§11 (deep leaderboard), §12–§13 (Sonnet baseline/adaptive), §14 (matrisin
tamamlanması).

**BRTR (Bug-Revealing Test Rate):** üretilen test buggy kodda FAIL **ve**
fixed kodda PASS edecek. Birincil metrik. Her hücre = 100 task × 3 run =
**300 run**. Güven aralıkları Wilson skoru, %95.

## Matris

| Model | baseline | adaptive | deep | deep kaynağı |
|---|---|---|---|---|
| **sonnet** | 94.3% † (283/300) | 94.0% † (282/300) | **100.0%** (300/300) | §11.1 |
| **haiku** | 98.0% (294/300) | 99.0% (297/300) | 99.0% (297/300) | §11.1 |
| **gpt-oss-120b** | 97.7% (293/300) | 98.0% (294/300) | 89.7% (269/300) | §11.1 |
| **qwen3-coder-next** | 89.0% (267/300) | 87.0% (261/300) | 82.3% (247/300) | §11.1 |
| **gpt-oss-20b** | 94.0% (282/300) | 95.0% (285/300) | **21.3%** (64/300) | merged |

**† Sonnet baseline/adaptive timeout-bozulmuş:** bu iki moddaki
başarısızlıkların ~%80'i gerçek test FAIL'i değil, 120s `claude -p`
subprocess timeout'udur (`attempts=0`, `ctok=0`). Timeout düzeltmesiyle
her iki mod ≈ %99'a çıkar; gerçek BRTR sonnet ≥ haiku beklenen sırasını
geri verir (bkz. §14.6).

## Wilson %95 güven aralıkları

| Model | baseline CI | adaptive CI | deep CI |
|---|---|---|---|
| sonnet | [91.1, 96.4] | [90.7, 96.2] | [98.7, 100.0] |
| haiku | [95.7, 99.1] | [97.1, 99.7] | [97.1, 99.7] |
| gpt-oss-120b | [95.3, 98.9] | [95.7, 99.1] | [85.7, 92.6] |
| qwen3-coder-next | [85.0, 92.1] | [82.7, 90.3] | [77.6, 86.2] |
| gpt-oss-20b | [90.7, 96.2] | [91.9, 97.0] | [17.1, 26.3] |

## Okunuş — analizin değeri model gücüne göre dereceli

- **Güçlü (sonnet):** deep mükemmelleştiriyor (1.000, +5.7pp); adaptive nötr.
- **Güçlü-orta (haiku):** üç mod da ~%98–99; deep ~5× prompt token'a rağmen
  BRTR kazandırmıyor → **tavan etkisi**.
- **Orta (gpt-oss-120b):** deep **zarar** veriyor (98 → 90, CI'lar ayrık).
- **Orta-zayıf (qwen):** **monoton zarar** — baseline 0.890 > adaptive 0.870
  > deep 0.823, analiz dozuyla ters orantılı; tüm başarısızlıklar gerçek.
- **Zayıf (gpt-oss-20b):** baseline/adaptive ~0.94–0.95, ama deep **çöküyor**
  (0.213) — küçük modelde tool döngüsü kendi kendini sabote ediyor; 236
  başarısızlığın tamamı gerçek test FAIL'i.

**Tek satır sonuç:** Analiz adımının işareti modele bağlıdır — yalnızca en
güçlü modelde net fayda (+5.7pp deep), orta/zayıf modellerde sıfır ya da
büyük zarar. Model kapasitesi baskın değişkendir.

## Ham veri dizinleri

| Hücre | Dizin |
|---|---|
| sonnet baseline | `results/benchmark_v2_sonnet_100_baseline_20260516_192612/` (+resume) |
| sonnet adaptive | `results/benchmark_v2_sonnet_100_adaptive_20260517_072031/` |
| haiku baseline | `results/benchmark_v2_haiku_100_baseline_20260525_211834/` |
| haiku adaptive | `results/benchmark_v2_haiku_100_adaptive_20260525_233102/` |
| gpt-oss-120b baseline | `results/benchmark_v2_gptoss120b_100_baseline_20260525_201648/` |
| gpt-oss-120b adaptive | `results/benchmark_v2_gptoss120b_100_adaptive_20260525_202846/` |
| gpt-oss-20b baseline | `results/benchmark_v2_gptoss20b_100_baseline_20260525_205021/` |
| gpt-oss-20b adaptive | `results/benchmark_v2_gptoss20b_100_adaptive_20260525_210036/` |
| gpt-oss-20b deep | `results/benchmark_v2_gptoss20b_100_deep_merged/` (via `scripts/merge_gptoss20b_deep_100.py`) |
| qwen3-coder baseline | `results/benchmark_v2_qwen3coder_100_baseline_20260529_085248/` |
| qwen3-coder adaptive | `results/benchmark_v2_qwen3coder_100_adaptive_20260529_090259/` |
| deep (sonnet/haiku/120b/qwen) | §11.1 deep-mode leaderboard run'ları |
