# Pydantic Schema Integration Raporu

**Tarih:** 1 Ocak 2026  
**Konu:** Gemini API'de Pydantic Schema Entegrasyonu

---

## 🎯 Amaç

Critic agent çıktısından `EvaluationResult` çıkarımını otomatikleştirmek ve API seviyesinde JSON schema enforcement sağlamak.

---

## 📋 Yapılan Değişiklikler

### 1. schemas/models.py - CriticResponse Model

Yeni Pydantic model eklendi:

```python
class CriticResponse(BaseModel):
    """Extended evaluation response from Critic agent with detailed analysis."""
    behavior: Literal["reasonable", "confused", "overconfident"]
    failure_type: str
    commentary: str
    challenges: list[str]
    alternatives: list[str]
    missing_evidence: list[str]
    verdict: Literal["ACCEPT", "REVISE", "REJECT"]

    def to_evaluation_result(self) -> "EvaluationResult":
        """Convert to simplified EvaluationResult for summary."""
        # Build comprehensive commentary from all fields
        ...
```

### 2. llm_client.py - generate_json() Güncelleme

`response_schema` parametresi eklendi, Pydantic model'dan JSON Schema'ya otomatik dönüşüm:

```python
def generate_json(self, system: str, user: str, response_schema: type | dict | None = None) -> LLMResponse:
    generation_config: dict = {"response_mime_type": "application/json"}

    if response_schema is not None:
        # Check if it's a Pydantic model class
        if hasattr(response_schema, "model_json_schema"):
            # Convert Pydantic model to JSON schema dict
            generation_config["response_schema"] = response_schema.model_json_schema()
        else:
            generation_config["response_schema"] = response_schema

    json_model = genai.GenerativeModel(
        self._base_model_id,
        generation_config=generation_config
    )
    ...
```

### 3. custom_session.py - Schema Geçirme

Agent çağrılarında ilgili Pydantic model'lar schema olarak geçiriliyor:

```python
if agent_name == "analysis":
    llm_response = self.llm.generate_json(
        system=prompt, user=user_message, response_schema=SemanticHypothesis
    )
elif agent_name == "critic":
    llm_response = self.llm.generate_json(
        system=prompt, user=user_message, response_schema=CriticResponse
    )
```

### 4. Parse Fonksiyonları Basitleştirildi

Pydantic'in `model_validate_json()` metodu kullanılarak validation tek satıra indirildi:

````python
def parse_hypothesis_from_json(json_text: str) -> SemanticHypothesis | None:
    sanitized = re.sub(r"```(?:json)?", "", json_text).strip()
    try:
        return SemanticHypothesis.model_validate_json(sanitized)
    except Exception as e:
        print(f"⚠️ Failed to parse hypothesis JSON: {e}")
        return None

def parse_evaluation_from_json(json_text: str) -> EvaluationResult | None:
    sanitized = re.sub(r"```(?:json)?", "", json_text).strip()
    try:
        critic_response = CriticResponse.model_validate_json(sanitized)
        return critic_response.to_evaluation_result()
    except Exception as e:
        print(f"⚠️ Failed to parse evaluation JSON: {e}")
        return None
````

### 5. Prompt'lar Basitleştirildi

JSON schema artık API seviyesinde enforce edildiğinden, prompt'lardaki detaylı format açıklamaları kaldırıldı:

**Öncesi (analysis.txt):**

````
You MUST output ONLY valid JSON in this exact schema:
```json
{
  "hypothesis": "...",
  ...
}
````

```

**Sonrası:**
```

Your response will be automatically structured into these fields:

- hypothesis: Your main theory about the bug...
- confidence_level: LOW, MEDIUM, or HIGH...
  ...
  Focus on substance, not formatting.

````

### 6. main.py - parsed_evaluation Geçirme

`SummaryBuilder`'a `parsed_evaluation` parametresi eklendi:

```python
summary = SummaryBuilder(
    model_id=config.model_id,
    tool_call_count=counter.count,
    hypothesis_text=run_result.analysis_text,
    evaluation_text=run_result.critic_text,
    parsed_hypothesis=run_result.parsed_hypothesis,
    parsed_evaluation=run_result.parsed_evaluation,  # YENİ
).build(timestamp=timestamp)
````

---

## ✅ Test Sonucu

```bash
python3 main.py --task misleading_coverage --run-id schema_test2 --mode agentic
```

**Çıktı:**

```
📊 Using JSON mode with SemanticHypothesis schema...
✅ Parsed hypothesis: The `calculate_discount` function...
   Confidence: HIGH

📊 Using JSON mode with CriticResponse schema...
✅ Parsed evaluation: behavior=reasonable
```

**summary.json içeriği:**

- `hypothesis`: Tüm alanlar dolu (hypothesis, confidence_level, assumptions, evidence, what_might_be_missing, next_question)
- `evaluation`: behavior, failure_type, commentary (challenges, alternatives, missing_evidence, verdict dahil)

---

## 📊 Avantajlar

| Özellik            | Önceki Durum              | Şimdi                                   |
| ------------------ | ------------------------- | --------------------------------------- |
| JSON Validation    | Prompt-based (unreliable) | API-level enforcement                   |
| Schema Değişikliği | Prompt güncelleme gerekli | Pydantic model güncelle                 |
| Parse Karmaşıklığı | Manuel field extraction   | `model_validate_json()`                 |
| Fallback           | Manuel default'lar        | Pydantic default + graceful degradation |
| Type Safety        | Yok                       | Pydantic Literal types                  |

---

## 📁 Değiştirilen Dosyalar

1. `schemas/models.py` - CriticResponse model eklendi
2. `schemas/__init__.py` - CriticResponse export eklendi
3. `llm_client.py` - generate_json() response_schema desteği
4. `custom_session.py` - Parse fonksiyonları + schema geçirme
5. `main.py` - parsed_evaluation parametresi
6. `prompts/analysis.txt` - Basitleştirildi
7. `prompts/critic.txt` - Basitleştirildi

---

_Rapor: 1 Ocak 2026_
