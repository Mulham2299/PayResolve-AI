import os
import base64
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()


class PayPalSandboxClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("PAYPAL_CLIENT_SECRET", "")
        self.api_base = api_base or os.getenv("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
        self._cached_token: Optional[str] = None

    async def get_access_token(self) -> str:
        """Fetch OAuth2 Bearer token using Client ID & Secret."""
        if not self.client_id or not self.client_secret:
            raise ValueError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be configured.")

        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{self.api_base}/v1/oauth2/token", headers=headers, data=data)
            resp.raise_for_status()
            res_json = resp.json()
            self._cached_token = res_json.get("access_token")
            return self._cached_token

    async def _get_auth_headers(self) -> Dict[str, str]:
        token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_capture_details(self, capture_id: str) -> Dict[str, Any]:
        """Fetch details of a completed PayPal payment capture."""
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.api_base}/v2/payments/captures/{capture_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def issue_refund(
        self,
        capture_id: str,
        amount_value: Optional[str] = None,
        currency_code: str = "USD",
        note_to_payer: Optional[str] = "PayResolve AI: Automated Dispute Resolution",
    ) -> Dict[str, Any]:
        """
        Issue full or partial refund for a captured payment.
        If amount_value is omitted, PayPal executes a full refund.
        """
        headers = await self._get_auth_headers()
        payload: Dict[str, Any] = {"note_to_payer": note_to_payer}

        if amount_value:
            payload["amount"] = {
                "value": amount_value,
                "currency_code": currency_code,
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.api_base}/v2/payments/captures/{capture_id}/refund",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_disputes(self) -> Dict[str, Any]:
        """Query PayPal Customer Disputes API (Sandbox)."""
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.api_base}/v1/customer/disputes", headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def create_order(
        self,
        amount_value: str = "89.99",
        currency_code: str = "USD",
        description: str = "PayResolve AI Sandbox Order",
    ) -> Dict[str, Any]:
        """Create a PayPal Checkout Order in Sandbox (/v2/checkout/orders)."""
        headers = await self._get_auth_headers()
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "description": description,
                    "amount": {
                        "currency_code": currency_code,
                        "value": amount_value,
                    },
                }
            ],
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.api_base}/v2/checkout/orders",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """Capture an approved PayPal Checkout Order (/v2/checkout/orders/{id}/capture)."""
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.api_base}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                json={},
            )
            resp.raise_for_status()
            return resp.json()

    async def verify_sandbox_status(self) -> Dict[str, Any]:
        """Verify live PayPal Sandbox OAuth2 token generation and Disputes endpoint connectivity."""
        token = await self.get_access_token()
        disputes_data = await self.list_disputes()
        dispute_items = disputes_data.get("items", [])
        return {
            "connected": True,
            "api_base": self.api_base,
            "token_prefix": f"{token[:12]}..." if token else None,
            "sandbox_dispute_count": len(dispute_items),
        }

