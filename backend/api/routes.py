from typing import Dict, Any, List
import httpx
from fastapi import APIRouter, HTTPException

from backend.models.schemas import (
    CreateOrderRequest,
    CustomerIntakeRequest,
    CustomerIntakeResponse,
    DisputeClaim,
    PayPalRefundResult,
    RefundTriggerRequest,
    ResolutionAction,
    ResolutionVerdict,
    SimulationResultResponse,
)
from backend.paypal.client import PayPalSandboxClient
from backend.agents.swarm import PayResolveSwarm
from backend.agents.tools import SIMULATION_SCENARIOS, execute_paypal_settlement

router = APIRouter()
paypal_client = PayPalSandboxClient()
swarm = PayResolveSwarm()

# In-memory store for active demo session (claims & verdicts)
CLAIMS_STORE: Dict[str, DisputeClaim] = {}
VERDICTS_STORE: Dict[str, ResolutionVerdict] = {}


# ============================================================================
# PAYPAL SANDBOX LIVE ENDPOINTS
# ============================================================================

@router.get("/paypal/status")
async def get_paypal_sandbox_status() -> Dict[str, Any]:
    """Verify live PayPal Sandbox OAuth2 token & Customer Disputes API connectivity."""
    try:
        return await paypal_client.verify_sandbox_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PayPal Sandbox connection error: {exc}")


@router.post("/paypal/orders")
async def create_paypal_sandbox_order(req: CreateOrderRequest) -> Dict[str, Any]:
    """Create a live PayPal Checkout Order in Sandbox (/v2/checkout/orders)."""
    try:
        return await paypal_client.create_order(
            amount_value=req.amount_value,
            currency_code=req.currency_code,
            description=req.description,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"PayPal Sandbox order error: {exc.response.text}",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/paypal/orders/{order_id}/capture")
async def capture_paypal_sandbox_order(order_id: str) -> Dict[str, Any]:
    """Capture an approved PayPal Checkout Order in Sandbox (/v2/checkout/orders/{id}/capture)."""
    try:
        return await paypal_client.capture_order(order_id=order_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"PayPal capture error: {exc.response.text}",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/paypal/captures/{capture_id}")
async def get_paypal_capture(capture_id: str) -> Dict[str, Any]:
    """Inspect a PayPal Sandbox payment capture (/v2/payments/captures/{id})."""
    try:
        return await paypal_client.get_capture_details(capture_id=capture_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"PayPal capture lookup error: {exc.response.text}",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/paypal/captures/{capture_id}/refund", response_model=PayPalRefundResult)
async def trigger_paypal_refund(
    capture_id: str, req: RefundTriggerRequest
) -> PayPalRefundResult:
    """
    Trigger a live PayPal Sandbox refund (/v2/payments/captures/{id}/refund).
    Supports both real captured Sandbox payments and simulated demo capture IDs.
    """
    try:
        amount_float = float(req.amount_value) if req.amount_value else 89.99
        action = (
            ResolutionAction.AUTO_REFUND_PARTIAL.value
            if req.amount_value
            else ResolutionAction.AUTO_REFUND_FULL.value
        )
        res = await execute_paypal_settlement(
            capture_id=capture_id,
            action=action,
            refund_amount=amount_float,
            currency=req.currency_code,
            claim_id=f"DIRECT-{capture_id}",
        )
        return PayPalRefundResult(
            id=res.get("paypal_refund_id") or "PP-RFD-UNKNOWN",
            status=res.get("status", "COMPLETED"),
            amount_value=res.get("amount_value", f"{amount_float:.2f}"),
            currency_code=res.get("currency_code", req.currency_code),
            create_time=res.get("create_time", ""),
            is_sandbox_live=True,
            note=res.get("mode"),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PayPal refund execution failed: {exc}")


@router.get("/paypal/disputes")
async def list_paypal_disputes() -> Dict[str, Any]:
    """List customer disputes from the live PayPal Sandbox API (/v1/customer/disputes)."""
    try:
        return await paypal_client.list_disputes()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PayPal disputes lookup failed: {exc}")


# ============================================================================
# MULTI-AGENT DISPUTE INTAKE, RESOLUTION & SIMULATION ENDPOINTS
# ============================================================================

@router.post("/disputes/intake", response_model=CustomerIntakeResponse)
async def customer_dispute_intake(req: CustomerIntakeRequest) -> CustomerIntakeResponse:
    """
    Conversational Customer Intake Agent endpoint:
    Parses a natural-language buyer statement into a structured `DisputeClaim`
    and returns an empathetic response + trace step.
    """
    intake_res = await swarm.run_customer_intake(req)
    CLAIMS_STORE[intake_res.claim.claim_id] = intake_res.claim
    return intake_res


@router.post("/disputes/resolve", response_model=ResolutionVerdict)
async def resolve_dispute_claim(claim: DisputeClaim) -> ResolutionVerdict:
    """
    Run the full 6-Agent Swarm on a structured `DisputeClaim` and execute
    instant PayPal Sandbox settlement when approved.
    """
    CLAIMS_STORE[claim.claim_id] = claim
    verdict = await swarm.evaluate_and_resolve_claim(claim)
    VERDICTS_STORE[claim.claim_id] = verdict
    return verdict


@router.get("/disputes/scenarios")
async def list_simulation_scenarios() -> List[Dict[str, Any]]:
    """Return all preset multi-agent dispute simulation scenarios."""
    return [
        {
            "scenario_id": k,
            "title": v["title"],
            "description": v["description"],
            "claim_preview": v["claim_payload"],
        }
        for k, v in SIMULATION_SCENARIOS.items()
    ]


@router.post("/disputes/simulate/{scenario_id}", response_model=SimulationResultResponse)
async def simulate_dispute_scenario(scenario_id: str) -> SimulationResultResponse:
    """
    Execute an end-to-end simulation for a preset scenario:
    1. Runs Customer Intake Agent on the scenario's buyer statement.
    2. Dispatches the 6-Agent Swarm (Evidence, Fraud, Policy, Arbiter, PayPal Settlement).
    3. Stores and returns the complete claim, empathetic reply, and `ResolutionVerdict`.
    """
    if scenario_id not in SIMULATION_SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario_id}'. Valid scenarios: {list(SIMULATION_SCENARIOS.keys())}",
        )

    scenario = SIMULATION_SCENARIOS[scenario_id]
    payload = dict(scenario["claim_payload"])

    intake_req = CustomerIntakeRequest(
        customer_email=payload["customer_email"],
        merchant_id=payload["merchant_id"],
        transaction_id=payload["transaction_id"],
        capture_id=payload.get("capture_id"),
        amount=payload["amount"],
        currency=payload.get("currency", "USD"),
        customer_message=payload["customer_statement"],
        tracking_number=payload.get("tracking_number"),
        evidence_urls=payload.get("evidence_urls", []),
    )
    intake_res = await swarm.run_customer_intake(intake_req)

    # Preserve canonical scenario claim_id & claim_type for deterministic testing
    claim = DisputeClaim(**payload)
    CLAIMS_STORE[claim.claim_id] = claim

    verdict = await swarm.evaluate_and_resolve_claim(
        claim=claim,
        initial_intake_trace=intake_res.intake_trace,
    )
    VERDICTS_STORE[claim.claim_id] = verdict

    return SimulationResultResponse(
        scenario_id=scenario_id,
        scenario_title=scenario["title"],
        empathetic_intake_reply=intake_res.empathetic_reply,
        claim=claim,
        verdict=verdict,
    )


@router.get("/disputes")
async def list_processed_disputes() -> Dict[str, Any]:
    """Return all processed dispute claims, verdicts, and aggregate merchant metrics."""
    items = []
    total_disputed = 0.0
    total_refunded = 0.0
    auto_resolved_count = 0
    fraud_blocked_usd = 0.0

    for claim_id, claim in CLAIMS_STORE.items():
        verdict = VERDICTS_STORE.get(claim_id)
        total_disputed += claim.amount
        if verdict:
            if verdict.action in (
                ResolutionAction.AUTO_REFUND_FULL,
                ResolutionAction.AUTO_REFUND_PARTIAL,
            ):
                total_refunded += verdict.refund_amount or 0.0
                auto_resolved_count += 1
            elif verdict.action == ResolutionAction.REJECT_CLAIM:
                fraud_blocked_usd += claim.amount
                auto_resolved_count += 1

        items.append(
            {
                "claim": claim,
                "verdict": verdict,
            }
        )

    return {
        "count": len(items),
        "metrics": {
            "total_claims": len(items),
            "auto_resolved_count": auto_resolved_count,
            "total_disputed_usd": round(total_disputed, 2),
            "total_refunded_usd": round(total_refunded, 2),
            "fraud_blocked_usd": round(fraud_blocked_usd, 2),
            "chargeback_fees_saved_usd": auto_resolved_count * 20.0,
        },
        "items": items,
    }


@router.get("/disputes/{claim_id}")
async def get_dispute_details(claim_id: str) -> Dict[str, Any]:
    """Fetch a single dispute claim and its full multi-agent verdict & audit trace."""
    if claim_id not in CLAIMS_STORE:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return {
        "claim": CLAIMS_STORE[claim_id],
        "verdict": VERDICTS_STORE.get(claim_id),
    }

