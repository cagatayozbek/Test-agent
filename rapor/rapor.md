# Adversarial LLM Agent Evaluation Report

**Tarih:** 31 Aralık 2025  
**Model:** gemini-2.5-pro  
**Framework:** Custom Multi-Agent Orchestrator

---

## 📊 Executive Summary

Bu rapor, LLM tabanlı bug-finding agent'ın adversarial task'lar üzerindeki performansını değerlendirmektedir.

### Genel Sonuçlar

| Metrik                 | Baseline  | Agentic        |
| ---------------------- | --------- | -------------- |
| **Ortalama Skor**      | 7.0/10    | 9.7/10         |
| **Bug Tespit Oranı**   | 2/3 (67%) | 3/3 (100%)     |
| **Reasoning Kalitesi** | Değişken  | Tutarlı Strong |

**Ana Bulgu:** Agentic mod (planner→analysis→critic→reflection→executor), baseline moda göre **%43 daha yüksek skor** ve **%100 bug tespit oranı** elde etti.

---

## 🧪 Task Detayları

### 1. Misleading Coverage Task

**Tuzak Tipi:** Coverage Illusion  
**Zorluk:** Orta

**Senaryo:** `calculate_discount` fonksiyonu %100 line/branch coverage'a sahip ama VIP + yüksek adet kombinasyonu test edilmemiş.

**Bug:** `discount = 0.1` satırı önceki VIP indirimi siliyor (+=0.1 olmalı).

| Mod      | Bug Tespit  | Reasoning | Skor  |
| -------- | ----------- | --------- | ----- |
| Baseline | ✅ Accurate | Strong    | 10/10 |
| Agentic  | ✅ Accurate | Strong    | 10/10 |

**Değerlendirme:** Her iki mod da bu task'ta mükemmel performans gösterdi. Agent "coverage illusion" tuzağını hemen fark etti.

---

### 2. State-Dependent Bug Task

**Tuzak Tipi:** State Transition  
**Zorluk:** Zor

**Senaryo:** `SessionManager.logout()` ve `Counter.reset()` metotları iç state'i tam temizlemiyor. Testler izole çalıştığı için bu sorun görünmüyor.

**Bug'lar:**

- `logout()` içinde `_session_data = {}` eksik
- `reset()` içinde `_history = []` eksik

| Mod      | Bug Tespit  | Reasoning | Skor  |
| -------- | ----------- | --------- | ----- |
| Baseline | ✅ Accurate | Strong    | 10/10 |
| Agentic  | ✅ Accurate | Strong    | 10/10 |

**Değerlendirme:** Agent her iki bug'ı da doğru tespit etti ve test stratejisindeki yapısal sorunu (state transition testlerinin eksikliği) açıkça ifade etti.

---

### 3. Indirect Cause Task

**Tuzak Tipi:** Indirect Causation  
**Zorluk:** Zor

**Senaryo:** Hata `DataService` katmanında görünüyor ama kök sebep `Config.timeout_ms = 0` default değeri. Testler her zaman explicit override kullanıyor.

**Bug:** `timeout_ms = 0` sonsuz bekleme riski oluşturuyor.

| Mod      | Bug Tespit  | Reasoning | Skor |
| -------- | ----------- | --------- | ---- |
| Baseline | ❌ Missed   | None      | 1/10 |
| Agentic  | ✅ Accurate | Strong    | 9/10 |

**Değerlendirme:** Bu task'ta baseline ve agentic arasındaki fark çok belirgin:

- **Baseline:** Sadece `run_tests` çağırıp hiçbir analiz yapmadan durdu. Kök sebep araştırması yok.
- **Agentic:** İlk adımda `Config.timeout_ms = 0` kök sebebini tespit etti ve test stratejisindeki sistemik sorunu açıkladı.

---

## 📈 Karşılaştırmalı Analiz

### Mod Karşılaştırması

```
                    Baseline    Agentic
                    --------    -------
misleading_coverage    10          10     (eşit)
state_dependent_bug    10          10     (eşit)
indirect_cause          1           9     (agentic +8)
                    --------    -------
Ortalama:             7.0         9.7
```

### Agentic Modun Avantajları

1. **Çok Aşamalı Reasoning:** Planner→Analysis→Critic→Reflection zinciri daha derin analiz sağlıyor.
2. **Self-Critique:** Critic agent overconfidence'ı ve zayıf varsayımları tespit ediyor.
3. **Kök Sebep Analizi:** Indirect cause gibi zor task'larda yüzeysel belirtilerden kök sebebe ulaşabiliyor.

### Baseline Modun Zayıflıkları

1. **Tek Adım Kısıtı:** Sadece executor çalışıyor, derinlemesine analiz yok.
2. **Context Bağımlılığı:** Task context verildiğinde iyi, verilmediğinde başarısız.
3. **Kök Sebep Körü:** Doğrudan görünmeyen bug'ları tespit edemiyor.

---

## 🔬 Agent Davranış Analizi

### Overconfidence Değerlendirmesi

- **Baseline:** 1/3 task'ta overconfident (sadece test çalıştırıp "başarılı" dedi)
- **Agentic:** 0/3 task'ta overconfident (critic agent etkili çalıştı)

### Reasoning Kalitesi Dağılımı

| Kalite   | Baseline | Agentic |
| -------- | -------- | ------- |
| Strong   | 2        | 3       |
| Adequate | 0        | 0       |
| Weak     | 0        | 0       |
| None     | 1        | 0       |

---

## 🎯 Sonuçlar ve Öneriler

### Ana Bulgular

1. **Agentic mod net üstünlük gösteriyor** - Özellikle dolaylı sebep gerektiren zor task'larda.
2. **Critic agent kritik rol oynuyor** - Overconfidence'ı engelliyor, varsayımları sorguluyor.
3. **Task context injection etkili** - Agent'lar kod ve test dosyalarını görebildiğinde performans artıyor.

### Gelecek Çalışmalar

1. **Daha fazla adversarial task** - Farklı tuzak tipleri (race condition, security, vb.)
2. **Çok turlu reasoning** - Agent'ın birden fazla tool çağrısı yapabilmesi
3. **Human-in-the-loop** - İnsan değerlendiricilerle LLM-as-judge karşılaştırması

---

## 📁 Teknik Detaylar

### Çalıştırma Komutu

```bash
python3 evaluation/run_all.py --mode both --evaluate -o evaluation/full_report.json
```

### Dosya Yapısı

```
evaluation/
├── tasks/
│   ├── misleading_coverage/
│   ├── state_dependent_bug/
│   └── indirect_cause/
├── evaluator.py          # LLM-based evaluation agent
├── run_all.py            # Test runner
└── full_report.json      # Ham sonuçlar
```

### Model Konfigürasyonu

- **Model:** gemini-2.5-pro
- **Temperature:** Default
- **Timeout:** 300s per task

---

_Rapor otomatik olarak oluşturulmuştur. Son güncelleme: 31 Aralık 2025_
