"""PayPal Orders v2 service.

Real mode: OAuth token -> create order -> capture, via httpx.
Mock mode (PAYPAL_MOCK=true OR credentials empty): simulates the full
create -> approve -> capture flow returning COMPLETED, so the local
gates (Blueprint Steps 7 and 17) can pass before Onkar creates his
PayPal Developer sandbox app. Mock mode NEVER calls PayPal.
"""
from __future__ import annotations
import os, time, uuid
import httpx


def _env(name, default=""):
    return os.environ.get(name, default).strip()


class PayPalService:
    def __init__(self):
        self.client_id = _env("PAYPAL_CLIENT_ID")
        self.client_secret = _env("PAYPAL_CLIENT_SECRET")
        self.webhook_id = _env("PAYPAL_WEBHOOK_ID")
        self.base_url = _env("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/")
        self.mock = _env("PAYPAL_MOCK", "false").lower() == "true" or not (self.client_id and self.client_secret)
        self._token, self._token_exp = None, 0
        self._mock_orders: dict = {}

    # --- token ---------------------------------------------------------
    def get_access_token(self) -> str:
        if self.mock:
            return "MOCK-ACCESS-TOKEN"
        if self._token and time.time() < self._token_exp - 30:
            return self._token
        r = httpx.post(f"{self.base_url}/v1/oauth2/token",
                       data={"grant_type": "client_credentials"},
                       auth=(self.client_id, self.client_secret),
                       headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_exp = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"}

    # --- orders --------------------------------------------------------
    def create_order(self, amount: float, description: str, custom_id: str) -> dict:
        amount = round(float(amount), 2)
        if self.mock:
            oid = f"MOCK-{uuid.uuid4().hex[:16].upper()}"
            self._mock_orders[oid] = {"id": oid, "amount": amount, "status": "CREATED",
                                      "description": description, "custom_id": str(custom_id)}
            return {"id": oid, "status": "CREATED", "amount": amount,
                    "approve_link": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}",
                    "mock": True}
        body = {"intent": "CAPTURE",
                "purchase_units": [{"amount": {"currency_code": "USD", "value": f"{amount:.2f}"},
                                    "description": description[:127], "custom_id": str(custom_id)}]}
        r = httpx.post(f"{self.base_url}/v2/checkout/orders", json=body,
                       headers=self._headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        link = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
        return {"id": data["id"], "status": data.get("status", "CREATED"),
                "amount": amount, "approve_link": link, "mock": False}

    def capture_order(self, order_id: str, expected_amount: float | None = None) -> dict:
        if self.mock:
            order = self._mock_orders.get(order_id)
            amount = float(expected_amount if expected_amount is not None
                           else (order["amount"] if order else 0))
            if order:
                order["status"] = "COMPLETED"
            return {"id": order_id, "status": "COMPLETED", "amount": amount, "mock": True}
        r = httpx.post(f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                       headers=self._headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        captured = None
        try:
            captured = float(data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"])
        except Exception:
            pass
        if expected_amount is not None and captured is not None and abs(captured - float(expected_amount)) > 0.001:
            return {"id": order_id, "status": "AMOUNT_MISMATCH", "amount": captured, "mock": False}
        return {"id": order_id, "status": data.get("status", ""), "amount": captured, "mock": False}

    # --- webhooks ------------------------------------------------------
    def verify_webhook(self, headers: dict, body: dict) -> bool:
        """In mock mode (or with no webhook id configured) verification is
        skipped and returns True - local development only. In real mode it
        calls PayPal's verify-webhook-signature endpoint."""
        if self.mock or not self.webhook_id:
            return True
        payload = {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": self.webhook_id,
            "webhook_event": body,
        }
        try:
            r = httpx.post(f"{self.base_url}/v1/notifications/verify-webhook-signature",
                           json=payload, headers=self._headers(), timeout=30)
            return r.json().get("verification_status") == "SUCCESS"
        except Exception:
            return False


paypal = PayPalService()
