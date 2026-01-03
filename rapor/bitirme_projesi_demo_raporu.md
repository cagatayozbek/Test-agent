# Bitirme Projesi Demo Raporu

## LLM'lerin Yazılım Test Yeteneklerinin Araştırılması: Pilot Çalışma

**Proje Adı:** Test-Agent: Multi-Agent Software Testing Framework  
**Tarih:** 2 Ocak 2026  
**Ekip:** 2 Kişi  
**Durum:** Pilot Çalışma Tamamlandı - Araştırma Devam Ediyor 🔬

---

## 📋 İçindekiler

1. [Araştırma Vizyonu ve Büyük Resim](#1-araştırma-vizyonu-ve-büyük-resim)
2. [Problem Tanımı](#2-problem-tanımı)
3. [Pilot Çalışma: Bug Detection](#3-pilot-çalışma-bug-detection)
4. [Sistem Mimarisi](#4-sistem-mimarisi)
5. [Teknik Uygulama](#5-teknik-uygulama)
6. [Deney Tasarımı ve Sonuçlar](#6-deney-tasarımı-ve-sonuçlar)
7. [Araştırma Yol Haritası](#7-araştırma-yol-haritası)
8. [Literatüre Potansiyel Katkılar](#8-literatüre-potansiyel-katkılar)
9. [Tartışmaya Açık Sorular (Hocaya)](#9-tartışmaya-açık-sorular-hocaya)
10. [Pilot Çalışma Sonuçları (Özet)](#10-pilot-çalışma-sonuçları-özet)

---

## 1. Araştırma Vizyonu ve Büyük Resim

### 1.1 Ana Araştırma Sorusu

Bu proje, daha geniş bir araştırma sorusunun parçasıdır:

> **"LLM'ler yazılım testinde ne kadar yetenekli? Hangi test görevlerinde başarılı, hangilerinde başarısız? Ve çok-ajanlı sistemler bu yetenekleri nasıl etkiliyor?"**

### 1.2 "Test Yapma" Kavramının Ayrıştırılması

"LLM'ler test yapabilir mi?" sorusu çok geniş. Bu soruyu alt yeteneklere ayırdık:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM TEST YETENEKLERİ TAKSONOMISI                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. TEST ANLAMA (Comprehension)                                     │
│     ├── Test sonuçlarını yorumlama                                  │
│     ├── Coverage raporlarını analiz etme                            │
│     └── Fail eden testlerin kök sebebini bulma                      │
│                                                                      │
│  2. TEST ÜRETİMİ (Generation)                                       │
│     ├── Unit test yazma                                             │
│     ├── Integration test yazma                                      │
│     ├── Edge case testi yazma                                       │
│     └── Property-based test yazma                                   │
│                                                                      │
│  3. TEST KALİTESİ DEĞERLENDİRME (Quality Assessment)               │
│     ├── Mevcut testlerin yeterliliğini değerlendirme               │
│     ├── Coverage gap analizi                                        │
│     └── Test smell detection                                        │
│                                                                      │
│  4. TEST STRATEJİSİ (Strategy)                                      │
│     ├── Hangi kodun test edilmesi gerektiğini belirleme            │
│     ├── Risk bazlı test önceliklendirme                            │
│     └── Regression test seçimi                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Pilot Çalışmanın Kapsamı

Bu raporda sunulan **pilot çalışma**, yukarıdaki taksonominin bir alt kümesine odaklanır:

| Yetenek               | Pilot Çalışmada | Gelecek Çalışmalarda |
| --------------------- | --------------- | -------------------- |
| Test Sonucu Yorumlama | ✅ Yapıldı      | Genişletilecek       |
| Bug Detection         | ✅ Yapıldı      | Genişletilecek       |
| Coverage Analizi      | ✅ Yapıldı      | Genişletilecek       |
| Test Generation       | ❌              | 🎯 Öncelikli         |
| Test Strategy         | Kısmen          | Genişletilecek       |

### 1.4 Neden Bu Yaklaşım?

**Araştırma Stratejisi:** Önce LLM'lerin "test anlama" yeteneklerini ölçtük, çünkü:

1. **Prerequisite:** Test yazabilmek için önce test okuyabilmek gerekir
2. **Daha kontrollü:** Bug detection, test generation'dan daha kolay değerlendirilebilir
3. **Framework validasyonu:** Çok-ajanlı sistemin çalıştığını doğruladık
4. **Baseline oluşturma:** Gelecek çalışmalar için karşılaştırma noktası

### 1.5 Projenin Özgün Değeri

Bu proje şu açılardan özgün:

| Özellik           | Mevcut Literatür | Bizim Yaklaşımımız    |
| ----------------- | ---------------- | --------------------- |
| **Odak**          | Kod üretimi      | Test yetenekleri      |
| **Mimari**        | Tek LLM          | Çok-ajanlı pipeline   |
| **Değerlendirme** | Basit metrikler  | Adversarial benchmark |
| **Kapsam**        | Tek yetenek      | Taksonomi bazlı       |

---

## 2. Problem Tanımı

### 2.1 Araştırma Boşluğu (Research Gap)

Mevcut LLM literatürü büyük ölçüde **kod üretimine** odaklanmıştır. Kod üretimi, açıklama ve bug fixing konularında çok sayıda çalışma bulunurken, **LLM'lerin test yetenekleri** görece az araştırılmış bir alandır.

**Gözlemimiz:** LLM'lerin yazılım test sürecindeki yeteneklerinin sistematik değerlendirmesi eksik.

### 2.2 Neden Test Yetenekleri Önemli?

| Pratik Sebep               | Açıklama                           |
| -------------------------- | ---------------------------------- |
| **CI/CD Entegrasyonu**     | Otomatik test önerisi/üretimi      |
| **Developer Productivity** | Test yazma süresinin azaltılması   |
| **Quality Assurance**      | Kaçırılan edge case'lerin tespiti  |
| **Legacy Code**            | Test'siz kodun test ile kaplanması |

### 2.3 Geleneksel Test Coverage'ın Sınırları

Yazılım testlerinde yaygın kullanılan metrikler (line coverage, branch coverage) yanıltıcı olabilir:

```
┌─────────────────────────────────────────────────────────┐
│  %100 Code Coverage ≠ %100 Bug-Free                     │
│                                                         │
│  Örnek: Tüm satırlar çalıştırılmış olabilir ama        │
│  - Edge case kombinasyonları test edilmemiştir          │
│  - State geçişleri kontrol edilmemiştir                 │
│  - Dolaylı bağımlılıklar gözden kaçmıştır              │
└─────────────────────────────────────────────────────────┘
```

**Soru:** LLM'ler bu "coverage illusion"ı tespit edebilir mi?

### 2.4 Tek LLM'in Sınırları

Tek bir LLM, bug detection'da şu problemlerle karşılaşır:

| Problem               | Açıklama                                           |
| --------------------- | -------------------------------------------------- |
| **Overconfidence**    | Model, yüzeysel analiz sonrası "bug yok" diyebilir |
| **Kök Sebep Körlüğü** | Dolaylı sebepleri tespit edemez                    |
| **Context Sınırı**    | Büyük codebase'lerde bağlamı kaybeder              |
| **Tek Bakış Açısı**   | Self-critique yapamaz                              |

### 2.5 Çözüm Yaklaşımımız: Çok-Ajanlı Sistem

**Çok-ajanlı sistem** ile bu problemleri ele aldık:

- Her agent farklı bir "uzmanlık" alanına sahip
- Agent'lar birbirlerini denetler (özellikle Critic agent)
- Karar döngüsü iteratif: yeterli kanıt toplanana kadar devam eder

---

## 3. Pilot Çalışma: Bug Detection

### 3.1 Pilot Çalışmanın Amacı

Bu ilk çalışmada şu soruyu test ettik:

> **"LLM'ler, mevcut testler ve coverage raporları verildiğinde, gizli bug'ları tespit edebilir mi?"**

Bu soru, daha geniş "test yetenekleri" araştırmasının **bir alt kümesidir**.

### 3.2 Neden Bug Detection ile Başladık?

1. **Değerlendirmesi kolay:** Bug var/yok binary sonuç
2. **Ground truth mevcut:** Bug'ın ne olduğunu biliyoruz
3. **Framework validasyonu:** Çok-ajanlı sistemin çalıştığını doğrular
4. **Test anlama gerektirir:** Coverage okuma, test yorumlama yeteneklerini ölçer

### 3.3 Pilot Hipotez

**Hipotez:** Çok-ajanlı bir LLM pipeline'ı (Planner → Analysis → Critic → Reflection → Executor), tek bir LLM'ye kıyasla özellikle **aldatıcı (adversarial)** senaryolarda daha yüksek hata tespit oranına sahiptir.

---

## 4. Sistem Mimarisi

### 4.1 Genel Bakış

Sistemimiz iki modda çalışabilir:

```
╔══════════════════════════════════════════════════════════════════╗
║                        BASELINE MOD                               ║
║  ┌──────────┐                              ┌──────────────────┐   ║
║  │   Task   │ ─────────────────────────▶   │     Executor     │   ║
║  │  Input   │                              │   (Tek LLM)      │   ║
║  └──────────┘                              └──────────────────┘   ║
║                                                     │             ║
║                                                     ▼             ║
║                                            ┌──────────────────┐   ║
║                                            │      Output      │   ║
║                                            └──────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║                        AGENTIC MOD                                ║
║                                                                   ║
║  ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐        ║
║  │   Task   │──▶│ Planner │──▶│ Analysis │──▶│  Critic │        ║
║  │  Input   │   └─────────┘   └──────────┘   └─────────┘        ║
║  └──────────┘        │                            │              ║
║                      │                            ▼              ║
║                      │    ┌────────────┐   ┌──────────────┐      ║
║                      │    │  Executor  │◀──│  Reflection  │      ║
║                      │    └────────────┘   └──────────────┘      ║
║                      │          │                                ║
║                      │          ▼                                ║
║                      │   ┌─────────────┐                         ║
║                      └──▶│ continue?   │──▶ (loop veya stop)     ║
║                          └─────────────┘                         ║
╚══════════════════════════════════════════════════════════════════╝
```

### 4.2 Agent Rolleri ve Sorumlulukları

Her agent, LLM tarafından çalıştırılan bağımsız bir karar vericidir:

#### 🎯 1. Planner Agent

```
Görev: "Şimdi ne yapmalıyım?"
Input: Task context, önceki adımların özeti
Output: Hangi tool çağrılacak, neden

Örnek Karar:
"Coverage raporu aldım ama şüpheli. Config dosyasını
okumam gerekiyor çünkü timeout değeri garip görünüyor."
```

#### 🔍 2. Analysis Agent

```
Görev: Ham verileri yorumla, hipotez üret
Input: Tool çıktıları (test results, file contents)
Output: Yapılandırılmış analiz, potansiyel bug hipotezleri

Örnek Çıktı:
{
  "observation": "Test coverage %100 ama VIP+bulk kombinasyonu yok",
  "hypothesis": "Discount hesaplamasında override bug'ı olabilir",
  "confidence": 0.7,
  "next_action": "Manuel edge case analizi gerekli"
}
```

#### ⚖️ 3. Critic Agent

```
Görev: Analizi sorgula, zayıflıkları bul
Input: Analysis agent'ın çıktısı
Output: Eleştiri, eksikler, alternatif açıklamalar

Kritik Rol: OVERCONFIDENCE ENGELLEYİCİ
"Analysis agent 0.9 confidence vermiş ama Config
dosyasına hiç bakmamış. Bu sonuç güvenilir değil."
```

#### 💭 4. Reflection Agent

```
Görev: Sentez yap, devam/dur kararı ver
Input: Tüm önceki agent çıktıları
Output: Sentez özeti, continue=true/false

Karar Mantığı:
- Yeterli kanıt var mı?
- Hipotez tutarlı mı?
- Daha fazla bilgi gerekli mi?
```

#### ⚡ 5. Executor Agent

```
Görev: Tool çağrısı yap, sonucu döndür
Input: Planner'ın kararı
Output: Ham tool çıktısı (yorum yok!)

Kullanılabilir Tool'lar:
- run_tests(): Testleri çalıştır
- read_file(path): Dosya oku
- list_files(): Dosyaları listele
- log_event(payload): Event logla
```

### 4.3 Veri Akışı ve Context Passing

Agent'lar arası iletişim kritik önem taşır:

```
┌─────────────────────────────────────────────────────────────────┐
│                      CONTEXT OBJECT                              │
├─────────────────────────────────────────────────────────────────┤
│  {                                                               │
│    "task_id": "indirect_cause",                                 │
│    "turn": 3,                                                    │
│    "history": [                                                  │
│      {"agent": "planner", "action": "read_file config.py"},     │
│      {"agent": "executor", "result": "timeout_ms = 0"},         │
│      {"agent": "analysis", "hypothesis": "zero timeout risk"},  │
│      {"agent": "critic", "concern": "test override effect?"}    │
│    ],                                                            │
│    "current_hypothesis": {...},                                  │
│    "confidence_score": 0.85                                      │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Kod ile Tool Arasındaki Ayrım

**ÖNEMLİ TASARIM PRENSİBİ:** Tool'lar tamamen "aptal"dır!

```
┌───────────────────────────────────────────────────────────────┐
│  TOOL'LAR (Kod)              │  AGENT'LAR (LLM)               │
│  ─────────────────           │  ─────────────────             │
│  ✗ Yorum yapmaz              │  ✓ Yorumlar                    │
│  ✗ Karar vermez              │  ✓ Karar verir                 │
│  ✗ Öncelik atamaz            │  ✓ Önceliklendirir             │
│  ✗ Coverage analiz etmez     │  ✓ Coverage yorumlar           │
│                              │                                 │
│  Sadece I/O:                 │  Tüm bilişsel görevler:        │
│  - Dosya oku/yaz             │  - Hipotez üretme              │
│  - Test çalıştır             │  - Eleştiri                    │
│  - Sonuç döndür              │  - Sentez                      │
└───────────────────────────────────────────────────────────────┘
```

Bu ayrım sayesinde:

- Aynı tool ile farklı stratejiler denenebilir
- Agent'ların karar süreçleri incelenebilir
- Sistem davranışı LLM'in yeteneklerine bağlıdır (hand-coded logic yok)

---

## 5. Teknik Uygulama

### 5.1 Teknoloji Stack'i

| Bileşen            | Teknoloji     | Açıklama                             |
| ------------------ | ------------- | ------------------------------------ |
| **Dil**            | Python 3.11   | Ana geliştirme dili                  |
| **LLM API**        | Google Gemini | gemini-2.0-flash, 2.5-flash, 2.5-pro |
| **Konfigürasyon**  | YAML          | Agent graph tanımları                |
| **Output Format**  | JSON/JSONL    | Structured logging                   |
| **Test Framework** | pytest        | Task testleri için                   |

### 5.2 Proje Dosya Yapısı

```
Test-Agent/
├── main.py                 # Ana giriş noktası
├── runner.py               # Benchmark orchestrator
├── custom_session.py       # Çok-ajanlı session yönetimi
├── llm_client.py           # LLM API wrapper
├── config.yaml             # Sistem konfigürasyonu
│
├── agents/
│   └── agent_graph.yaml    # Agent pipeline tanımı
│
├── tools/
│   └── __init__.py         # Tool implementasyonları
│
├── evaluation/
│   ├── evaluator.py        # Otomatik değerlendirici
│   ├── tasks/              # Benchmark task'ları (v1)
│   └── tasks_v2/           # Benchmark task'ları (v2)
│
├── prompts/
│   ├── planner.txt         # Planner system prompt
│   ├── analysis.txt        # Analysis system prompt
│   ├── critic.txt          # Critic system prompt
│   ├── reflection.txt      # Reflection system prompt
│   └── executor.txt        # Executor system prompt
│
├── runs/                   # Çalıştırma sonuçları
├── benchmark_runs/         # Benchmark sonuçları
└── rapor/                  # Raporlar
```

### 5.3 Agent Graph Konfigürasyonu

Agent pipeline'ı YAML ile tanımlanır:

```yaml
# agents/agent_graph.yaml
agents:
  - name: planner
    prompt_file: prompts/planner.txt
    next: analysis

  - name: analysis
    prompt_file: prompts/analysis.txt
    next: critic

  - name: critic
    prompt_file: prompts/critic.txt
    next: reflection

  - name: reflection
    prompt_file: prompts/reflection.txt
    next: executor
    decision_field: continue # true/false döner

  - name: executor
    prompt_file: prompts/executor.txt
    next: planner # loop back
    can_use_tools: true

settings:
  max_turns: 10
  timeout_seconds: 300
```

### 5.4 Örnek Prompt Yapısı (Critic Agent)

```
Sen bir Critic Agent'sın. Görevin Analysis Agent'ın
çıktısını eleştirel gözle değerlendirmek.

KONTROL LİSTESİ:
1. Hipotez kanıtlarla destekleniyor mu?
2. Alternatif açıklamalar düşünüldü mü?
3. Confidence skoru gerçekçi mi?
4. Eksik veri var mı?

OVERCONFIDENCE UYARISI:
- %90+ confidence → çok güçlü kanıt gerektirir
- Tek bir dosya okuması yeterli değildir
- Test coverage yanıltıcı olabilir

OUTPUT FORMAT:
{
  "critique": "...",
  "concerns": [...],
  "alternative_explanations": [...],
  "recommendation": "accept/revise/need_more_data"
}
```

### 5.5 Session Yönetimi

`custom_session.py` dosyası, agent'lar arası geçişi ve context'i yönetir:

```python
class AgenticSession:
    def __init__(self, task_context, config):
        self.context = task_context
        self.history = []
        self.current_agent = "planner"

    async def run(self):
        while self.current_agent and self.turn < self.max_turns:
            # 1. Agent'ı çalıştır
            result = await self.run_agent(self.current_agent)

            # 2. History'e ekle
            self.history.append({
                "agent": self.current_agent,
                "result": result,
                "turn": self.turn
            })

            # 3. Sonraki agent'a geç veya dur
            if self.current_agent == "reflection":
                if not result.get("continue"):
                    break

            self.current_agent = self.get_next_agent()
            self.turn += 1

        return self.generate_summary()
```

---

## 6. Deney Tasarımı ve Sonuçlar

### 6.1 Benchmark Task'ları

12 adet **adversarial** (aldatıcı) task tasarladık. Bu task'lar, LLM'leri yanıltmak için özel olarak hazırlandı:

| Task                    | Tuzak Tipi         | Zorluk   | Açıklama                                 |
| ----------------------- | ------------------ | -------- | ---------------------------------------- |
| `misleading_coverage`   | Coverage Illusion  | Orta     | %100 coverage ama eksik edge case        |
| `state_dependent_bug`   | State Transition   | Zor      | İzole testlerde görünmeyen state bug     |
| `indirect_cause`        | Indirect Causation | Zor      | Kök sebep farklı katmanda                |
| `async_race_condition`  | Concurrency        | Zor      | Race condition                           |
| `boundary_threshold`    | Edge Case          | Orta     | Sınır değer hatası                       |
| `cache_invalidation`    | State              | Orta     | Cache tutarsızlığı                       |
| `null_handling_profile` | Null Safety        | Zor      | None/null handling                       |
| `off_by_one_loop`       | Classic            | Kolay    | Off-by-one hatası                        |
| `swallowed_exception`   | Error Handling     | Çok Zor  | Yutulmuş exception                       |
| `type_coercion_price`   | Type Safety        | Orta     | Tip dönüşüm hatası                       |
| `bugsinpy_*`            | Real-World         | Değişken | Gerçek dünya bug'ları (BugsInPy dataset) |

### 6.2 Task Yapısı

Her task şu dosyaları içerir:

```
evaluation/tasks_v2/indirect_cause/
├── source_code.py      # Bug'lı kaynak kod
├── test_code.py        # Mevcut testler (bug'ı yakalamıyor)
├── metadata.json       # Task bilgileri ve doğru cevap
└── README.md           # Task açıklaması
```

**Örnek metadata.json:**

```json
{
  "task_id": "indirect_cause",
  "difficulty": "hard",
  "bug_type": "indirect_causation",
  "expected_bug_location": "config.py:15",
  "expected_root_cause": "timeout_ms = 0 causes infinite wait",
  "decoy_symptoms": ["DataService timeout", "Connection error"],
  "evaluation_criteria": {
    "must_identify": "Config.timeout_ms default value",
    "must_explain": "Indirect causation through dependency"
  }
}
```

### 6.3 Deney Parametreleri

| Parametre         | Değer                                              |
| ----------------- | -------------------------------------------------- |
| **Modeller**      | gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro |
| **Modlar**        | Baseline, Agentic                                  |
| **Task Sayısı**   | 12                                                 |
| **Tekrar Sayısı** | Her kombinasyon için max 3 deneme                  |
| **Max Turns**     | 10 (agentic mod için)                              |
| **Timeout**       | 300 saniye                                         |

### 6.4 Değerlendirme Kriterleri

Her run şu kriterlere göre değerlendirildi:

1. **Success (Başarı):** Doğru bug tespit edildi mi?
2. **Attempts:** Kaç denemede başarılı olundu?
3. **Tool Calls:** Kaç tool çağrısı yapıldı?
4. **Token Usage:** Toplam token tüketimi
5. **Duration:** Çalışma süresi

**Otomatik Değerlendirme:**

```python
def evaluate_run(run_output, expected):
    # Bug lokasyonu doğru mu?
    location_match = expected["bug_location"] in run_output["identified_location"]

    # Kök sebep açıklanmış mı?
    root_cause_match = semantic_similarity(
        run_output["explanation"],
        expected["root_cause"]
    ) > 0.7

    return location_match and root_cause_match
```

---

### 6.5 Sonuçlar ve Analiz

### 6.1 Genel Başarı Oranları

#### Model ve Mod Bazında Özet

| Model            | Mod      | Başarı Oranı | Ort. Deneme | Ort. Tool Çağrısı | Ort. Token | Ort. Süre |
| ---------------- | -------- | ------------ | ----------- | ----------------- | ---------- | --------- |
| gemini-2.0-flash | Baseline | **%66.7**    | 1.8         | 3.7               | 4,358      | 5.4s      |
| gemini-2.0-flash | Agentic  | %50.0        | 2.2         | 8.1               | 40,415     | 28.7s     |
| gemini-2.5-flash | Baseline | **%83.3**    | 1.4         | 2.8               | 7,698      | 23.9s     |
| gemini-2.5-flash | Agentic  | **%83.3**    | 1.5         | 5.1               | 50,057     | 86.6s     |
| gemini-2.5-pro   | Baseline | %83.3        | 1.3         | 2.5               | 6,107      | 31.3s     |
| gemini-2.5-pro   | Agentic  | **%91.7**    | 1.4         | 6.6               | 51,888     | 162.9s    |

#### Görselleştirme

```
Başarı Oranı Karşılaştırması (%)
═══════════════════════════════════════════════════════════════

gemini-2.0-flash
  Baseline  ████████████████████████████████████████░░░░░  66.7%
  Agentic   █████████████████████████░░░░░░░░░░░░░░░░░░░░░  50.0%

gemini-2.5-flash
  Baseline  █████████████████████████████████████████████░  83.3%
  Agentic   █████████████████████████████████████████████░  83.3%

gemini-2.5-pro
  Baseline  █████████████████████████████████████████████░  83.3%
  Agentic   █████████████████████████████████████████████████ 91.7%

═══════════════════════════════════════════════════════════════
```

### 6.2 Task Bazlı Detaylı Sonuçlar

#### Başarı Matrisi (✓ = %100 Başarı, ✗ = %0 Başarı)

| Task                  | 2.0-flash Base | 2.0-flash Agent | 2.5-flash Base | 2.5-flash Agent | 2.5-pro Base | 2.5-pro Agent |
| --------------------- | -------------- | --------------- | -------------- | --------------- | ------------ | ------------- |
| async_race_condition  | ✓              | ✗               | ✓              | ✓               | ✓            | ✓             |
| boundary_threshold    | ✓              | ✓               | ✓              | ✓               | ✓            | ✓             |
| bugsinpy_black_async  | ✓              | ✗               | ✓              | ✓               | ✓            | ✓             |
| bugsinpy_pysnooper    | ✗              | ✗               | ✓              | ✗               | ✓            | ✓             |
| bugsinpy_thefuck_fish | ✓              | ✓               | ✓              | ✓               | ✓            | ✓             |
| bugsinpy_thefuck_fix  | ✗              | ✓               | ✓              | ✓               | ✓            | ✓             |
| bugsinpy_tqdm         | ✓              | ✓               | ✓              | ✓               | ✓            | ✓             |
| cache_invalidation    | ✓              | ✓               | ✓              | ✓               | ✓            | ✓             |
| null_handling_profile | ✗              | ✗               | ✗              | ✓               | ✗            | ✓             |
| off_by_one_loop       | ✓              | ✓               | ✓              | ✓               | ✓            | ✓             |
| swallowed_exception   | ✗              | ✗               | ✗              | ✗               | ✗            | ✗             |
| type_coercion_price   | ✓              | ✗               | ✓              | ✓               | ✓            | ✓             |

### 6.3 Önemli Bulgular

#### Bulgu 1: Model Kalitesi Agentic Modda Daha Kritik

```
gemini-2.0-flash: Baseline > Agentic (66.7% > 50.0%)
gemini-2.5-flash: Baseline = Agentic (83.3% = 83.3%)
gemini-2.5-pro:   Baseline < Agentic (83.3% < 91.7%)
```

**Yorum:** Düşük kapasiteli modeller (2.0-flash), çok-ajanlı sistemin karmaşıklığıyla başa çıkamıyor. Agent'lar arası iletişimde bilgi kaybı yaşanıyor. Güçlü modeller (2.5-pro) ise agentic mod'dan fayda sağlıyor.

#### Bulgu 2: Zor Task'larda Agentic Mod Fark Yaratıyor

**null_handling_profile** task'ı örneği:

| Model     | Baseline | Agentic |
| --------- | -------- | ------- |
| 2.0-flash | ✗        | ✗       |
| 2.5-flash | ✗        | ✓       |
| 2.5-pro   | ✗        | ✓       |

Bu task'ta baseline mod hiçbir modelde başarılı olamazken, agentic mod ile 2.5-flash ve 2.5-pro başarılı oldu.

#### Bulgu 3: swallowed_exception Tüm Kombinasyonlarda Başarısız

Bu task, tüm model-mod kombinasyonlarında %0 başarı oranına sahip. Bu, mevcut LLM'lerin "yutulmuş exception" paternini tespit etmekte zorlandığını gösteriyor.

**Olası sebepler:**

- Exception handling kodu normal görünüyor
- Hata belirtisi dolaylı (silent failure)
- Daha sofistike analiz stratejisi gerekli

#### Bulgu 4: Maliyet-Performans Dengesi

```
                    Token Kullanımı (ortalama)
═══════════════════════════════════════════════════════════

Baseline Modlar
  gemini-2.0-flash    ████░░░░░░░░░░░░░░░░░░░░░░░░  4,358
  gemini-2.5-flash    ████████░░░░░░░░░░░░░░░░░░░░  7,699
  gemini-2.5-pro      ██████░░░░░░░░░░░░░░░░░░░░░░  6,107

Agentic Modlar
  gemini-2.0-flash    ████████████████████████████░ 40,416
  gemini-2.5-flash    ██████████████████████████████ 50,057
  gemini-2.5-pro      ██████████████████████████████ 51,889

═══════════════════════════════════════════════════════════
```

**Agentic mod ~10x daha fazla token tüketiyor** ama en yüksek başarı oranını (%91.7) sağlıyor.

### 6.4 Başarısız Run Analizi

En çok başarısız olan senaryolar:

| Task                  | Model     | Mod         | Deneme | Sebep                          |
| --------------------- | --------- | ----------- | ------ | ------------------------------ |
| swallowed_exception   | Tümü      | Tümü        | 3      | Silent failure tespiti çok zor |
| null_handling_profile | 2.0-flash | Her iki mod | 3      | Model kapasitesi yetersiz      |
| async_race_condition  | 2.0-flash | Agentic     | 3      | Concurrency analizi karmaşık   |

---

### 6.6 Tartışma

#### 6.6.1 Hipotez Değerlendirmesi

**Orijinal Hipotez:** "Çok-ajanlı pipeline, tek LLM'den daha başarılı"

**Sonuç:** **Kısmen Doğrulandı**

- ✓ En yüksek başarı oranı (%91.7) agentic mod ile elde edildi
- ✓ Zor task'larda (null_handling) agentic mod fark yarattı
- ✗ Düşük kapasiteli modellerde agentic mod zararlı oldu
- ✗ Bazı task'larda (swallowed_exception) hiçbir mod başarılı olamadı

#### 6.6.2 Agentic Modun Avantajları

1. **Derinlemesine Analiz:** Birden fazla tur sayesinde yüzeysel analizin ötesine geçebiliyor
2. **Self-Correction:** Critic agent, hatalı hipotezleri düzeltebiliyor
3. **Kök Sebep Tespiti:** Dolaylı bug'ları bulma kapasitesi daha yüksek

#### 6.6.3 Agentic Modun Dezavantajları

1. **Yüksek Maliyet:** ~10x token tüketimi
2. **Uzun Süre:** ~5-10x daha uzun çalışma süresi
3. **Model Bağımlılığı:** Zayıf modellerde performans düşüşü

#### 6.6.4 Neden Bazı Task'lar Zor?

| Task Tipi           | Zorluk Sebebi            | Gerekli Yetenek          |
| ------------------- | ------------------------ | ------------------------ |
| Indirect Cause      | Semptom ≠ Sebep          | Cross-module reasoning   |
| State Bug           | İzole testlerde görünmez | Temporal reasoning       |
| Swallowed Exception | Sessiz başarısızlık      | Deep code understanding  |
| Race Condition      | Non-deterministic        | Concurrency mental model |

#### 6.6.5 Pilot Çalışmanın Sınırlılıkları

1. **Tek API (Gemini):** Diğer LLM'ler (GPT-4, Claude) test edilmedi
2. **Sınırlı Task Çeşitliliği:** 12 task, gerçek dünya çeşitliliğini tam yansıtmıyor
3. **Deterministik Olmayan Sonuçlar:** LLM çıktıları değişkenlik gösteriyor
4. **Otomatik Değerlendirme:** İnsan değerlendirmesi yapılmadı

---

## 7. Araştırma Yol Haritası

### 7.1 Gelecek Çalışmaların Genel Görünümü

Pilot çalışma tamamlandı. Şimdi daha geniş araştırma sorularına geçebiliriz:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ARAŞTIRMA YOL HARİTASI                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ✅ TAMAMLANDI                                                          │
│  ════════════                                                           │
│  Pilot Çalışma: Bug Detection                                           │
│  • Framework geliştirildi                                               │
│  • Baseline vs Agentic karşılaştırıldı                                  │
│  • 12 adversarial task ile test edildi                                  │
│                                                                          │
│  🎯 SIRADA (Öncelik 1)                                                  │
│  ════════════════════                                                   │
│  Çalışma 2: Test Generation                                             │
│  • LLM'e kod ver, test yazdır                                           │
│  • Yazılan testlerin kalitesini ölç                                     │
│  • Coverage artışını raporla                                            │
│                                                                          │
│  📋 GELECEK (Öncelik 2)                                                 │
│  ═════════════════════                                                  │
│  Çalışma 4: Test Strategy Recommendation                                │
│  Çalışma 5: Multi-Model Comparison (GPT-4, Claude, Llama)              │
│  Çalışma 6: Human-in-the-Loop Experiments                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Çalışma 2: Test Generation (Detay)

**Araştırma Sorusu:** LLM'ler, kaynak kod verildiğinde kaliteli test yazabilir mi?

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEST GENERATION DENEYİ                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT                          OUTPUT                           │
│  ─────                          ──────                           │
│  • source_code.py        ───▶   • generated_tests.py            │
│  • (test yok)                   • coverage report                │
│                                                                  │
│  DEĞERLENDİRME KRİTERLERİ                                       │
│  ────────────────────────                                        │
│  1. Coverage: Kaç satır/branch kaplandı?                        │
│  2. Readability: Testler okunabilir mi?                         │
│  3. Edge Cases: Sınır değerler test ediliyor mu?                │
│  4. False Positives: Yanlış fail eden test var mı?              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Mevcut framework'ü nasıl kullanırız:**

- Planner: "Hangi fonksiyonları test etmeliyim?"
- Analysis: "Bu fonksiyonun edge case'leri neler?"
- Critic: "Bu test yeterli mi? Eksik case var mı?"
- Executor: Test kodunu yaz ve çalıştır

### 7.3 Çalışma 3: Test Strategy (Detay)

**Araştırma Sorusu:** LLM'ler, mevcut test suite'in eksiklerini tespit edip strateji önerebilir mi?

**Senaryolar:**

1. "Bu kod için test coverage %60. Hangi kısımlar kritik ve öncelikli test edilmeli?"
2. "Bu fonksiyon değişti. Hangi testler etkilenmiş olabilir?"
3. "Sınırlı süremiz var. En riskli kodları test etmek için strateji öner."

### 7.4 Framework'ün Esnekliği

Mevcut çok-ajanlı framework, tüm bu çalışmalar için yeniden kullanılabilir:

| Çalışma         | Planner         | Analysis          | Critic              | Executor      |
| --------------- | --------------- | ----------------- | ------------------- | ------------- |
| Bug Detection   | Tool seç        | Bug hipotezi      | Hipotezi sorgula    | Tool çalıştır |
| Test Generation | Test stratejisi | Edge case analizi | Test kalitesi       | Test yaz      |
| Test Strategy   | Öncelik belirle | Risk analizi      | Strateji eleştirisi | Rapor oluştur |

---

## 8. Literatüre Potansiyel Katkılar

### 8.1 Novel Contributions (Özgün Katkılar)

Bu araştırmanın potansiyel özgün katkıları:

| #   | Katkı                     | Açıklama                                           | Yenilik Seviyesi |
| --- | ------------------------- | -------------------------------------------------- | ---------------- |
| 1   | **Taksonomi**             | LLM test yeteneklerinin sistematik sınıflandırması | ⭐⭐⭐           |
| 2   | **Multi-Agent Mimari**    | Test görevleri için çok-ajanlı tasarım             | ⭐⭐⭐           |
| 3   | **Adversarial Benchmark** | LLM'leri zorlayan test senaryoları                 | ⭐⭐⭐⭐         |
| 4   | **Empirik Çalışma**       | Model × Mod × Task karşılaştırması                 | ⭐⭐             |

### 8.2 İlgili Çalışmalar (Related Work)

Literatürle konumlandırma için bakılması gereken alanlar:

| Alan                          | Örnek Çalışmalar            | Bizim Farkımız    |
| ----------------------------- | --------------------------- | ----------------- |
| **LLM Code Generation**       | Codex, CodeLlama, StarCoder | Test odaklı değil |
| **Automated Test Generation** | EvoSuite, Randoop           | LLM tabanlı değil |
| **LLM for Testing**           | CodaMosa, ChatUniTest       | Çok-ajanlı değil  |
| **Multi-Agent LLM**           | AutoGen, CrewAI             | Test odaklı değil |

### 8.3 Araştırma Soruları Matrisi

Tüm araştırmayı kapsayan research questions:

```
RQ1: LLM'ler farklı test görevlerinde (anlama, üretme, strateji)
     nasıl performans gösteriyor?

RQ2: Çok-ajanlı mimariler, test görevlerinde tek-ajanlı sistemlere
     göre avantaj sağlıyor mu?

RQ3: Model kapasitesi (2.0-flash vs 2.5-pro) test performansını
     nasıl etkiliyor?

RQ4: Hangi test senaryoları LLM'ler için hâlâ çözümsüz?
```

---

## 9. Tartışmaya Açık Sorular (Hocaya)

Bu bölüm, danışman hocamızın görüşlerini almak istediğimiz konuları içerir.

### 9.1 Araştırma Kapsamı Hakkında

> **Soru 1:** Araştırma sorusu ("LLM'ler test yapabilir mi?") çok geniş mi? Daha spesifik bir alt probleme mi odaklanmalıyız?

> **Soru 2:** Pilot çalışma (bug detection) yeterli bir başlangıç mı? Yoksa önce test generation ile mi başlamalıydık?

> **Soru 3:** Taksonomimizdeki 4 yetenek (anlama, üretme, kalite, strateji) kapsamlı mı? Eksik bir kategori var mı?

### 9.2 Metodoloji Hakkında

> **Soru 4:** Adversarial benchmark yaklaşımı literatür için yeterince yeni mi? Başka değerlendirme metodları önerir misiniz?

> **Soru 5:** Sadece Gemini API kullanıyoruz. Farklı LLM'leri (GPT-4, Claude) test etmek şart mı, yoksa bir model ailesi yeterli mi?

### 9.3 Teknik Sorular

> **Soru 6:** Çok-ajanlı mimaride Critic agent'ın rolü çok kritik çıktı. Bu bulguyu nasıl genelleştirebiliriz?

> **Soru 7:** swallowed_exception tüm kombinasyonlarda başarısız oldu. Bu tür "LLM için zor" senaryoları araştırma odağı yapmalı mıyız?

> **Soru 8:** Test generation çalışmasında "kalite" nasıl ölçülmeli?

### 9.4 Pratik Sorular

> **Soru 9:** Framework'ü açık kaynak yapmalı mıyız? Ne zaman?

> **Soru 10:** Bu araştırma, bir tez çalışmasına dönüşebilir mi? Yüksek lisans için yeterli mi?

---

## 10. Pilot Çalışma Sonuçları (Özet)

### 10.1 Ana Bulgular

1. **Çok-ajanlı sistemler potansiyel taşıyor:** En yüksek başarı oranı (%91.7) agentic mod ile elde edildi.

2. **Model kalitesi kritik:** Agentic mod ancak güçlü modellerle (gemini-2.5-pro) fayda sağlıyor.

3. **Trade-off var:** Performans artışı, maliyet ve süre artışı ile birlikte geliyor.

4. **Bazı bug tipleri hâlâ çok zor:** swallowed_exception gibi paternler mevcut LLM'ler için çözümsüz.

### 10.2 Mevcut Katkılarımız

| Katkı              | Açıklama                                       |
| ------------------ | ---------------------------------------------- |
| **Framework**      | Yeniden kullanılabilir çok-ajanlı test sistemi |
| **Benchmark**      | 12 adversarial task içeren test seti           |
| **Empirik Analiz** | 3 model × 2 mod × 12 task = 72 deney           |
| **Mimari Önerisi** | Critic agent'ın kritik rolünün gösterilmesi    |

### 10.3 Sonraki Adım Önerisi

Pilot çalışma başarılı. Önerilen sonraki adım:

```
┌─────────────────────────────────────────────────────────────┐
│  ÖNERİLEN SONRAKİ ADIM: Test Generation Çalışması           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Neden?                                                      │
│  • Pilot çalışma "test anlama" yeteneğini ölçtü             │
│  • Doğal devamı "test üretme" yeteneğini ölçmek             │
│  • Framework hazır, sadece task/prompt değişikliği gerek    │
│  • Mutation testing ile birleştirilirse güçlü katkı olur    │
│                                                              │
│  Süre Tahmini: 4-6 hafta                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📎 Ekler

### Ek A: Çalıştırma Komutları

```bash
# Baseline mod çalıştırma
python main.py --mode baseline --model gemini-2.5-pro --task indirect_cause

# Agentic mod çalıştırma
python main.py --mode agentic --model gemini-2.5-pro --task indirect_cause

# Tüm benchmark'ı çalıştırma
./run_benchmark.sh

# Rapor oluşturma
python generate_benchmark_report.py
```

### Ek B: Örnek Çıktı (Agentic Mod)

```json
{
  "task_id": "indirect_cause",
  "mode": "agentic",
  "model": "gemini-2.5-pro",
  "success": true,
  "turns": 4,
  "agent_trace": [
    { "agent": "planner", "action": "run_tests" },
    { "agent": "analysis", "hypothesis": "DataService timeout issue" },
    { "agent": "critic", "concern": "Root cause not in DataService" },
    { "agent": "planner", "action": "read_file config.py" },
    { "agent": "analysis", "hypothesis": "timeout_ms=0 is root cause" },
    { "agent": "critic", "verdict": "Strong evidence" },
    { "agent": "reflection", "decision": "STOP - bug found" }
  ],
  "final_hypothesis": {
    "bug_location": "config.py:15",
    "root_cause": "timeout_ms = 0 causes infinite wait risk",
    "confidence": 0.92
  },
  "tokens_used": 23517,
  "duration_seconds": 77.2
}
```

### Ek C: Proje Yapısı

```
Test-Agent/
├── main.py                 # Ana giriş noktası
├── runner.py               # Benchmark orchestrator
├── custom_session.py       # Çok-ajanlı session yönetimi
├── llm_client.py           # LLM API wrapper
├── config.yaml             # Sistem konfigürasyonu
├── agents/                 # Agent tanımları
├── tools/                  # Tool implementasyonları
├── evaluation/             # Değerlendirme sistemi
│   ├── tasks_v2/           # 12 adversarial task
│   └── evaluator.py        # Otomatik değerlendirici
├── prompts/                # Agent prompt'ları
├── runs/                   # Çalıştırma sonuçları
└── rapor/                  # Raporlar
```

### Ek D: Referanslar

1. BugsInPy Dataset - Real Python Bugs
2. Google Gemini API Documentation
3. Multi-Agent Systems in Software Engineering (Literature)

---

**Rapor Sonu**

_Bu rapor, Test-Agent projesinin pilot çalışması tamamlandıktan sonra hazırlanmıştır. Rapor, bir sonuç değil bir başlangıç olarak konumlandırılmıştır. Danışman hocamızın görüşleri doğrultusunda araştırma yönlendirilecektir._

**Sonraki Toplantı İçin Gündem:**

- [ ] Araştırma kapsamının netleştirilmesi
- [ ] Araştırma yol haritasının gözden geçirilmesi
- [ ] Test generation çalışmasının planlanması
