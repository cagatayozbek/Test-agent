# Executor-Pytest Path Bug Düzeltmesi Raporu

**Tarih:** 1 Ocak 2026  
**Durum:** ✅ Tamamlandı  
**Etki:** Kritik - Executor'ın testleri keşfedememesi sorunu çözüldü

---

## 1. Problem Tanımı

### 1.1 Semptom

Executor agent `run_tests` çağırdığında pytest "0 tests collected" hatası veriyordu:

```
============================= test session starts ==============================
collected 0 items
============================= no tests ran =====================================
```

### 1.2 Kök Neden Analizi

**Problem:** Test dosyaları ile kaynak dosyaları farklı dizinlerde bulunuyordu.

```
evaluation/tasks_v2/boundary_threshold/
├── buggy/
│   └── source.py          # Kaynak kod burada
├── fixed/
│   └── source.py
├── generated_tests/       # Testler buraya yazılıyordu (YANLIŞ)
│   └── test_generated.py
└── metadata.json
```

**Sorunlar:**

1. Test dosyası `task_dir/generated_tests/` dizinine yazılıyordu
2. Pytest `task_dir/` dizininde çalışıyordu
3. Test dosyası `from source import ...` yapıyordu ama `source.py` `buggy/` içindeydi
4. Import hatası nedeniyle testler keşfedilemiyordu

### 1.3 İkincil Problem: TestWriter Tool Execution

Agentic modda TestWriter'ın `write_test_file` çağrısı sadece "öneri" olarak kalıyordu, gerçekten execute edilmiyordu. Bu nedenle:

1. TestWriter test dosyası öneriyor (JSON response)
2. Executor ilk iş olarak `run_tests` çağırıyor
3. Test dosyası henüz yazılmadığı için pytest hiçbir test bulamıyordu

---

## 2. Uygulanan Düzeltmeler

### 2.1 Düzeltme 1: Test Dosyası Yazma Lokasyonu

**Dosya:** `custom_session.py`  
**Metod:** `_write_test_file_in_run_dir()`

**Önceki Kod:**

```python
def _write_test_file_in_run_dir(self, output_dir, filename, content, attempt=1):
    # Sadece runs/ dizinine yazıyordu
    run_dir = self.log_path.parent
    target_dir = run_dir / output_dir
    result = self.tools.write_test_file(target_dir, filename, content, attempt)

    # task_dir'e de yazıyordu ama YANLIŞ lokasyona
    if self.task_dir and result.get("success"):
        task_test_path = self.task_dir / filename  # generated_tests/ dizinini görmezden geliyordu
        task_test_path.write_text(content)
    return result
```

**Düzeltilmiş Kod:**

```python
def _write_test_file_in_run_dir(self, output_dir, filename, content, attempt=1):
    """Write generated test file to BOTH run directory AND buggy directory.

    The test file is written to:
    1. runs/<task>/<run_id>/generated_tests/ - for archival
    2. task_dir/buggy/ - for immediate pytest execution (same dir as source.py)
    """
    # Arşiv için runs/ dizinine yaz
    run_dir = self.log_path.parent
    target_dir = run_dir / output_dir
    result = self.tools.write_test_file(target_dir, filename, content, attempt)

    # Pytest keşfi için buggy/ dizinine yaz
    # Testler source.py ile aynı dizinde olmalı ki importlar çalışsın
    if self.task_dir and result.get("success"):
        try:
            buggy_dir = self.task_dir / "buggy"
            if buggy_dir.exists():
                task_test_path = buggy_dir / filename
                task_test_path.write_text(content, encoding="utf-8")
                result["task_dir_path"] = str(task_test_path)
        except Exception as e:
            result["task_dir_error"] = str(e)

    return result
```

**Sonuç Dizin Yapısı:**

```
evaluation/tasks_v2/boundary_threshold/
├── buggy/
│   ├── source.py           # Kaynak kod
│   └── test_generated.py   # Test dosyası (YENİ - aynı dizinde)
├── fixed/
│   └── source.py
└── metadata.json

runs/boundary_threshold/agentic_20260101_xxx/
└── generated_tests/
    └── test_generated.py   # Arşiv kopyası
```

### 2.2 Düzeltme 2: Pytest Çalışma Dizini

**Dosya:** `custom_session.py`  
**Metod:** `_run_tests_in_task_dir()`

**Önceki Kod:**

```python
def _run_tests_in_task_dir(self, command=None, cwd=None):
    if cwd is None and self.task_dir:
        cwd = self.task_dir  # task_dir/ dizininde çalışıyordu
    return self.tools.run_tests(command=command, cwd=cwd)
```

**Düzeltilmiş Kod:**

```python
def _run_tests_in_task_dir(self, command=None, cwd=None):
    """Run tests in the task's buggy directory.

    Tests are run in buggy/ subdirectory where source.py lives,
    so imports work correctly.
    """
    if cwd is None and self.task_dir:
        # buggy/ dizininde çalıştır (source.py ve testlerin bulunduğu yer)
        buggy_dir = self.task_dir / "buggy"
        cwd = buggy_dir if buggy_dir.exists() else self.task_dir
    elif isinstance(cwd, str):
        cwd = self._get_task_path(cwd)
    return self.tools.run_tests(command=command, cwd=cwd)
```

### 2.3 Düzeltme 3: TestWriter Tool Otomatik Execution

**Dosya:** `custom_session.py`  
**Lokasyon:** Agent loop içinde testwriter işleme kısmı

**Önceki Kod:**

```python
if agent_name == "testwriter":
    executor_reply = reply  # Sadece reply'i saklıyordu
```

**Düzeltilmiş Kod:**

```python
if agent_name == "testwriter":
    executor_reply = reply
    # TestWriter'ın tool çağrısını hemen execute et (write_test_file)
    # Bu, test dosyasının Executor'ın run_tests çağrısından ÖNCE oluşturulmasını sağlar
    tool_name, tool_args, tool_result, _ = self._execute_tool_with_continue(reply)
    if tool_name == "write_test_file" and "success" in str(tool_result):
        history.add_tool_result(tool_name, tool_args, tool_result)
        all_tool_results.append(tool_result)
        print(f"✅ TestWriter tool executed: {tool_name}")
        result_preview = str(tool_result)[:200] + "..."
        print(f"📤 Result: {result_preview}")
```

---

## 3. Test Sonuçları

### 3.1 Düzeltme Öncesi

```
🔧 Executing tool (iteration 1/5)...
✅ Tool: run_tests
📤 Result: {'stdout': '... collected 0 items ... no tests ran ...'}
🔄 Continuing investigation...

🔧 Executing tool (iteration 2/5)...
... (executor test dosyasını arıyor)

🔧 Executing tool (iteration 3/5)...
... (executor test dosyasını yeniden yazıyor)

🔧 Executing tool (iteration 4/5)...
... (hala bulamıyor)

🔧 Executing tool (iteration 5/5)...
⚠️ Max iterations (5) reached
```

**Problem:** Executor 5 iterasyona ulaşıyor, testler bulunamıyordu.

### 3.2 Düzeltme Sonrası

```
==================================================
🤖 [TESTWRITER] calling LLM...
📝 Response (2045 chars) in 15.27s
✅ TestWriter tool executed: write_test_file
📤 Result: {'success': True, 'path': '.../generated_tests/test_generated.py',
            'task_dir_path': '.../buggy/test_generated.py'}

==================================================
🤖 [EXECUTOR] calling LLM...
📝 Response: run_tests

==================================================
🔧 Executing tool (iteration 1/5)...
✅ Tool: run_tests
📤 Result: {'stdout': '... collected 1 item ... 1 failed ...'}
🔄 Continuing investigation...

==================================================
🔧 Executing tool (iteration 2/5)...
✅ Tool: log_event
📤 Result: {'message': 'ROOT CAUSE: ...'}
✅ Investigation complete
```

**Sonuç:** Sadece 2 iterasyon kullanıldı (run_tests + log_event).

### 3.3 Final Test Sonuçları

```
📊 BRTR Summary:
  baseline: 100.0% (avg attempts: 1.0)
  agentic: 100.0% (avg attempts: 1.0)

--------------------------------------------------
Total: 4 | Passed: 4 | Bug-Revealing: 4
```

| Task               | Mode     | Sonuç            | İterasyonlar | Attempt |
| ------------------ | -------- | ---------------- | ------------ | ------- |
| cache_invalidation | baseline | ✅ Bug-revealing | 1            | 1       |
| cache_invalidation | agentic  | ✅ Bug-revealing | 2            | 1       |
| boundary_threshold | baseline | ✅ Bug-revealing | 1            | 1       |
| boundary_threshold | agentic  | ✅ Bug-revealing | 2            | 1       |

---

## 4. Teknik Detaylar

### 4.1 Dosya Akışı (Düzeltme Sonrası)

```
TestWriter JSON Response
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ _write_test_file_in_run_dir() otomatik çalışır     │
│                                                     │
│  1. runs/.../generated_tests/test_generated.py     │
│     (arşiv kopyası)                                │
│                                                     │
│  2. task_dir/buggy/test_generated.py               │
│     (pytest keşfi için - source.py ile aynı dizin) │
└─────────────────────────────────────────────────────┘
         │
         ▼
Executor "run_tests" çağırır
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ _run_tests_in_task_dir()                           │
│                                                     │
│  cwd = task_dir/buggy/                             │
│  pytest -v                                          │
│                                                     │
│  → Test dosyası bulunur ✅                          │
│  → source.py import edilir ✅                       │
│  → Test çalışır ve FAIL olur ✅                     │
└─────────────────────────────────────────────────────┘
```

### 4.2 Import Çözümlemesi

**Problem:** Test dosyası `from source import Customer` yaparken `source.py` bulunamıyordu.

**Çözüm:** Test dosyası `buggy/` dizinine yazılıyor, pytest de aynı dizinde çalışıyor:

```
buggy/
├── source.py           # from source import ... ✅
└── test_generated.py   # Test buradan import yapıyor
```

### 4.3 Validation Süreci (Değişiklik Yok)

`task_loader.py` içindeki `run_test_on_both_versions()` fonksiyonu doğru şekilde çalışmaya devam ediyor:

1. Geçici dizin oluşturur
2. Test dosyasını kopyalar
3. `buggy/source.py` veya `fixed/source.py` kopyalar
4. Pytest çalıştırır
5. Sonuçları karşılaştırır (buggy_failed AND fixed_passed = bug_revealing)

---

## 5. Öğrenilen Dersler

### 5.1 Path Management

- Test dosyaları ve kaynak dosyaları **aynı dizinde** olmalı
- Python import sistemi, dosyanın bulunduğu dizini `sys.path`'e ekler
- Farklı dizinlerde import için `PYTHONPATH` veya `conftest.py` gerekir

### 5.2 Tool Execution Timing

- TestWriter'ın tool çağrısı "öneri" değil, **gerçek eylem** olmalı
- Executor'ın `run_tests` çağrısından önce test dosyası mevcut olmalı
- Agent pipeline'da tool execution sırası kritik önemde

### 5.3 Debugging Stratejisi

1. Manuel pytest çalıştırarak problemi izole et
2. Dosya lokasyonlarını kontrol et
3. Import path'lerini doğrula
4. Agent çıktılarını analiz et

---

## 6. Kod Değişiklikleri Özeti

| Dosya             | Metod                           | Değişiklik                                    |
| ----------------- | ------------------------------- | --------------------------------------------- |
| custom_session.py | `_write_test_file_in_run_dir()` | Test dosyasını `buggy/` dizinine de yaz       |
| custom_session.py | `_run_tests_in_task_dir()`      | Pytest'i `buggy/` dizininde çalıştır          |
| custom_session.py | Agent loop (testwriter)         | TestWriter tool çağrısını otomatik execute et |

**Toplam:** 3 metod düzeltmesi, ~40 satır kod değişikliği

---

## 7. Sonuç

Executor-pytest path bug'ı başarıyla düzeltildi. Sistem artık:

- ✅ Test dosyalarını doğru lokasyona yazıyor
- ✅ Pytest'i doğru dizinde çalıştırıyor
- ✅ TestWriter tool çağrılarını hemen execute ediyor
- ✅ %100 BRTR oranına ulaşıyor (her iki modda)
- ✅ Minimum iterasyon kullanıyor (2 vs 5)

**Bug Durumu:** 🟢 ÇÖZÜLDÜ
