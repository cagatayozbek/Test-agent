# Test Generation Pipeline (A8) - Uygulama Raporu

**Tarih:** 1 Ocak 2026  
**Milestone:** A8 - Test Generation Pipeline  
**Durum:** ✅ Tamamlandı

---

## 📋 Özet

Bug detection odaklı mevcut sisteme **test generation** kapasitesi eklendi. Yeni sistem, LLM'in bug-revealing testler yazmasını, bu testleri hem buggy hem fixed kod üzerinde doğrulamasını ve sonuçları BRTR (Bug-Revealing Test Rate) metriği ile değerlendirmesini sağlıyor.

---

## 🔧 Yapılan Değişiklikler

### 1. Agent Mimarisi Genişletmesi

#### `agents/agent_graph.yaml`

```yaml
# Önceki agentic akış:
# planner → analysis → critic → reflection → executor

# Yeni agentic akış:
planner → analysis → testwriter → critic → reflection → executor
# Baseline modu değişikliği:
# Önceki: executor (tek agent)
# Yeni: testwriter (tek agent - sadece test generation)
```

#### `prompts/testwriter.txt` (YENİ)

- pytest odaklı bug-revealing test prompt'u
- JSON output formatı: `tool`, `args`, `test_metadata`
- Few-shot örnekler: boundary bug, cache invalidation bug
- Kritik gereksinimler: "Test MUST FAIL on buggy, MUST PASS on fixed"

---

### 2. Test Dosyası Yönetimi

#### `tools/__init__.py`

```python
# Yeni fonksiyon eklendi:
def write_test_file(
    output_dir: Path,
    filename: str,
    content: str,
    attempt: int = 1
) -> dict[str, Any]:
    """Write a generated test file to the output directory."""
```

**Özellikler:**

- Otomatik dizin oluşturma (`mkdir -p` davranışı)
- Attempt-based isolation: `test_generated_attempt_2.py`
- UTF-8 encoding
- Soft error handling (exception yerine dict dönüşü)

#### `instrumented_tools.py`

- `write_test_file()` wrapper eklendi
- String-to-Path dönüşümü
- Counter increment entegrasyonu

#### `run_paths.py`

```python
@dataclass
class RunPaths:
    root: Path
    raw_logs: Path
    summary: Path
    tool_outputs: Path
    generated_tests: Path  # YENİ
```

#### `custom_session.py`

- `tool_map`'e `write_test_file` eklendi
- `_write_test_file_in_run_dir()` metodu: Test dosyalarını run dizinine yazar

#### `prompts/executor.txt`

- `write_test_file` tool dokümantasyonu eklendi
- Few-shot örnek eklendi

---

### 3. Bug-Revealing Test Doğrulama Döngüsü

#### `task_loader.py`

**Yeni class: `TaskContextV2`**

```python
@dataclass
class TaskContextV2:
    task_id: str
    buggy_code: str      # Agent'a gösterilir
    fixed_code: str      # Sadece validation için
    metadata: dict
    buggy_path: Path
    fixed_path: Path
```

**Yeni fonksiyon: `run_test_on_both_versions()`**

```python
def run_test_on_both_versions(
    test_file_path: Path,
    buggy_dir: Path,
    fixed_dir: Path,
    timeout: int = 60
) -> dict:
    """
    Returns:
        buggy_failed: bool
        fixed_passed: bool
        is_bug_revealing: buggy_failed AND fixed_passed
    """
```

#### `config.yaml`

```yaml
# Yeni ayarlar:
test_generation:
  max_retry_attempts: 3
  test_timeout_seconds: 60
```

---

### 4. Schema Genişletmesi

#### `schemas/models.py`

**Yeni model: `TestGenerationResult`**

```python
class TestGenerationResult(BaseModel):
    attempt: int
    test_file: str
    buggy_failed: bool
    fixed_passed: bool
    is_bug_revealing: bool
    buggy_output: str = ""
    fixed_output: str = ""
```

**Yeni model: `TestGenerationSummary`**

```python
class TestGenerationSummary(BaseModel):
    # Base fields
    hypothesis: SemanticHypothesis | None
    evaluation: EvaluationResult | None
    model_id: str
    timestamp: str
    tool_call_count: int

    # Test generation fields
    task_id: str
    mode: Literal["baseline", "agentic"]
    tests_generated: int
    attempts_until_success: int | None
    buggy_failed: bool
    fixed_passed: bool
    is_bug_revealing: bool
    overfitting_detected: bool
    test_results: list[TestGenerationResult]

    def calculate_brtr(self) -> float:
        """Bug-Revealing Test Rate: 1.0 if success, 0.0 otherwise"""
```

#### `schemas/__init__.py`

- `TestGenerationResult` ve `TestGenerationSummary` export'ları eklendi

---

### 5. Task Yapısı v2

#### Yeni dizin yapısı: `evaluation/tasks_v2/`

```
evaluation/tasks_v2/
├── boundary_threshold/
│   ├── buggy/
│   │   └── source.py      # > yerine >= kullanılmalı
│   ├── fixed/
│   │   └── source.py      # >= doğru kullanım
│   └── metadata.json
└── cache_invalidation/
    ├── buggy/
    │   └── source.py      # logout() cache temizlemiyor
    ├── fixed/
    │   └── source.py      # logout() cache.clear() çağırıyor
    └── metadata.json
```

#### Örnek `metadata.json` formatı:

```json
{
  "task_id": "boundary_threshold",
  "title": "VIP Threshold Boundary Bug",
  "bug_type": "boundary_condition",
  "bug_description": "Uses > instead of >= for threshold check",
  "bug_location": {
    "file": "source.py",
    "function": "calculate_discount",
    "line": 35
  },
  "expected_failure_signal": "AssertionError on boundary value",
  "test_hint": "Test with exactly LOYALTY_THRESHOLD points"
}
```

---

### 6. Evaluation Güncellemesi

#### `evaluation/run_all.py`

**Yeni fonksiyon: `discover_tasks_v2()`**

```python
def discover_tasks_v2(tasks_dir: Path) -> list[str]:
    """evaluation/tasks_v2/ altındaki test generation task'larını bul."""
```

**Yeni fonksiyon: `run_test_generation_tasks()`**

```python
def run_test_generation_tasks(...) -> dict:
    """
    1. Agent'ı çalıştır (test üret)
    2. Generated test'i bul
    3. Buggy ve fixed üzerinde çalıştır
    4. BRTR hesapla
    """
```

**Yeni CLI flag:**

```bash
python evaluation/run_all.py --test-gen --mode both
```

**Output formatı:**

```json
{
  "evaluation_type": "test_generation",
  "results": [...],
  "brtr_summary": {
    "baseline": 0.5,
    "agentic": 0.8
  }
}
```

---

### 7. Failure Analysis

#### `evaluation/failure_analyzer.py` (YENİ)

**FailureCategory enum:**
| Kategori | Açıklama |
|----------|----------|
| `success` | Bug-revealing test (buggy fail, fixed pass) |
| `no_fail` | Test buggy kod'da pass ediyor |
| `overfit` | Test her iki versiyonda da fail |
| `flaky` | Non-deterministic sonuçlar |
| `wrong_assert` | Assertion yanlış davranışı hedefliyor |
| `wrong_input` | Input bug'ı tetiklemiyor |
| `wrong_state` | Setup bug durumunu oluşturmuyor |

**Ana fonksiyonlar:**

```python
def classify_failure(buggy_failed, fixed_passed, ...) -> FailureCategory
def analyze_test_code(test_content: str) -> Optional[FailureCategory]
def analyze_pytest_output(output: str) -> dict
```

**FailureAnalyzer class:**

```python
analyzer = FailureAnalyzer()
analyzer.add_record(task_id, attempt, test_file, ...)
analyzer.get_summary()  # {"success": 3, "no_fail": 2, ...}
analyzer.save_analysis(Path("failures.json"))
analyzer.print_summary()
```

---

## 📊 Değişiklik Özeti

| Dosya                                     | Değişiklik Tipi | Satır Değişikliği |
| ----------------------------------------- | --------------- | ----------------- |
| `agents/agent_graph.yaml`                 | Güncelleme      | +3 satır          |
| `prompts/testwriter.txt`                  | Yeni dosya      | ~100 satır        |
| `prompts/executor.txt`                    | Güncelleme      | +5 satır          |
| `tools/__init__.py`                       | Güncelleme      | +70 satır         |
| `instrumented_tools.py`                   | Güncelleme      | +30 satır         |
| `run_paths.py`                            | Güncelleme      | +2 satır          |
| `custom_session.py`                       | Güncelleme      | +225 satır        |
| `config.py`                               | Güncelleme      | +15 satır         |
| `config.yaml`                             | Güncelleme      | +4 satır          |
| `task_loader.py`                          | Güncelleme      | +150 satır        |
| `schemas/models.py`                       | Güncelleme      | +80 satır         |
| `schemas/__init__.py`                     | Güncelleme      | +10 satır         |
| `evaluation/run_all.py`                   | Güncelleme      | +270 satır        |
| `evaluation/test_evaluator.py`            | Yeni dosya      | ~430 satır        |
| `evaluation/failure_analyzer.py`          | Yeni dosya      | ~300 satır        |
| `evaluation/tasks_v2/boundary_threshold/` | Yeni klasör     | 3 dosya           |
| `evaluation/tasks_v2/cache_invalidation/` | Yeni klasör     | 3 dosya           |

**Toplam:** ~18 dosya, ~1700+ satır yeni/değiştirilmiş kod

---

## 🚀 Kullanım

### Test Generation Modunu Çalıştırma

```bash
# Tüm task'ları her iki modda çalıştır
python evaluation/run_all.py --test-gen --mode both

# Tek task
python evaluation/run_all.py --test-gen --task boundary_threshold --mode agentic

# Verbose output
python evaluation/run_all.py --test-gen --mode both -v
```

### Beklenen Output

```
🧪 Test Generation Mode
Discovered 2 task(s): ['boundary_threshold', 'cache_invalidation']
Modes: ['baseline', 'agentic']
--------------------------------------------------
[boundary_threshold] mode=baseline run_id=baseline_20260101_120000
  🎯 BRTR: buggy_fail=True, fixed_pass=True → bug_revealing=True
  ✓ OK
[boundary_threshold] mode=agentic run_id=agentic_20260101_120030
  🎯 BRTR: buggy_fail=True, fixed_pass=True → bug_revealing=True
  ✓ OK
--------------------------------------------------
Total: 4 | Passed: 4 | Bug-Revealing: 3

📊 BRTR Summary:
  baseline: 50.0%
  agentic: 100.0%
```

---

## 🔮 Sonraki Adımlar

1. **Paper Hazırlığı (A9):** Threats to validity, experimental setup, key findings
2. **Daha fazla task:** Farklı bug türleri için v2 task'lar ekle

### ✅ Tamamlanan Sonraki Adımlar

3. ~~**Retry mekanizması:** Başarısız test generation'da otomatik retry~~ ✅ Eklendi (1 Ocak 2026)
4. ~~**LLM-based failure analysis:** Neden bug-revealing olmadı?~~ ✅ Eklendi

---

## 🆕 Güncelleme: Execution-Based BRTR + LLM Analysis (1 Ocak 2026 - Akşam)

### Mimari Kararı

**BRTR (Bug-Revealing Test Rate)** metriği **execution-based** olmalı:

```
is_bug_revealing = buggy_failed AND fixed_passed
                   ^^^^^^^^^^^^     ^^^^^^^^^^^^
                   pytest exit      pytest exit
                   code != 0        code == 0
```

**Neden?**

- Deterministic ve reproducible
- Reviewer-friendly (execution truth)
- LLM hallucination riski yok
- Paper'da savunması kolay

### LLM'in Rolü: Açıklayıcı, Karar Verici Değil

LLM şimdi **analiz ve açıklama** sağlıyor, BRTR'ı **etkilemiyor**:

| Metric             | Source                          | LLM Etkisi       |
| ------------------ | ------------------------------- | ---------------- |
| `is_bug_revealing` | pytest exit codes               | ❌ Yok           |
| `BRTR`             | count(is_bug_revealing) / total | ❌ Yok           |
| `failure_category` | LLM analysis                    | ✓ Açıklayıcı     |
| `retry_suggestion` | LLM analysis                    | ✓ Öğretici       |
| `commentary`       | LLM analysis                    | ✓ Bilgilendirici |

### Yeni Mimari: TestEvaluator (Açıklayıcı Rol)

#### `evaluation/test_evaluator.py`

```python
class TestEvaluator:
    """LLM-based analyzer for test results (not judge)."""

    def evaluate_test(...) -> TestEvaluationResult:
        """
        Provides analysis and explanation.
        Does NOT determine is_bug_revealing - that's execution-based.
        """
```

**LLM'in sağladığı analiz:**

- `llm_verdict`: LLM'in kendi değerlendirmesi (karşılaştırma için)
- `confidence`: high/medium/low
- `failure_category`: success, no_fail, overfit, wrong_assert, wrong_input, etc.
- `buggy_analysis`: Buggy kod üzerinde ne oldu
- `fixed_analysis`: Fixed kod üzerinde ne oldu
- `why_not_revealing`: Neden bug-revealing değil (eğer değilse)
- `retry_suggestion`: Bir sonraki deneme için öneri
- `test_quality_score`: 1-10 arası kalite puanı

#### `evaluation/run_all.py`

```python
def run_test_generation_tasks(...):
    # BRTR is execution-based (deterministic)
    is_bug_revealing = validation["buggy_failed"] and validation["fixed_passed"]

    # LLM provides analysis (not the verdict)
    eval_result = test_evaluator.evaluate_test(...)

    result["test_validation"] = {
        "is_bug_revealing": is_bug_revealing,  # Execution-based
        "llm_analysis": {
            "llm_verdict": eval_result.is_bug_revealing,  # For comparison
            "failure_category": eval_result.failure_category,
            "commentary": eval_result.commentary,
            ...
        }
    }
```

### Output Formatı

```
[boundary_threshold] mode=agentic run_id=agentic_20260101_120030
  🎯 Execution: buggy_fail=True, fixed_pass=True → bug_revealing=True
     🤖 LLM Analysis: success [high] - Test correctly targets the boundary...
  ✓ OK
```

### Örnek LLM Analysis Output

```json
{
  "llm_verdict": true,
  "confidence": "high",
  "failure_category": "success",
  "buggy_analysis": "Test failed with AssertionError: expected 20% discount but got 0%",
  "fixed_analysis": "Test passed, discount correctly applied at boundary",
  "why_not_revealing": "",
  "retry_suggestion": "",
  "test_quality_score": 9,
  "commentary": "Excellent test - directly targets the >= vs > boundary condition"
}
```

### Retry Feedback Mekanizması

LLM analizi, başarısız denemelerde **öğretici feedback** sağlıyor:

```python
# custom_session.py
class CustomSession:
    def __init__(self, ..., retry_context: str = ""):
        self.retry_context = retry_context  # LLM'den gelen öneri
```

**Akış:**

1. Test execution-based olarak `is_bug_revealing=False` → başarısız
2. LLM analiz eder: "wrong_input - value=50 kullandın ama bug value=100'de"
3. Bu feedback `retry_context` olarak sonraki denemeye geçirilir
4. TestWriter agent bu context'i görür, aynı hatayı tekrarlamaz

### Paper İçin Avantajlar

| Özellik         | Eski (LLM-judge) | Yeni (Execution-based) |
| --------------- | ---------------- | ---------------------- |
| Reproducibility | ❌ LLM'e bağlı   | ✓ Deterministic        |
| Reviewer güveni | "LLM judge?"     | "Execution truth ✓"    |
| Methodology     | Questionable     | Standard               |
| LLM cost        | Her test için    | İsteğe bağlı analiz    |

---

## 🆕 Güncelleme: Retry Mekanizması (1 Ocak 2026 - Gece)

### Motivasyon

İlk test generation denemesi her zaman bug-revealing olmayabilir. LLM'in yanlış input, yanlış assertion veya eksik setup kullanması muhtemel. Retry mekanizması, başarısız denemelerdeki feedback'i kullanarak iteratif iyileştirme sağlıyor.

### Yeni Class'lar

#### `config.py`

```python
class TestGenerationConfig(BaseModel):
    """Configuration for test generation mode."""
    max_retry_attempts: int = 3
    test_timeout_seconds: int = 60


class Config(BaseModel):
    model_id: str
    max_turns: int
    timeout_seconds: int
    test_generation: Optional[TestGenerationConfig] = None
```

#### `custom_session.py`

**Yeni dataclass: `TestGenerationResult`**

```python
@dataclass
class TestGenerationResult:
    """Result from a single test generation attempt."""
    attempt: int
    test_file: Path | None
    test_code: str
    is_bug_revealing: bool
    buggy_failed: bool
    fixed_passed: bool
    evaluation: TestEvaluationResult | None = None
```

**Yeni dataclass: `TestGenerationSessionResult`**

```python
@dataclass
class TestGenerationSessionResult:
    """Final result from test generation session with retries."""
    success: bool
    attempts: int
    results: list[TestGenerationResult]
    final_test_file: Path | None = None
```

**Yeni class: `TestGenerationSession`**

```python
class TestGenerationSession:
    """Session for test generation with retry logic.

    Manages the retry loop:
    1. Run agent pipeline to generate test
    2. Validate test against buggy/fixed code
    3. If not bug-revealing, get feedback from TestEvaluator
    4. Inject feedback as retry_context for next attempt
    5. Run again with improved context
    6. Repeat until success or max retries
    """

    def __init__(
        self,
        graph: AgentGraph,
        mode: str,
        prompts: dict[str, str],
        tools: InstrumentedTools,
        log_path: Path,
        llm: GeminiClient,
        task_context: TaskContextV2,
        test_evaluator: TestEvaluator,
        max_retries: int = 3,
        test_timeout: int = 60,
    ) -> None: ...

    def run(self) -> TestGenerationSessionResult:
        """Run test generation with retry loop."""
```

### Retry Akışı

```
┌─────────────────────────────────────────────────────────────┐
│                    Attempt 1                                 │
├─────────────────────────────────────────────────────────────┤
│  1. Run CustomSession (planner→analysis→testwriter→...)     │
│  2. Find generated test file                                 │
│  3. Validate: run_test_on_both_versions()                   │
│  4. is_bug_revealing? ────────────────────────► SUCCESS ✅  │
│         │ No                                                 │
│         ▼                                                    │
│  5. TestEvaluator.evaluate_test()                           │
│  6. Get retry_context with failure analysis                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Attempt 2                                 │
├─────────────────────────────────────────────────────────────┤
│  1. CustomSession with retry_context injected               │
│     (ConversationHistory.set_retry_context())               │
│  2. TestWriter sees previous failure + suggestion           │
│  3. Generate improved test                                   │
│  4. Validate again...                                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                    (max_retries'a kadar)
```

### Context Injection

Retry context, `ConversationHistory` üzerinden TestWriter agent'a geçiriliyor:

```python
# ConversationHistory.get_context_for_agent()
def get_context_for_agent(self, current_agent: str) -> str:
    context_parts = []

    # Include retry context for testwriter agent
    if current_agent == "testwriter" and self.retry_context:
        context_parts.append(self.retry_context)
        context_parts.append("")

    # ... rest of context building
```

### Retry Context Formatı

```
=== PREVIOUS TEST GENERATION ATTEMPTS ===
Total attempts so far: 2

### Attempt 1
- Result: no_fail
- Bug-Revealing: ✗
- Analysis: Test passed on buggy code - input value=50 doesn't trigger the bug
- Suggestion: Use exactly 100 points (LOYALTY_THRESHOLD) to hit the boundary

### Attempt 2
- Result: wrong_assert
- Bug-Revealing: ✗
- Analysis: Test asserts wrong expected value
- Suggestion: Expected discount is 20%, not 10%

=== USE THIS FEEDBACK TO IMPROVE YOUR TEST ===
```

### CLI Güncellemesi

```bash
# Varsayılan 3 retry ile
python evaluation/run_all.py --test-gen --mode both

# Özel retry sayısı ile
python evaluation/run_all.py --test-gen --mode agentic --max-retries 5
```

### Output Formatı

```
🧪 Test Generation Mode (with retry)
Discovered 2 task(s): ['boundary_threshold', 'cache_invalidation']
Modes: ['baseline', 'agentic']
Max retries: 3
--------------------------------------------------
✓ Config loaded: max_retries=3, timeout=60s

============================================================
[boundary_threshold] mode=agentic run_id=agentic_20260101_180000
Bug: Uses > instead of >= for threshold check...
============================================================

============================================================
🧪 TEST GENERATION ATTEMPT 1/3
============================================================
🤖 [PLANNER] calling LLM...
...
📄 Generated test: test_generated.py
🔬 Validating test...
❌ Validation: buggy_fail=False, fixed_pass=True → bug_revealing=False
🔄 Getting feedback for retry...
   Category: no_fail
   Suggestion: Use boundary value 100 instead of 150...

============================================================
🧪 TEST GENERATION ATTEMPT 2/3
============================================================
📋 Retry context loaded from previous attempts
🤖 [PLANNER] calling LLM...
...
📄 Generated test: test_generated.py
🔬 Validating test...
🎯 Validation: buggy_fail=True, fixed_pass=True → bug_revealing=True
✅ SUCCESS! Bug-revealing test generated on attempt 2

🎯 Final: bug_revealing=True (attempts: 2)

--------------------------------------------------
Total: 4 | Passed: 4 | Bug-Revealing: 4

📊 BRTR Summary:
  baseline: 50.0% (avg attempts: 2.5)
  agentic: 100.0% (avg attempts: 1.5)
```

### Yeni Report Alanları

```json
{
  "evaluation_type": "test_generation",
  "max_retries": 3,
  "results": [
    {
      "task_id": "boundary_threshold",
      "mode": "agentic",
      "success": true,
      "attempts": 2,
      "test_validation": {
        "is_bug_revealing": true,
        "test_file": "runs/.../generated_tests/test_generated.py",
        "attempts_detail": [
          {
            "attempt": 1,
            "buggy_failed": false,
            "fixed_passed": true,
            "is_bug_revealing": false,
            "failure_category": "no_fail"
          },
          {
            "attempt": 2,
            "buggy_failed": true,
            "fixed_passed": true,
            "is_bug_revealing": true,
            "failure_category": "success"
          }
        ]
      }
    }
  ],
  "brtr_summary": {
    "baseline": 0.5,
    "agentic": 1.0
  },
  "attempts_stats": {
    "baseline": {
      "avg_attempts_to_success": 2.5,
      "success_count": 1
    },
    "agentic": {
      "avg_attempts_to_success": 1.5,
      "success_count": 2
    }
  }
}
```

### Değişiklik Özeti (Retry)

| Dosya                   | Değişiklik Tipi | Satır Değişikliği |
| ----------------------- | --------------- | ----------------- |
| `config.py`             | Güncelleme      | +15 satır         |
| `custom_session.py`     | Güncelleme      | +200 satır        |
| `evaluation/run_all.py` | Güncelleme      | +150 satır        |

**Toplam:** ~365 satır yeni kod

---

_Rapor güncelleme tarihi: 1 Ocak 2026 (Gece - Retry Mekanizması)_
