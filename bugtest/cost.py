"""Per-model token pricing (USD per 1K tokens) for the experiment cost report.

Sources:
- Claude (claude.com/pricing): sonnet 4.6 $3/M in, $15/M out; opus 4.7 $15/M in, $75/M out;
  haiku 4.5 $1/M in, $5/M out.
- NVIDIA Build endpoints expose third-party / open-source models at $0.0 to the user
  during free tier; we record nominal "list" prices to indicate compute weight:
  gpt-oss-120b ≈ $0.15/M in $0.60/M out (OpenAI public pricing for gpt-oss-120b),
  llama-4-maverick-17b ≈ $0.20/M in $0.60/M out (estimated).

Numbers are USD per million tokens; convert to /1K by *0.001.
"""

from __future__ import annotations

PRICE_USD_PER_M_TOKENS: dict[str, tuple[float, float]] = {
    # Claude CLI
    "sonnet": (3.0, 15.0),
    "opus": (15.0, 75.0),
    "haiku": (1.0, 5.0),
    # NVIDIA-hosted OSS (nominal compute-equivalent list prices)
    "openai/gpt-oss-120b": (0.15, 0.60),
    "meta/llama-4-maverick-17b-128e-instruct": (0.20, 0.60),
}


def estimate_cost_usd(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return estimated USD cost for one call given input/output token counts."""
    prices = PRICE_USD_PER_M_TOKENS.get(model_id)
    if not prices:
        return 0.0
    in_price, out_price = prices
    return (prompt_tokens * in_price + completion_tokens * out_price) / 1_000_000.0
