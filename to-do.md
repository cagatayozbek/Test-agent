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
- [x] **Evaluation içeriği**: Critic agent çıktısından EvaluationResult çıkarımı. ✅ JSON mode ile çözüldü.

---

## 📋 Yapılacaklar

### Orta Öncelik

#### 1. Structured Output Parsing ✅

- [x] **JSON mode**: Gemini'den JSON format zorlama (response_mime_type).
- [x] **SemanticHypothesis extraction**: Analysis çıktısından yapılandırılmış hipotez parse.
- [x] **Fallback handling**: Parse başarısız olursa graceful degradation.
- [x] **Pydantic schema enforcement**: API seviyesinde response_schema ile şema zorlama. ✅
- [x] **CriticResponse model**: Critic için genişletilmiş Pydantic model + to_evaluation_result() dönüşümü. ✅

#### 2. Multi-turn Execution ✅

- [x] **Iterative tool calls**: Agent'ın birden fazla tool çağrısı yapabilmesi.
- [x] **Loop control**: Max iterations ve early stopping mekanizması.
- [x] **Tool result feedback**: Tool sonucuna göre sonraki adıma karar verme.

### Düşük Öncelik

#### 3. Prompt Tuning ✅

- [x] **Tool signature injection**: Her prompt'a available tools listesi ve signature eklendi.
- [x] **Example output**: Beklenen output formatı prompt'lara eklendi.
- [x] **Stop instruction**: "Then STOP" direktifleri güçlendirildi.
- [x] **Few-shot examples**: Gerçek örnek tool çağrıları eklendi (executor, planner, analysis, critic, reflection).

#### 4. Observability & Debug

- [x] **Verbose mode**: Canlı console output (emoji + truncated response).
- [x] **Duration tracking**: Her agent call süresini LogEntry'ye ekle (duration_seconds). ✅
- [x] **Token counting**: API kullanım takibi. ✅

#### 5. Dokümantasyon ✅

- [x] **README.md**: Kurulum, kullanım, örnek run talimatları. ✅
- [x] **Architecture diagram**: Agent flow görselleştirmesi (Mermaid). ✅
- [x] **API reference**: Tool ve session sınıfları için kapsamlı docstring'ler eklendi.
  - tools/**init**.py: run_tests, read_file, read_file_window, list_files, log_event
  - instrumented_tools.py: ToolCounter, InstrumentedTools
  - custom_session.py: CustomSession, ConversationHistory, AgentMessage, RunResult, SummaryBuilder
  - llm_client.py: GeminiClient, LLMResponse
  - task_loader.py: TaskContext, load_task_context
  - emitter.py: emit_log_entry
  - runner.py: iso8601_utc_timestamp, build_log_entry, write_summary
  - schemas/models.py: SemanticHypothesis, EvaluationResult, CriticResponse, TokenUsage, LogEntry, Summary

### GitHub ✅

- [x] **.gitignore**: runs/, .env, **pycache** vb. hariç tutma.
- [x] **Initial commit**: 45 dosya commit edildi.
- [x] **Push to GitHub**: https://github.com/cagatayozbek/Test-agent ✅

---

### 🧪 Test Generation Pipeline (Milestone A8)

#### 8.1 Agent Mimarisi Genişletmesi

- [x] **TestWriter agent eklenmesi**: agents/agent_graph.yaml'a testwriter eklendi ✅
- [x] **Agentic mode akışı**: planner → analysis → testwriter → critic → reflection → executor ✅
- [x] **Baseline mode**: Tek testwriter agent (sadece test generation) ✅
- [x] **prompts/testwriter.txt**: pytest odaklı prompt, net çıktı formatı ✅

#### 8.2 Test Dosyası Üretimi & Yönetimi

- [x] **Generated test path standardizasyonu**: `runs/<task>/<run_id>/generated_tests/` ✅
- [x] **write_test_file tool**: tools/**init**.py + instrumented_tools.py ✅
- [x] **Executor desteği**: custom_session.py tool_map + prompts güncellemesi ✅
- [x] **Test isolation**: attempt parametresi ile ayrı dosya adlandırma ✅

#### 8.3 Bug-Revealing Test Doğrulama Döngüsü

- [x] **TaskContextV2**: task_loader.py'de buggy/fixed desteği ✅
- [x] **run_test_on_both_versions()**: Test dosyasını iki ortamda çalıştırma ✅
- [x] **is_bug_revealing logic**: `buggy_failed AND fixed_passed` ✅
- [x] **Config retry ayarları**: `max_retry_attempts`, `test_timeout_seconds` ✅
- [x] **Retry mekanizması**: Başarısızsa Reflection → TestWriter → yeniden üretim ✅

#### 8.4 Yeni Metrikler & Summary Genişletmesi

- [x] **TestGenerationResult model**: attempt, test_file, buggy_failed, fixed_passed, is_bug_revealing ✅
- [x] **TestGenerationSummary model**: tests_generated, attempts_until_success, overfitting_detected, test_results ✅
- [x] **BRTR hesaplama**: calculate_brtr() metodu ✅
- [x] **schemas/**init**.py**: Export güncellemesi ✅

#### 8.5 Task Yapısı Güncellemesi

- [x] **evaluation/tasks_v2/ klasörü**: Yeni format task'lar için ayrı dizin ✅
- [x] **boundary_threshold task**: VIP eşik boundary bug örneği ✅
- [x] **cache_invalidation task**: State management bug örneği ✅
- [x] **metadata.json formatı**: bug_description, expected_failure_signal, test_hint ✅

#### 8.6 Evaluation & Karşılaştırma

- [x] **run_all.py güncelleme**: `--test-gen` flag, `discover_tasks_v2()`, `run_test_generation_tasks()` ✅
- [x] **BRTR hesaplama**: Task bazlı ve mode bazlı BRTR özeti ✅
- [x] **Validation döngüsü**: `run_test_on_both_versions()` entegrasyonu ✅

#### 8.7 Failure Analysis

- [x] **FailureCategory enum**: success, no_fail, overfit, flaky, wrong_assert, wrong_input, wrong_state ✅
- [x] **classify_failure()**: Validation sonucundan kategori çıkarımı ✅
- [x] **analyze_test_code()**: Statik analiz (syntax, import, weak assert) ✅
- [x] **FailureAnalyzer class**: Record toplama, özet çıkarma, JSON export ✅

#### 8.8 Bug Fixes (1 Ocak 2026) ✅

- [x] **Task directory path bug**: `tasks` → `tasks_v2` dizin düzeltmesi ✅
- [x] **prompt_loader.py**: "testwriter" eksik prompt dosyası sorunu ✅
- [x] **task_loader.py**: Docstring syntax hataları (unterminated string) ✅
- [x] **Baseline mode tool execution**: testwriter output capture eksikliği ✅
- [x] **Executor-pytest path bug**: Test dosyası lokasyonu düzeltmesi ✅
  - `_write_test_file_in_run_dir()`: Test dosyasını `buggy/` dizinine de yaz
  - `_run_tests_in_task_dir()`: Pytest'i `buggy/` dizininde çalıştır
  - TestWriter tool execution: Otomatik write_test_file çalıştırma

---

### 📄 Paper Hazırlığı (Milestone A9)

#### 9.1 Mevcut Analiz

- [ ] **Threats to validity**: Model bağımlılığı, prompt sensitivity, LLM-as-judge riski.
- [ ] **Negatif sonuç anlatısı**: "LLM nerede başarısız oldu" analizi.
- [ ] **DeepAgents failure note**: Paper'da routing substrate evaluation açıklaması.

#### 9.2 Test Generation Ekseni

- [ ] **Problem Definition**: "LLM-based test generation under misleading signals"
- [ ] **Experimental Setup**: Bug-revealing test tanımı, retry allowed test generation
- [ ] **Threats genişletme**: Prompt leakage, overfitting testler, pytest nondeterminism
- [ ] **Key Finding**: Agentic yapıların test generation başarısına etkisi

---

## 🐛 Bilinen Sorunlar

1. ~~**tool_call_count = 0**: Executor tool çağrısı soft error verdiğinde sayaç artmıyor.~~ ✅ Düzeltildi
2. ~~**Agent izolasyonu**: Her agent bağımsız çalışıyor; önceki agent context'i görmüyor.~~ ✅ ConversationHistory ile düzeltildi
3. ~~**Planner boş args**: Planner "list_files" dese de executor farklı tool çağırabiliyor.~~ ✅ Context passing ile çözüldü
4. ~~**DeepAgents**: Non-terminating loop - kullanılamaz durumda.~~ (docs/deepagents_failure.md)
5. ~~**Executor-pytest path bug**: Test dosyaları bulunamıyordu.~~ ✅ 1 Ocak 2026 düzeltildi

---

## 🎯 Yapılacaklar (Kalan İşler)

### Yüksek Öncelik

#### 1. Daha Fazla Test Task'ı

- [ ] **Yeni task'lar ekle**: En az 3-5 farklı bug türü
  - [ ] Off-by-one hatası (farklı varyasyon)
  - [ ] Null/None handling bug
  - [ ] Race condition benzeri durum
  - [ ] Exception handling eksikliği
  - [ ] Type coercion bug
- [ ] **Zorluk çeşitliliği**: Kolay, orta, zor task'lar

#### 2. Retry Mekanizması Test

- [ ] **Retry senaryoları**: BRTR < 100% olan task'lar ile test
- [ ] **Retry context kullanımı**: Önceki hata bilgisinin yeni denemeye etkisi
- [ ] **Max retry analizi**: Kaç deneme yeterli?

### Orta Öncelik

#### 3. İstatistiksel Analiz

- [ ] **Çoklu run**: Her task için 5-10 run (variance analizi)
- [ ] **Token kullanımı karşılaştırması**: Baseline vs Agentic
- [ ] **Süre analizi**: Agent başına ortalama süre

#### 4. Overfitting Tespiti

- [ ] **Overfitting test senaryoları**: Sadece buggy'de fail eden testler oluştur
- [ ] **Overfitting rate hesaplama**: fixed_failed durumlarını say

### Düşük Öncelik (Paper Hazırlığı)

#### 5. Paper Yazımı

- [ ] **Threats to validity**: Model bağımlılığı, prompt sensitivity, LLM-as-judge riski
- [ ] **Negatif sonuç analizi**: "LLM nerede başarısız oldu"
- [ ] **Problem Definition**: "LLM-based test generation under misleading signals"
- [ ] **Key Finding**: Agentic vs baseline karşılaştırması

#### 6. Failure Analysis Genişletme

- [ ] **Başarısız test örnekleri saklama**: Etiketli arşiv
- [ ] **Pattern analizi**: Hangi bug türlerinde LLM zorlanıyor?

---

## 📊 Test Sonuçları

### Bug Detection (1 Ocak 2026 - Context Passing Sonrası)

| Task                | Baseline   | Agentic     |
| ------------------- | ---------- | ----------- |
| misleading_coverage | 1/10 ❌    | 10/10 ✅    |
| state_dependent_bug | 1/10 ❌    | 10/10 ✅    |
| indirect_cause      | 1/10 ❌    | 10/10 ✅    |
| **Ortalama**        | **1.0/10** | **10.0/10** |

**Ana Bulgu:** Context passing sonrası agentic mod %100 bug tespit oranı, baseline %0.

### Test Generation - BRTR (1 Ocak 2026) ✅

| Task               | Baseline BRTR | Agentic BRTR | Avg Attempts |
| ------------------ | ------------- | ------------ | ------------ |
| cache_invalidation | 100%          | 100%         | 1.0          |
| boundary_threshold | 100%          | 100%         | 1.0          |
| **Ortalama**       | **100%**      | **100%**     | **1.0**      |

**Ana Bulgu:** Her iki modda da %100 BRTR, ilk denemede başarı.

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
│   ├── tasks/                   # Adversarial task'lar (v1)
│   │   ├── misleading_coverage/
│   │   ├── state_dependent_bug/
│   │   └── indirect_cause/
│   └── tasks_v2/                # 🆕 Test generation task'ları
│       └── <task>/
│           ├── buggy/source.py
│           ├── fixed/source.py
│           └── metadata.json
├── generated_tests/             # 🆕 Üretilen testler
│   └── test_generated_<n>.py
├── graph_loader.py              # Graph parser
├── instrumented_tools.py        # Tool wrapper
├── llm_client.py                # Gemini client
├── main.py                      # CLI entry
├── prompt_loader.py             # Prompt loader
├── prompts/*.txt                # Agent prompts (+ testwriter.txt)
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
├── .gitignore                   # Git ignore rules
└── to-do.md                     # Bu dosya
```

---

_Son güncelleme: 1 Ocak 2026 (Bug fixes + BRTR sonuçları eklendi)_
