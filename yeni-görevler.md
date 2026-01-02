Tamam. Mevcut To-Do yapısını bozmadan, altına yalnızca test generation odaklı yeni görevleri ekliyorum.
Aşağıdaki maddeler doğrudan senin kararlaştırdığın mimariye birebir uyumlu ve yapılabilir işlerdir.

⸻

➕ EKLENECEK YENİ GÖREVLER (Test Generation Odaklı)

🧪 Test Generation Pipeline (Milestone A8)

🆕 Agent Mimarisi Genişletmesi
• TestWriter agent eklenmesi
• agents/agent_graph.yaml:
• Agentic mode’a testwriter ekle
(planner → analysis → testwriter → critic → reflection → executor)
• Baseline mode:
• Executor tek başına test yazabilecek (tek-ajan test generation)
• prompts/testwriter.txt
• pytest odaklı prompt
• Sadece test üretme görevi
• Net çıktı formatı:
• test dosya adı
• test fonksiyonu
• assert ifadeleri
• “Buggy kodda fail etmeli” talimatı açıkça yazılacak

⸻

🧩 Test Dosyası Üretimi & Yönetimi
• Generated test path standardizasyonu
• Üretilen testler:

generated*tests/
└── test_generated*<n>.py

    •	Executor test yazma desteği
    •	TestWriter çıktısını dosyaya yazma
    •	Dosya overwrite / append stratejisi belirleme
    •	Test isolation
    •	Her deneme için ayrı test dosyası
    •	Önceki başarısız testler silinmez (audit trail)

⸻

🔁 Bug-Revealing Test Doğrulama Döngüsü (KRİTİK)
• Buggy / Fixed ayrımı
• task_loader:
• buggy/ ve fixed/ dizinlerini ayırt edebilecek yapı
• Executor:
• Aynı test dosyasını iki ortamda çalıştırır
• Test sonucu sınıflandırması
• buggy_fail: bool
• fixed_pass: bool
• is_bug_revealing = buggy_fail AND fixed_pass
• Retry mekanizması
• Test başarısızsa (buggy PASS):
• Reflection → TestWriter → yeniden test üretimi
• Max deneme sayısı config’ten okunur

⸻

📊 Yeni Metrikler & Summary Genişletmesi
• Summary schema güncellemesi
• Ek alanlar:
• tests_generated: int
• attempts_until_success: int | null
• buggy_failed: bool
• fixed_passed: bool
• is_bug_revealing: bool
• overfitting_detected: bool
• Bug-Revealing Test Rate (BRTR) hesaplama
• task bazlı
• baseline vs agentic karşılaştırmalı

⸻

🧪 Task Yapısı Güncellemesi
• Task formatı revizyonu

task/
├── buggy/
│ └── source.py
├── fixed/
│ └── source.py
├── metadata.json

    •	metadata.json genişletmesi
    •	expected_failure_signal
    •	bug_description (human-readable)
    •	test_hint (opsiyonel, agent görmez)

⸻

📈 Evaluation & Karşılaştırma
• evaluation/run_all.py
• Test generation modunu destekle
• Her task için:
• baseline BRTR
• agentic BRTR
• Yeni karşılaştırma tabloları
• Bug-Revealing Test Rate
• Attempts per success
• False confidence rate
• Overfitting rate

⸻

🧠 Failure Analysis (Paper için altın)
• Başarısız test örnekleri saklama
• generated_tests/ altında etiketle:
• no_fail
• overfit
• flaky
• Negatif örnek analizi
• “LLM neden doğru testi yazamadı?”
• Pattern bazlı sınıflandırma:
• yanlış assert
• yanlış giriş kombinasyonu
• yanlış state kurulumu

⸻

📄 Paper Hazırlığı – Test Generation Ekseni
• Problem Definition (revize)
• “LLM-based test generation under misleading signals”
• Experimental Setup
• Bug-revealing test tanımı
• Retry allowed test generation
• Threats to Validity (genişletme)
• Prompt leakage
• Overfitting testler
• pytest nondeterminism
• Key Finding
• Agentic yapıların test generation başarısına etkisi

⸻

🧷 Not (kendine hatırlatma)

Bu noktadan sonra:
• “bug bulma” dili ❌
• “test yazdı mı” dili ❌
• “bug-revealing test generation” dili ✅

⸻

İstersen bir sonraki adımda:
• testwriter.txt prompt’unu birebir yazayım
• veya agent_graph.yaml için minimal diff çıkarayım
• ya da summary schema’yı pydantic olarak güncelleyeyim

Hangisiyle devam edelim?
