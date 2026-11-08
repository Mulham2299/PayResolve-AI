import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.append(str(Path(__file__).parent.parent))

from backend.api.main import app
from backend.models.schemas import AgentRole, ResolutionAction


@pytest.mark.asyncio
async def test_health_and_paypal_sandbox_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        health_resp = await ac.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "ok"
        assert health_data["paypal_configured"] is True

        pp_resp = await ac.get("/api/paypal/status")
        assert pp_resp.status_code == 200
        pp_data = pp_resp.json()
        assert pp_data["connected"] is True
        assert pp_data["token_prefix"] is not None


@pytest.mark.asyncio
async def test_all_four_swarm_scenarios():
    transport = ASGITransport(app=app)
    # Disable external LLM call in unit test for fast deterministic execution while keeping live PayPal Sandbox API
    from backend.api.routes import swarm
    swarm._client = None

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Clean Item Not Received -> Full Auto Refund ($89.99)
        r1 = await ac.post("/api/disputes/simulate/clean_inr_refund")
        assert r1.status_code == 200
        d1 = r1.json()
        v1 = d1["verdict"]
        assert v1["action"] == ResolutionAction.AUTO_REFUND_FULL.value
        assert v1["refund_amount"] == 89.99
        assert v1["fraud_risk_score"] < 0.20
        assert v1["paypal_refund_id"] is not None
        assert v1["paypal_refund_id"].startswith("PP-RFD-")
        assert len(v1["audit_trace"]) == 6
        roles_1 = [step["agent"] for step in v1["audit_trace"]]
        assert roles_1 == [
            AgentRole.CUSTOMER_INTAKE.value,
            AgentRole.EVIDENCE_VERIFIER.value,
            AgentRole.FRAUD_RISK_SCORER.value,
            AgentRole.POLICY_AUDITOR.value,
            AgentRole.SUPERVISOR_ARBITER.value,
            AgentRole.PAYPAL_SETTLEMENT.value,
        ]

        # 2. Damaged Item -> 40% Partial Refund ($48.00 of $120.00)
        r2 = await ac.post("/api/disputes/simulate/damaged_partial_refund")
        assert r2.status_code == 200
        v2 = r2.json()["verdict"]
        assert v2["action"] == ResolutionAction.AUTO_REFUND_PARTIAL.value
        assert v2["refund_amount"] == 48.00
        assert v2["fraud_risk_score"] < 0.20
        assert v2["paypal_refund_id"] is not None

        # 3. Opportunistic Fraud -> Claim Rejected
        r3 = await ac.post("/api/disputes/simulate/fraud_claim_rejected")
        assert r3.status_code == 200
        v3 = r3.json()["verdict"]
        assert v3["action"] == ResolutionAction.REJECT_CLAIM.value
        assert v3["fraud_risk_score"] >= 0.65
        assert v3["paypal_refund_id"] is None

        # 4. High Value ($480.00) -> Escalated to Merchant
        r4 = await ac.post("/api/disputes/simulate/high_value_escalation")
        assert r4.status_code == 200
        v4 = r4.json()["verdict"]
        assert v4["action"] == ResolutionAction.ESCALATE_TO_MERCHANT.value
        assert v4["paypal_refund_id"] is None

        # 5. Verify Merchant Dashboard summary metrics
        summary_resp = await ac.get("/api/disputes")
        assert summary_resp.status_code == 200
        metrics = summary_resp.json()["metrics"]
        assert metrics["total_claims"] == 4
        assert metrics["auto_resolved_count"] == 3
        assert metrics["total_refunded_usd"] == 137.99
        assert metrics["fraud_blocked_usd"] == 215.00
        assert metrics["chargeback_fees_saved_usd"] == 60.00

