# BugsInPy × {baseline, adaptive, deep} × {Claude, OSS} — Pilot Raporu

**Bağlam.** Test-agent'ın mevcut `baseline` ve `adaptive` modlarına ek olarak,
deep-test'in kendi yazdığımız ReAct orchestrator'ı (langchain'siz) `deep` mod
olarak entegre edildi. 100 BugsInPy bug'ı `tasks_v2_bugsinpy/` altına çıkarıldı.

## Mimari

```
Test-agent/
├── bugtest/
│   ├── agents/
│   │   ├── analyzer.py       (mevcut — adaptive için)
│   │   ├── test_writer.py    (mevcut — baseline/adaptive için)
│   │   └── deep_agent.py     (YENİ — DeepTestOrchestrator wrapper)
│   ├── deep/                 (YENİ — deep-test/src/deeptest port)
│   │   ├── agent.py            minimal ReAct loop
│   │   ├── orchestrator.py     DeepTestOrchestrator + system promptlar
│   │   ├── llm.py              multi-provider LLMClient
│   │   │                       (claude_cli, nvidia, anthropic, openai)
│   │   ├── tools.py            tool registry / OpenAI function-call schema
│   │   ├── builtin_tools.py    read_file, ls, run_tests, safe_edit_file,
│   │   │                       analyze_project, search_workspace,
│   │   │                       save_knowledge
│   │   ├── runner.py           pytest + coverage subprocess
│   │   ├── editor.py           SafeEditor (validate-and-revert)
│   │   ├── test_file_policy.py
│   │   ├── types.py
│   │   ├── config.py           settings shim
│   │   └── analysis/           ProjectModel, DependencyGraph
│   ├── pipeline.py             baseline/agentic/adaptive/deep dispatch
│   ├── experiment.py           batch runner + Wilson CI istatistikleri
│   ├── llm.py                  Claude CLI / Gemini / NVIDIA istemcileri
│   └── validator.py            deterministic pytest-based bug-revealing kontrol
├── evaluation/
│   ├── tasks_v2/               12 hand-curated task (5 BugsInPy mini-repro + 7)
│   └── tasks_v2_bugsinpy/      100 auto-extracted BugsInPy task
└── run_pilot_all.py            multi-model pilot launcher
```

### Deep mode workflow (DeepTestOrchestrator)

1. Geçici workspace kur:
   - `source.py` ← task'ın `buggy/source.py` kopyası
   - `tests/test_benchmark.py` ← baseline import test
2. Orchestrator'ı çalıştır (max_steps=8, timeout=180s).  
   Agent şu tool'ları kullanır: `read_file`, `ls`, `run_tests`, `safe_edit_file`.
3. Agent `safe_edit_file` ile bug-revealing testi `tests/test_benchmark.py`'a
   ekler (`allow_bug_revealing=true`).
4. Test dosyası `Validator` ile **buggy/** ve **fixed/** klasörlerinde ayrı
   ayrı çalıştırılır. Bug-revealing := `buggy_passed=False` ∧ `fixed_passed=True`.

## Veri seti

100 BugsInPy bug'ı `tasks_v2_bugsinpy/` altında. Extractor:
1. `_bugsinpy/projects/<proj>/bugs/<n>/bug_patch.txt`'den değişen .py dosyasını bul.
2. `raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>` ile buggy ve
   fixed commitlerinin tam dosyalarını çek.
3. `from .x import y` / `from <proj>.x import y` gibi import'ları stub class
   ile değiştir (`source.py` standalone yüklenebilsin diye).
4. `ast.parse` ile sözdizim kontrolü → kabul.

Filtreler: ≤3 değişen .py dosyası, ≤2000 satır, sözdizim geçerli.

**Bilinen sınırlama.** Stub'lı import'lar bug davranışını silebiliyor (helper'a
delege eden fonksiyonlarda buggy ≈ fixed). Bu, tüm modlar için ortak zorluk
olduğundan modlar arası RELATİF karşılaştırma geçerli.

## Pilot konfigürasyonu (v3 — final)

| Parametre | Değer |
|---|---|
| Task sayısı | **100** (full BugsInPy auto-extracted set, smallest-first) |
| Mod | baseline, adaptive, deep (deep artık critic outer-loop ile) |
| Model | önce **sonnet** (claude-sonnet-4-6); bittikten sonra opus (claude-opus-4-7) → OSS |
| Run/task | **3** (Wilson 95% CI sıkı olsun) |
| max_attempts | **3** (her modun retry/outer-loop budget'ı) |
| Claude CLI timeout | **600s** (300s'de timeout sıklığı yüksekti) |
| Toplam run (sonnet) | 100 × 3 × 3 = **900 invocation** |
| Tahmini süre (sonnet) | ~3-5 gün kesintisiz |
| Mac uyumasın | `caffeinate -i` |
| Terminal-resilient | `nohup` + log |
| Log | `/tmp/pilot_sonnet_v600.log` |

### Restart geçmişi

| Versiyon | timeout | Sebep | Sonuç |
|---|---|---|---|
| v1 | 300s | İlk launch | PySnooper_1'de 1 timeout, restart |
| v2-v5 | 600s | Resume + sleep + limit-detect + log/tmp in-tree | Küçük tasklarda iyi, büyük tasklarda timeout fırtınası |
| **v6** | **900s** | ansible_1 (1226L) ve PySnooper_2 (394L) timeout pattern'i | Aktif |

**Şu ana kadar tamamlanan tasklar (sonnet, max_attempts=3):**
| Task | Lines | baseline | adaptive | deep | Toplam OK |
|---|---|---|---|---|---|
| PySnooper_1 | 54 | 1/3 | 2/3 | 2/3 | 5/9 |
| PySnooper_2 | 394 | 0/3 (3 timeout) | 0/3 (3 timeout) | 0/3 (FAIL) | 0/9 |
| PySnooper_3 | 77 | 3/3 | 3/3 | 1/3 | 7/9 |
| ansible_1 | 1226 | 0/2 (2 timeout) | 1+ OK | 1 FAIL | kısmi |

## Maliyet metodolojisi

Her run için kaydedilen alanlar:
- `prompt_tokens_total`, `completion_tokens_total`: Claude CLI artık
  `--output-format json` ile çağrıldığı için input+cache_read+cache_creation
  ve output token'ları gerçek değerlerle gelir; NVIDIA için openai SDK usage
  alanından okunur.
- `duration_seconds`: pipeline.py wall-clock (LLM + validator dahil).
- `est_cost_usd = (p * in_price + c * out_price) / 1e6` — `bugtest/cost.py`
  tablosundan model bazında. Claude için Anthropic public list price
  (sonnet $3/$15, opus $15/$75); NVIDIA OSS modeller için nominal compute-eq
  (gpt-oss-120b $0.15/$0.60, llama-4-maverick $0.20/$0.60). User'ın Max
  aboneliği maliyeti API list price'tan farklı olabilir; bu rakamlar
  "compute weight" karşılaştırması için.

## v1 sonuç (early kill)

İlk `thefuck_10` üzerinde sonnet:
- baseline → OK 347.9s (2 attempt)
- adaptive → OK 300.1s (2 attempt)
- deep → FAIL 86.0s (1 attempt) → **bug**: deep wrapper Claude CLI'a
  `--add-dir` flag'i pas etmiyor, claude'un Read/Edit araçları workspace'i
  göremiyor, test eklenemiyor. **Düzeltildi.**

## v2 düzeltmeleri (uygulandı, yeniden başlıyor)

1. `bugtest/deep/llm.py:_call_claude_cli` artık `--add-dir <workspace>` ve
   `--output-format json` kullanıyor → Claude CLI workspace dosyalarına
   erişiyor + token sayısı dönüyor.
2. `bugtest/llm.py:ClaudeCodeClient.generate` (baseline/adaptive için kullanılan)
   de `--output-format json` ile çalışıyor → her run için token sayısı kayda
   geçiyor.
3. `bugtest/cost.py` eklendi → per-call USD tahmini.
4. `ModeStats` modeli ve `experiment.py` agregasyonu cost alanlarıyla
   genişletildi (`total_cost_usd`, `avg_cost_per_run_usd`, `avg_cost_per_success_usd`).
5. `aggregate_pilot.py` raporuna 5 yeni sütun (Total Tokens, Total Dur, Total $,
   $/run, $/OK).

Smoke kontrol (`tqdm` task, sonnet deep mode):
- step=1, status=completed
- tokens p=97,341 c=1,760
- est cost = **$0.318** (1 görevin sonnet deep mode maliyeti)
- bug-revealing test eklendi, validation OK

## Pilot v2 — canlı sonuçlar

| # | Model | Task | Mode | Sonuç | Süre | Tokens | $ | Notlar |
|---|---|---|---|---|---|---|---|---|
| 1 | sonnet | bugsinpy_thefuck_10 | baseline | FAIL | 263.9s (2 atm) | (run dosyasında) | — | Doğru bug bulundu ama stubified `replace_argument` helper test'i her iki tarafta fail ettiriyor |
| 2 | sonnet | bugsinpy_thefuck_10 | adaptive | FAIL | 303.5s (2 atm) | — | — | Aynı kök neden — stub'lı helper |
| 3 | sonnet | bugsinpy_thefuck_10 | deep | FAIL | 158.8s (1 atm) | — | — | --add-dir fix sonrası tek shot, yine stub helper |

## Mode toplam (pilot tamamlandıkça)

| Model | Mode | BRTR | 95% CI | OK/Total | Avg Tokens | Avg Dur | Total $ | $/OK |
|---|---|---|---|---|---|---|---|---|
| - | - | - | - | - | - | - | - | - |

## Notlar / sürpriz bulgular

- v1 deep mode `--add-dir` eksikti — fixed.
- Sonnet deep tek shot ortalama ~$0.30/run (97k input → cache hit'le maliyet
  düşer, sonraki run'larda görülecek).
