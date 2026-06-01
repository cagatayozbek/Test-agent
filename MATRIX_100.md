# 100-Task BRTR Matrix — baseline × adaptive × deep (9 models)

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
| **phi-4 (14B)** | **66.7%** (200/300) | **67.7%** (203/300) | N/A ‡ | — |
| **llama-3.1-8b** | **64.3%** (193/300) | **68.7%** (206/300) | **17.3%** (52/300) | OpenRouter ◇ |
| **DeepSeek-V3.1** | 85.3% (256/300) | 89.0% (267/300) | **95.0%** (285/300) | OpenRouter ◇ |
| **llama-3.3-70b** | 79.3% (238/300) | 81.3% (244/300) | **34.0%** (102/300) | OpenRouter ◇ |

**† Sonnet baseline/adaptive timeout-bozulmuş:** bu iki moddaki
başarısızlıkların ~%80'i gerçek test FAIL'i değil, 120s `claude -p`
subprocess timeout'udur (`attempts=0`, `ctok=0`). Timeout düzeltmesiyle
her iki mod ≈ %99'a çıkar; gerçek BRTR sonnet ≥ haiku beklenen sırasını
geri verir (bkz. §14.6).

**‡ phi-4 deep ölçülemez:** phi-4'ün OpenRouter endpoint'lerinin hiçbiri
(NextBit, DeepInfra) function/tool-calling desteklemiyor — deep mode'un
`read_file` tool döngüsü 404 alıyor. 300/300 run `tool_call_count=0`,
sıfır token, hepsi aynı trivial `import source; assert source is not None`
fallback stub'ı (buggy ve fixed'de PASS → BRTR 0). Bu bir sağlayıcı
kısıtıdır, modelin akıl yürütme çöküşü **değildir** (gpt-oss-20b deep'in
236 gerçek FAIL'inden farklı), bu yüzden N/A olarak işaretlenmiştir.
Ek olarak deep path, model id'de "/" görünce config'i yok sayıp
`TOGETHER_API_KEY`'e yönleniyor (bkz. ◇); phi-4 Together'da da yok, yani
çift sebeple ölçülemez (bkz. §15.3).

**◇ Deep mode routing düzeltmesi:** `_resolve_deep_model_name`, model id'de
"/" görünce config'in `base_url`/`api_key_env`'ini **yok sayıp** ortamdaki
`TOGETHER_API_KEY`'e yönlendiriyor (OpenAI-compat deep client `OPENAI_API_KEY`
+ `DEEPTEST_OPENAI_BASE_URL` env'lerini okur, config'i değil). OpenRouter
modellerini deep'te koşmak için run'dan önce
`OPENAI_API_KEY=$OPENROUTER_API_KEY` ve
`DEEPTEST_OPENAI_BASE_URL=https://openrouter.ai/api/v1` set edilir; aksi
halde Together'a yanlış slug gider → 404 → 0-token stub. llama-3.1-8b deep
bu override ile koşuldu (300/300 run, 289'u tool çağırdı; 8'i network
kopması nedeniyle 0-token).

**llama-3.1-8b okunuşu:** baseline/adaptive zayıf bantta (64–69%, tavanı
kırar), adaptive +4.4pp (CI'lar örtüşür, kesin değil); **deep çöküyor
(17.3%)** — model tool çağırıyor (289/300) ama agentic protokolü
beceremiyor. gpt-oss-20b deep çöküşünü (0.213) **ikinci zayıf modelle ve
gerçek ölçümle** bağımsız doğrular.

## Wilson %95 güven aralıkları

| Model | baseline CI | adaptive CI | deep CI |
|---|---|---|---|
| sonnet | [91.1, 96.4] | [90.7, 96.2] | [98.7, 100.0] |
| haiku | [95.7, 99.1] | [97.1, 99.7] | [97.1, 99.7] |
| gpt-oss-120b | [95.3, 98.9] | [95.7, 99.1] | [85.7, 92.6] |
| qwen3-coder-next | [85.0, 92.1] | [82.7, 90.3] | [77.6, 86.2] |
| gpt-oss-20b | [90.7, 96.2] | [91.9, 97.0] | [17.1, 26.3] |
| phi-4 (14B) | [61.2, 71.8] | [62.2, 72.7] | N/A ‡ |
| llama-3.1-8b | [58.8, 69.5] | [63.2, 73.7] | [13.5, 22.0] |
| DeepSeek-V3.1 | [80.9, 88.9] | [85.0, 92.1] | [91.9, 97.0] |
| llama-3.3-70b | [74.4, 83.5] | [76.5, 85.3] | [28.9, 39.5] |

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
- **En zayıf (phi-4, 14B):** baseline 0.667 — spektrumun alt ucu, tavanı net
  kırar. adaptive 0.677 **nötr** (+1pp, CI'lar tamamen örtüşür) ama ctok
  254→377 (+%48). Analiz, en zayıf modeli bile yukarı taşıyamıyor — token
  harcayıp sıfır BRTR kazandırıyor. (deep ölçülemedi, bkz. ‡)
- **En zayıf (llama-3.1-8b):** baseline 0.643 — phi-4 ile birlikte alt uç.
  adaptive 0.687 (+4.4pp, CI'lar örtüşür → kesin değil ama hafif pozitif).
  **deep çöküyor (0.173)** — model tool çağırıyor (289/300) ama agentic
  protokolü beceremiyor. gpt-oss-20b deep çöküşünü (0.213) **ikinci zayıf
  modelle ve gerçek ölçümle** bağımsız doğrular: zorunlu tool döngüsü
  (deep), zayıf modeli baseline'a göre ~3.7× kötüleştiriyor. (300 run'ın
  8'i network kopması artefaktı = 0-token; gerçek payda ~292, BRTR≈0.178 —
  fark ihmal edilebilir.)

- **Güçlü, tavanda değil (DeepSeek-V3.1):** **monoton fayda** —
  baseline 0.853 < adaptive 0.890 < **deep 0.950**, analiz dozuyla doğru
  orantılı. Üstelik deep CI'ı [91.9, 97.0], baseline CI'ı [80.9, 88.9]'un
  tamamen **üstünde** (örtüşmez) → deep, baseline'dan **istatistiksel olarak
  anlamlı** şekilde iyi. Tezin en net pozitif kanıtı: oynayacak yeri olan
  yetenekli bir modelde analiz açıkça yardım ediyor. (300/300, sıfır
  zero-token, hepsi tool çağırdı.)

- **Güçlü ama tool-beceriksiz (llama-3.3-70b):** baseline 0.793 (8B
  kardeşinin 0.643'ünden +15pp — aile içi ölçek etkisi net). adaptive +2pp
  (nötr). **deep çöküyor (0.340)** — 70B bile, oynayacak yeri olmasına
  rağmen (0.793) agentic protokolü beceremiyor. Llama ailesi deep'te
  **bedenden bağımsız** çöküyor (8B −47pp, 70B −45pp). **Kritik kontrast:**
  benzer baseline'lı DeepSeek-V3.1 (0.853) deep'te **0.950'ye çıkarken**,
  llama-3.3-70b (0.793) deep'te **0.340'a düşüyor** → baseline kapasitesi
  deep sonucunu öngörmüyor; belirleyici **tool-sürme/agentic beceri**.

**Tek satır sonuç:** Analiz adımının işareti modele bağlıdır. İki uç:
yetenekli-ama-doymamış modelde **monoton fayda** (DeepSeek-V3.1: deep 0.950
> baseline 0.853, anlamlı; sonnet deep 1.000) ↔ zayıf modelde **deep
felaket** (gpt-oss-20b 0.213, llama-3.1-8b 0.173). Arada tavan etkisi
(haiku), hafif/monoton zarar (gpt-oss-120b, qwen). Model kapasitesi baskın
değişkendir; ama "daha güçlü = daha çok fayda" basit değil. Asıl belirleyici
**agentic/tool-sürme becerisi**: benzer baseline'lı iki model deep'te taban
tabana ayrışıyor (DeepSeek 0.853→0.950 kazanır ↔ llama-3.3-70b 0.793→0.340
çöker). Llama ailesi (8B ve 70B) tool çağırıyor ama protokolü beceremiyor;
DeepSeek ustaca sürüyor. Analiz, model hem doymamış hem de agentic loop'u
becerikli sürebiliyorsa yardım eder; aksi halde (beceriksiz tool-sürme)
büyük model bile çöker.

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
| phi-4 baseline | `results/benchmark_v2_phi4_100_baseline_20260531_132254/` |
| phi-4 adaptive | `results/benchmark_v2_phi4_100_adaptive_20260531_133215/` |
| phi-4 deep (artefakt) | `results/benchmark_v2_phi4_100_deep_20260531_142054/` (300 run, hepsi 404→stub; N/A) |
| llama-3.1-8b baseline | `results/benchmark_v2_llama31_8b_100_baseline_20260531_194231/` |
| llama-3.1-8b adaptive | `results/benchmark_v2_llama31_8b_100_adaptive_20260531_201622/` |
| llama-3.1-8b deep | `results/benchmark_v2_llama31_8b_100_deep_20260531_194639/` (300 run, OpenRouter override; 289/300 tool çağırdı) |
| DeepSeek-V3.1 baseline | `results/benchmark_v2_deepseekv31_100_baseline_*/` |
| DeepSeek-V3.1 adaptive | `results/benchmark_v2_deepseekv31_100_adaptive_*/` |
| DeepSeek-V3.1 deep | `results/benchmark_v2_deepseekv31_100_deep_20260601_075443/` (300 run, OpenRouter override; 300/300 tool çağırdı, sıfır zero-token) |
| llama-3.3-70b baseline | `results/benchmark_v2_llama33_70b_100_baseline_*/` |
| llama-3.3-70b adaptive | `results/benchmark_v2_llama33_70b_100_adaptive_*/` |
| llama-3.3-70b deep | `results/benchmark_v2_llama33_70b_100_deep_20260601_094951/` (300 run, OpenRouter override; 300/300 tool çağırdı, sıfır zero-token) |
| deep (sonnet/haiku/120b/qwen) | §11.1 deep-mode leaderboard run'ları |
