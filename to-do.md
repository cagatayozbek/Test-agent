# To-Do

## ✅ Tamamlananlar

### Altyapı & Konfigürasyon

- [x] **config.yaml / config.py**: model_id, max_turns, timeout_seconds; dallanmasız loader.
- [x] **requirements.txt**: google-generativeai, pydantic, yaml.
- [x] **.env**: GOOGLE_API_KEY güvenli saklama; `source .env` ile yükleme.

### Ajan Grafiği & Prompt'lar

- [x] **agents/agent_graph.yaml**: Baseline (tek LLM) / Agentic (planner→analysis→critic→reflection→executor) statik wiring.
- [x] **prompts/\*.txt**: planner, analysis, critic, reflection, executor prompt dosyaları.
- [x] **prompt_loader.py**: Prompt dosyalarını dict olarak yükler.
- [x] **graph_loader.py**: agent_graph.yaml'ı AgentGraph dataclass'a parse eder.

### Kör Tool Katmanı

- [x] **tools/**init**.py**: run_tests, read_file, read_file_window, list_files, log_event - tamamen kör, yorum/heuristic yok.
- [x] **instrumented_tools.py**: ToolCounter + InstrumentedTools wrapper; her çağrıda sayaç artışı.
- [x] **String→Path dönüşümü**: LLM string path gönderdiğinde otomatik Path'e çevir.
- [x] **Hata yönetimi**: read_file/read_file_window/run_tests FileNotFoundError'da soft error string döner.
- [x] **run_tests varsayılan komut**: `command=None` durumunda `python3 -m pytest -v` çalıştırır.

### Şemalar & Veri Yapıları

- [x] **schemas/**: SemanticHypothesis, EvaluationResult, LogEntry, Summary (pydantic).
- [x] **run_paths.py**: build_run_paths() → root, raw_logs, summary, tool_outputs path'leri.

### Logging & Emitter

- [x] **emitter.py**: stateless emit_log_entry(); append JSONL; exclude_unset/none.
- [x] **runner.py**: iso8601_utc_timestamp(), build_log_entry(), write_summary().

### LLM Client

- [x] **llm_client.py**: GeminiClient - google.generativeai wrapper; complete() ve generate() metotları.
- [x] **JSON mode**: generate_json() metodu ile yapılandırılmış output (response_mime_type).
- [x] **API retry**: DeadlineExceeded ve ResourceExhausted için exponential backoff.

### Orchestrator

- [x] **custom_session.py**: CustomSession - deterministik agent döngüsü; direct LLM call; tool JSON parse; soft error handling.
- [x] **task_loader.py**: TaskContext dataclass; task dosyalarını yükler; prompt context oluşturur.
- [x] **Canlı log çıktısı**: Her agent çağrısı console'a yazılır (emoji + truncated response).
- [x] **Multi-turn execution**: Executor'un birden fazla tool çağırabilmesi (max 5 iterasyon).
- [x] **Task directory awareness**: Tüm tool'lar task dizininde çalışır (read_file, list_files, run_tests).
- [x] **deepagents_session.py**: DeepAgentsSession (DEPRECATED) - non-terminating loop sorunu nedeniyle kullanılmıyor.
- [x] **docs/deepagents_failure.md**: DeepAgents failure case dokümantasyonu.

### CLI & Main

- [x] **main.py**: --task/--run-id/--mode argümanları; paths oluşturma; CustomSession çalıştırma; summary yazma.

### Test Run'ları

- [x] **test1-test8**: Farklı konfigürasyonlarla dummy run'lar; test8 başarılı (summary.json + raw_logs.jsonl).

### Adversarial Toy Benchmark (Milestone A4) ✅

- [x] **evaluation/tasks/misleading_coverage/**: %100 coverage ama VIP+quantity kombinasyonu test edilmemiş.
- [x] **evaluation/tasks/state_dependent_bug/**: logout/reset sonrası stale data kalıyor.
- [x] **evaluation/tasks/indirect_cause/**: Config.timeout_ms=0 kök sebebi, hata üst katmanda görünüyor.
- [x] **metadata.json**: Her task için beklenen davranış, tuzak açıklaması, reproduction steps.

### Run Engine (Milestone A5) ✅

- [x] **evaluation/run_all.py**: Tüm task'ları tek komutla koşan script.
- [x] **Baseline vs Agentic karşılaştırması**: `--mode both` ile her iki modda çalıştırma.
- [x] **runs/<task>/<run_id>/ yapısı**: Tutarlı çıktı organizasyonu.
- [x] **--verbose flag**: Canlı subprocess output gösterimi.

### LLM-Based Evaluation (Milestone A6) ✅

- [x] **evaluation/evaluator.py**: Evaluator class + EvaluationReport dataclass.
- [x] **Soru seti**: bug_identified, overconfidence, reasoning_quality, stopped_appropriately.
- [x] **İstatistik çıkarımı**: avg_score, bugs_found per mode.
- [x] **--evaluate flag**: run_all.py'de otomatik LLM değerlendirmesi.

### Raporlama ✅

- [x] **rapor.md**: Detaylı Türkçe markdown rapor (baseline vs agentic karşılaştırması).
- [x] **evaluation/full_report.json**: Ham JSON sonuçları.

---

## 🔄 Devam Eden / Kısmen Tamamlanan

### Agent Döngüsü Kalitesi

- [x] **Task context passing**: task_loader.py ile task dosyaları agent'lara context olarak geçiriliyor.
- [x] **Agent-to-agent context**: Önceki agent çıktılarını sonraki agent'lara bağlam olarak geçirme. ✅ ConversationHistory class eklendi.
- [x] **Planner→Executor akışı**: Planner'ın önerdiği tool'u executor'a explicit iletme mekanizması. ✅ History üzerinden geçiyor.

### Summary İçeriği

- [x] **Gerçek hipotez çıkarımı**: Analysis agent çıktısından SemanticHypothesis alanlarını parse etme. ✅ JSON mode ile çözüldü.
- [ ] **Evaluation içeriği**: Critic agent çıktısından EvaluationResult çıkarımı.

---

## 📋 Yapılacaklar

### Orta Öncelik

#### 1. Structured Output Parsing ✅

- [x] **JSON mode**: Gemini'den JSON format zorlama (response_mime_type).
- [x] **SemanticHypothesis extraction**: Analysis çıktısından yapılandırılmış hipotez parse.
- [x] **Fallback handling**: Parse başarısız olursa graceful degradation.

#### 2. Multi-turn Execution ✅

- [x] **Iterative tool calls**: Agent'ın birden fazla tool çağrısı yapabilmesi.
- [x] **Loop control**: Max iterations ve early stopping mekanizması.
- [x] **Tool result feedback**: Tool sonucuna göre sonraki adıma karar verme.

### Düşük Öncelik

#### 3. Prompt Tuning (Kısmen Tamamlandı)

- [x] **Tool signature injection**: Her prompt'a available tools listesi ve signature eklendi.
- [x] **Example output**: Beklenen output formatı prompt'lara eklendi.
- [x] **Stop instruction**: "Then STOP" direktifleri güçlendirildi.
- [ ] **Few-shot examples**: Gerçek örnek tool çağrıları ekleme.

#### 4. Observability & Debug

- [x] **Verbose mode**: Canlı console output (emoji + truncated response).
- [x] **Duration tracking**: Her agent call süresini LogEntry'ye ekle (duration_seconds). ✅
- [x] **Token counting**: API kullanım takibi. ✅

#### 5. Dokümantasyon

- [x] **README.md**: Kurulum, kullanım, örnek run talimatları. ✅
- [x] **Architecture diagram**: Agent flow görselleştirmesi (Mermaid). ✅
- [ ] **API reference**: Tool ve session sınıfları için docstring'ler.

#### 6. Paper Hazırlığı (Milestone A7)

- [ ] **Threats to validity**: Model bağımlılığı, prompt sensitivity, LLM-as-judge riski.
- [ ] **Negatif sonuç anlatısı**: "LLM nerede başarısız oldu" analizi.
- [ ] **DeepAgents failure note**: Paper'da routing substrate evaluation açıklaması.

---

## 🐛 Bilinen Sorunlar

1. ~~**tool_call_count = 0**: Executor tool çağrısı soft error verdiğinde sayaç artmıyor.~~ ✅ Düzeltildi
2. ~~**Agent izolasyonu**: Her agent bağımsız çalışıyor; önceki agent context'i görmüyor.~~ ✅ ConversationHistory ile düzeltildi
3. ~~**Planner boş args**: Planner "list_files" dese de executor farklı tool çağırabiliyor.~~ ✅ Context passing ile çözüldü
4. **DeepAgents**: Non-terminating loop - kullanılamaz durumda (docs/deepagents_failure.md).

---

## 📊 Test Sonuçları (1 Ocak 2026 - Context Passing Sonrası)

| Task                | Baseline   | Agentic     |
| ------------------- | ---------- | ----------- |
| misleading_coverage | 1/10 ❌    | 10/10 ✅    |
| state_dependent_bug | 1/10 ❌    | 10/10 ✅    |
| indirect_cause      | 1/10 ❌    | 10/10 ✅    |
| **Ortalama**        | **1.0/10** | **10.0/10** |

**Ana Bulgu:** Context passing sonrası agentic mod %100 bug tespit oranı, baseline %0.

### Önceki Sonuçlar (31 Aralık 2025)

| Task                | Baseline   | Agentic    |
| ------------------- | ---------- | ---------- |
| misleading_coverage | 10/10 ✅   | 10/10 ✅   |
| state_dependent_bug | 10/10 ✅   | 10/10 ✅   |
| indirect_cause      | 1/10 ❌    | 9/10 ✅    |
| **Ortalama**        | **7.0/10** | **9.7/10** |

---

## 📁 Dosya Yapısı

```
Test-agent/
├── agents/agent_graph.yaml      # Agent wiring
├── config.yaml                  # Model config
├── config.py                    # Config loader
├── custom_session.py            # ✅ Ana orchestrator
├── task_loader.py               # ✅ Task context loader
├── deepagents_session.py        # ❌ Deprecated
├── docs/deepagents_failure.md   # Failure case
├── emitter.py                   # JSONL emitter
├── evaluation/                  # ✅ Evaluation framework
│   ├── __init__.py
│   ├── evaluator.py             # LLM-based evaluator
│   ├── run_all.py               # Test runner
│   ├── full_report.json         # Son test sonuçları
│   └── tasks/                   # Adversarial task'lar
│       ├── misleading_coverage/
│       ├── state_dependent_bug/
│       └── indirect_cause/
├── graph_loader.py              # Graph parser
├── instrumented_tools.py        # Tool wrapper
├── llm_client.py                # Gemini client
├── main.py                      # CLI entry
├── prompt_loader.py             # Prompt loader
├── prompts/*.txt                # Agent prompts
├── rapor.md                     # ✅ Evaluation raporu
├── requirements.txt             # Dependencies
├── run_paths.py                 # Path builder
├── runner.py                    # Utilities
├── runs/                        # Run outputs
│   ├── dummy/test*/
│   ├── misleading_coverage/
│   ├── state_dependent_bug/
│   └── indirect_cause/
├── schemas/                     # Pydantic models
├── tools/__init__.py            # Blind tools
└── to-do.md                     # Bu dosya
```

---

_Son güncelleme: 1 Ocak 2026_
