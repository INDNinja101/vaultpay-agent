import copy
from policy_engine import DEFAULT_POLICY, evaluate, validate_policy
import pytest

P = copy.deepcopy(DEFAULT_POLICY)
ITEM = {"name": "LED String Lights 10m", "price": 18.0, "category": "fest supplies", "seller_rating": 4.6}


def ev(item=None, spent=0.0, policy=None):
    return evaluate(policy or P, item or ITEM, spent)


def test_allow_happy_path():
    r = ev()
    assert r["verdict"] == "ALLOW" and "ALLOW" in r["reason"]

def test_rule1_blocked_category_deny():
    r = ev({**ITEM, "category": "subscription", "price": 5.0})
    assert r["verdict"] == "DENY" and "blocked category" in r["reason"]

def test_rule2_hard_cap_deny():
    r = ev({**ITEM, "price": 120.0})
    assert r["verdict"] == "DENY" and "hard cap" in r["reason"]

def test_rule3_low_rating_deny():
    r = ev({**ITEM, "seller_rating": 3.5})
    assert r["verdict"] == "DENY" and "rating" in r["reason"]

def test_rule4_budget_deny():
    r = ev({**ITEM, "price": 20.0}, spent=45.0)  # 45+20=65 > 60
    assert r["verdict"] == "DENY" and "budget" in r["reason"]

def test_rule5_ask_above_threshold():
    r = ev({**ITEM, "price": 31.0})
    assert r["verdict"] == "ASK" and "ask threshold" in r["reason"]

# --- boundaries ---------------------------------------------------------
def test_boundary_price_exactly_at_ask_threshold_allows():
    assert ev({**ITEM, "price": 25.0})["verdict"] == "ALLOW"  # > threshold asks, == does not

def test_boundary_price_exactly_at_hard_cap_not_denied_by_cap():
    # 100 == cap (not >), but 100 > budget 60, so DENY must come from budget rule
    r = ev({**ITEM, "price": 100.0})
    assert r["verdict"] == "DENY" and "budget" in r["reason"]

def test_boundary_rating_exactly_at_minimum_allows():
    assert ev({**ITEM, "seller_rating": 4.0})["verdict"] == "ALLOW"

def test_boundary_spent_plus_price_exactly_at_budget_allows():
    assert ev({**ITEM, "price": 20.0}, spent=40.0)["verdict"] == "ALLOW"  # 40+20=60, not >

def test_boundary_blocked_beats_everything():
    # blocked + over cap + low rating: first rule wins
    r = ev({**ITEM, "category": "Subscription", "price": 999.0, "seller_rating": 1.0})
    assert r["verdict"] == "DENY" and "blocked category" in r["reason"]

def test_validate_rejects_garbage():
    with pytest.raises(ValueError):
        validate_policy({"total_budget_usd": "sixty"})
    with pytest.raises(ValueError):
        validate_policy({"unknown_field": 1})
    with pytest.raises(ValueError):
        validate_policy("not a dict")
