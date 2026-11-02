"""Agent orchestrator.

The LLM (when LLM_API_KEY is set) may PARSE text and EXPLAIN results.
It never decides a verdict - policy_engine.evaluate() does that.
With no LLM key, a deterministic local fallback parser is used, so the
whole app runs offline. Fallback defaults err toward ASK, never ALLOW,
by relying on the default policy's ask threshold.
"""
from __future__ import annotations
import json, os, re
from pathlib import Path
import httpx
from policy_engine import DEFAULT_POLICY, validate_policy

_CATALOGUE_PATHS = [Path(__file__).parent / "catalogue.json",
                    Path(__file__).parent.parent / "catalogue.json"]


def load_catalogue() -> list[dict]:
    for p in _CATALOGUE_PATHS:
        if p.exists():
            return json.loads(p.read_text())
    return []


# ---------------------------------------------------------------- LLM --
def _llm_json(system: str, user: str) -> dict | None:
    """Best-effort LLM call (OpenAI-compatible). Returns None on any failure."""
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        return None
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    try:
        r = httpx.post(f"{base}/chat/completions",
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": model, "response_format": {"type": "json_object"},
                             "messages": [{"role": "system", "content": system},
                                          {"role": "user", "content": user}]},
                       timeout=30)
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


# ------------------------------------------------------- policy parsing --
def parse_policy_text(text: str) -> dict:
    """Plain language -> policy JSON. LLM first if available, else regex fallback."""
    llm = _llm_json(
        "Convert spending rules into JSON with keys: total_budget_usd, "
        "per_item_ask_above_usd, per_item_hard_cap_usd, blocked_categories, "
        "allowed_categories, min_seller_rating, auto_allow. Numbers only, no prose.",
        text)
    if llm:
        try:
            return validate_policy({**DEFAULT_POLICY, **llm})
        except Exception:
            pass  # fall through to deterministic fallback
    p = dict(DEFAULT_POLICY)
    t = text.lower()
    m = re.search(r"(?:under|budget|max|limit)[^\d$]*\$?\s*(\d+(?:\.\d+)?)", t)
    if m:
        p["total_budget_usd"] = float(m.group(1))
    m = re.search(r"ask[^\d$]*\$?\s*(\d+(?:\.\d+)?)", t)
    if m:
        p["per_item_ask_above_usd"] = float(m.group(1))
    m = re.search(r"(?:never|no|block|not)[^.]*?(subscription|subscriptions)", t)
    if m:
        p["blocked_categories"] = ["subscription"]
    m = re.search(r"rated?\s*(?:above|over|\+|at least)?\s*(\d+(?:\.\d+)?)\+?", t)
    if m:
        p["min_seller_rating"] = float(m.group(1))
    return validate_policy(p)


# --------------------------------------------------------- task parsing --
_CATEGORY_WORDS = {
    "fest supplies": ["fest", "party", "decoration", "decor", "balloon", "banner", "lights"],
    "textbooks": ["textbook", "book", "notes", "algorithms"],
    "snacks": ["snack", "snacks", "chips", "chocolate", "food", "noodles", "cookies"],
    "subscription": ["subscription", "streaming", "membership"],
}


def parse_task(prompt: str) -> dict:
    t = prompt.lower()
    category = None
    for cat, words in _CATEGORY_WORDS.items():
        if cat in t or any(w in t for w in words):
            category = cat
            break
    qty = 1
    m = re.search(r"\b(\d+)\s*(?:x|items?|pcs?|pieces?)\b", t)
    if m:
        qty = int(m.group(1))
    return {"prompt": prompt, "category": category, "quantity": qty,
            "tokens": [w for w in re.findall(r"[a-z]+", t) if len(w) > 2]}


# --------------------------------------------------- candidate selection --
def select_candidates(parsed: dict, catalogue: list[dict], limit: int = 5) -> list[dict]:
    tokens = set(parsed.get("tokens", []))

    def score(item):
        name_tokens = set(re.findall(r"[a-z]+", item["name"].lower()))
        desc_tokens = set(re.findall(r"[a-z]+", (item.get("description") or "").lower()))
        overlap = len(tokens & name_tokens) * 3 + len(tokens & desc_tokens)
        exact = 100 if item["name"].lower() in parsed["prompt"].lower() else 0
        cat_bonus = 10 if parsed.get("category") and item["category"] == parsed["category"] else 0
        return (exact + cat_bonus + overlap, float(item["seller_rating"]), -float(item["price"]))

    pool = catalogue
    if parsed.get("category"):
        in_cat = [i for i in catalogue if i["category"] == parsed["category"]]
        if in_cat:
            pool = in_cat
    ranked = sorted(pool, key=score, reverse=True)
    out = []
    for item in ranked[:limit]:
        just = (f"{item['name']} (${item['price']:.2f}, {item['category']}, "
                f"seller {item.get('seller','')} rated {item['seller_rating']}) - "
                f"best price/rating fit for this task.")
        out.append({**item, "justification": just})
    return out


def explain(task_prompt: str, events: list[dict]) -> str:
    """Plain-language summary of audit events. Explanation only - it is
    generated AFTER verdicts and can never change one."""
    if not events:
        return "Nothing happened for this task yet."
    paid = [e for e in events if e["type"] == "PAID"]
    asks = [e for e in events if e["type"] == "ASK"]
    denys = [e for e in events if e["type"] == "DENY"]
    parts = [f"For '{task_prompt}':"]
    if paid:
        parts.append(f"{len(paid)} purchase(s) completed via PayPal.")
    if asks:
        parts.append(f"{len(asks)} item(s) paused for your approval.")
    if denys:
        parts.append(f"{len(denys)} item(s) refused by your policy rules.")
    if not (paid or asks or denys):
        parts.append("No purchases were made.")
    return " ".join(parts)
