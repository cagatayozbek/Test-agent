FINAL PROJECT PLAN

Fully Agentic, LLM-Only Semantic Coverage Interpretation

(DeepAgents-Orchestrated)

⸻

🔒 Milestone A0 — Research Claim Lock (LLM-Only Redefinition)

Amaç

“LLM-only” iddiasını yanlış anlaşılmayacak şekilde tanımlamak.

Yapılacaklar
• Tek cümlelik iddia:

“This work investigates whether LLM-based agents, without any hand-coded decision logic, can autonomously interpret raw execution artifacts (tests, coverage, traces) and decide how to act.”

    •	Açık non-goals:
    •	AST yok
    •	CFG yok
    •	heuristic yok
    •	rule-based policy yok
    •	code-driven prioritization yok
    •	Net ayrım:
    •	Code = sandbox + I/O
    •	Agents = cognition + control

Çıktılar
• docs/research_positioning.md

Kabul Kriteri
• Bir okuyucu “kod ne yapıyor / LLM ne yapıyor” ayrımını net görüyor.

⸻

🧱 Milestone A1 — Blind Tool Substrate (No Intelligence)

Amaç

Araçlar tamamen kör olsun.

Tools (değiştirilemez kontrat)
• run_tests() → raw stdout/stderr
• read_file(path)
• read_file_window(path, start, end)
• list_files()
• log_event(payload)

❗ Tools:
• coverage yorumlamaz
• missing line hesaplamaz
• context seçmez
• önem atamaz

Çıktılar
• tools/
• runs/<run_id>/raw_logs.json

Kabul Kriteri
• Tool çıktıları tek başına hiçbir anlam ifade etmiyor.

⸻

🧠 Milestone A2 — Agent Graph (DeepAgents Core)

Amaç

Policy yerine çok-ajanlı biliş.
**⚠️ DeepAgents Integration Note:**
DeepAgents was evaluated as a routing substrate but exhibited non-terminating internal loops even under tool-free configurations. The custom orchestrator (`custom_session.py`) was retained for experimental reproducibility. See `docs/deepagents_failure.md` for details.
Agent’lar (tamamı LLM) 1. Planner Agent
• “Şu an ne yapmalıyım?”
• Hangi tool çağrılacak → kendisi karar verir 2. Analysis Agent
• Ham test/coverage çıktısını yorumlar
• Hipotez üretir 3. Critic Agent
• “Bu yorum saçma mı?”
• Çelişki, boşluk, aşırı özgüven tespiti 4. Reflection Agent
• “Devam etmeli miyim?”
• STOP kararını kendisi verir 5. Executor Agent
• Tool çağrısını yapar
• Asla yorum yapmaz

DeepAgents sadece:
• mesaj akışını
• sıra kontrolünü
• max_turn (güvenlik) sınırını yönetir

Çıktılar
• agents/
• agent_graph.yaml

Kabul Kriteri
• Hiçbir karar koddan gelmiyor.
• Aynı durumda farklı run’lar farklı strateji deneyebiliyor.

⸻

🧾 Milestone A3 — LLM-Owned Semantic Hypothesis

Amaç

Yapı var ama zorlayıcı kontrol yok.

SemanticHypothesis (LLM sözleşmesi)

{
"hypothesis": "...",
"confidence_level": "LOW|MEDIUM|HIGH",
"assumptions": [...],
"evidence": [...],
"what_might_be_missing": "...",
"next_question": "..."
}

    •	JSON validation: syntax only
    •	İçerik doğruluğu:
    •	Critic Agent tarafından denetlenir
    •	“Bilmiyorum” tamamen serbest

Kabul Kriteri
• Aynı input → farklı ama tutarlı hipotezler üretilebiliyor.

⸻

🧪 Milestone A4 — Adversarial Toy Benchmark

Amaç

Gerçekten semantic reasoning test etmek.

Task özellikleri
• misleading coverage
• state-dependent bug
• test doğru, sebep dolaylı
• “önemsiz görünen satır” asıl neden

Her task:
• failing test
• ham coverage
• LLM için kasıtlı belirsizlik

Çıktılar
• evaluation/tasks/
• metadata.json

Kabul Kriteri
• Coverage’a bakarak yanlış yola sapılabilen task’lar var.

⸻

⚙️ Milestone A5 — Fully Agentic Run Engine

Amaç

Baseline vs Agentic aynı altyapı, farklı zeka.

Modlar
• Baseline
• Tek LLM
• ReAct benzeri
• No critic, no reflection
• Agentic
• Full agent graph

Her run:
• tüm agent mesajları
• tool çağrıları
• reflection kararları

Çıktılar
• evaluation/run_all.py
• runs/<task>/<run_id>/

Kabul Kriteri
• Tek komutla tüm deney seti koşuyor.

⸻

📊 Milestone A6 — LLM-Based Evaluation (No Hard Metrics)

Amaç

“Doğru / yanlış” bile LLM tarafından yorumlansın.

Evaluation Agent

Input:
• full run log
• final outcome

Soru seti:
• “Ajan makul mü davrandı?”
• “Yanlış ama özgüvenli miydi?”
• “Ne zaman durmalıydı?”

Çıktı:

{
"behavior": "reasonable|confused|overconfident",
"failure_type": "...",
"commentary": "..."
}

Kod:
• sadece sayar
• istatistik çıkarır

Kabul Kriteri
• Negatif sonuçlar anlamlı anlatı üretiyor.

⸻

📝 Milestone A7 — Writing & Defense

Ana vurgu
• Bu bir başarı optimizasyonu çalışması değil
• Bu bir sınır keşfi çalışması

Paper başlığı önerisi:

When LLMs Are Left Alone: An Agentic Study of Semantic Interpretation Without Hand-Coded Control

Threats to Validity
• model bağımlılığı
• prompt sensitivity
• LLM-as-judge riski (bilinçli olarak kabul)
