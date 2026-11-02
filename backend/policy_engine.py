"""Deterministic policy engine for VaultPay Agent.

CORE RULE: the LLM never decides whether money moves. This module does.
evaluate() is a pure function - same input, same verdict, every time.
Check order is fixed by the blueprint and must not be reordered.
"""
from __future__ import annotations

DEFAULT_POLICY = {
    "total_budget_usd": 60.0,
    "per_item_ask_above_usd": 25.0,
    "per_item_hard_cap_usd": 100.0,
    "blocked_categories": ["subscription"],
    "allowed_categories": [],  # empty = all non-blocked categories allowed
    "min_seller_rating": 4.0,
    "auto_allow": True,
}

_FIELDS = {
    "total_budget_usd": (int, float),
    "per_item_ask_above_usd": (int, float),
    "per_item_hard_cap_usd": (int, float),
    "blocked_categories": (list,),
    "allowed_categories": (list,),
    "min_seller_rating": (int, float),
    "auto_allow": (bool,),
}


def validate_policy(policy: dict) -> dict:
    """Strict validation. Raises ValueError on anything malformed.
    Returns a normalised copy (categories lower-cased)."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a JSON object")
    out = dict(DEFAULT_POLICY)
    for key, value in policy.items():
        if key not in _FIELDS:
            raise ValueError(f"unknown policy field: {key}")
        if not isinstance(value, _FIELDS[key]) or isinstance(value, bool) and key != "auto_allow":
            raise ValueError(f"policy field {key} has wrong type")
        out[key] = value
    for k in ("total_budget_usd", "per_item_ask_above_usd", "per_item_hard_cap_usd"):
        if out[k] < 0:
            raise ValueError(f"policy field {k} must be >= 0")
    if not (0 <= out["min_seller_rating"] <= 5):
        raise ValueError("min_seller_rating must be between 0 and 5")
    out["blocked_categories"] = [str(c).strip().lower() for c in out["blocked_categories"]]
    out["allowed_categories"] = [str(c).strip().lower() for c in out["allowed_categories"]]
    return out


def _get(item, key, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def evaluate(policy: dict, item, spent_so_far: float) -> dict:
    """Return {"verdict": "ALLOW"|"ASK"|"DENY", "reason": str}.

    Order (blueprint Step 10, exact):
      1. blocked category            -> DENY
      2. price > hard cap            -> DENY
      3. seller rating < minimum     -> DENY
      4. spent + price > budget      -> DENY
      5. price > ask threshold       -> ASK
      else                           -> ALLOW
    """
    p = validate_policy(policy)
    price = float(_get(item, "price", 0))
    category = str(_get(item, "category", "")).strip().lower()
    rating = float(_get(item, "seller_rating", _get(item, "rating", 0)))
    name = _get(item, "name", "item")

    if category in p["blocked_categories"]:
        return {"verdict": "DENY",
                "reason": f"DENY: '{category}' is a blocked category in your policy. No PayPal order was created for {name}."}
    if p["allowed_categories"] and category not in p["allowed_categories"]:
        return {"verdict": "DENY",
                "reason": f"DENY: '{category}' is not in the allowed categories {p['allowed_categories']}."}
    if price > p["per_item_hard_cap_usd"]:
        return {"verdict": "DENY",
                "reason": f"DENY: ${price:.2f} exceeds the per-item hard cap of ${p['per_item_hard_cap_usd']:.2f}."}
    if rating < p["min_seller_rating"]:
        return {"verdict": "DENY",
                "reason": f"DENY: seller rating {rating} is below the minimum {p['min_seller_rating']}."}
    if spent_so_far + price > p["total_budget_usd"]:
        return {"verdict": "DENY",
                "reason": f"DENY: ${spent_so_far:.2f} already spent + ${price:.2f} would exceed the total budget of ${p['total_budget_usd']:.2f}."}
    if price > p["per_item_ask_above_usd"]:
        return {"verdict": "ASK",
                "reason": f"ASK: ${price:.2f} is above your ask threshold of ${p['per_item_ask_above_usd']:.2f}, so a human must approve first."}
    return {"verdict": "ALLOW",
            "reason": f"ALLOW: ${price:.2f} is within budget (${p['total_budget_usd']:.2f}), under the ask threshold, category '{category}' is allowed and seller rating {rating} meets the minimum."}
