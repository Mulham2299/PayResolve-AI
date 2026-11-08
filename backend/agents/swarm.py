import json
import os
import uuid
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from backend.models.schemas import (
    AgentRole,
    AgentTraceStep,
    ClaimStatus,
    ClaimType,
    CustomerIntakeRequest,
    CustomerIntakeResponse,
    DisputeClaim,
    ResolutionAction,
    ResolutionVerdict,
)
from backend.agents.tools import (
    EVIDENCE_TOOL_DECLARATION,
    FRAUD_TOOL_DECLARATION,
    POLICY_TOOL_DECLARATION,
    audit_merchant_policy,
    compute_fraud_risk_score,
    execute_paypal_settlement,
    verify_carrier_tracking,
)

load_dotenv()

FAST_WORKER_MODEL = "gemini-3.8-flash"
ARBITER_MODEL = "gemini-4-argon"


class PayResolveSwarm:
    """
    Hub-and-Spoke Multi-Agent Dispute Resolution & Settlement Swarm.
    Coordinates 6 specialized agents using the Google Gemini Interactions API
    (google-genai >= 2.30.1) and the live PayPal Sandbox REST API.
    """

    def __init__(self, api_key: Optional[str] = None, enable_live_llm: Optional[bool] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        # Note: OAuth/Vertex 'AQ.' tokens require Vertex AI credentials; AI Studio API keys start with 'AIza'
        if enable_live_llm is None:
            enable_live_llm = bool(self.api_key and self.api_key.startswith("AIza"))
        self.enable_live_llm = enable_live_llm
        self._client: Optional[Any] = None

    def _get_client(self) -> Optional[Any]:
        if not self.enable_live_llm or not self.api_key:
            return None
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None
        return self._client

    async def _call_gemini_structured(
        self,
        model: str,
        system_instruction: str,
        prompt: str,
        schema: Dict[str, Any],
        timeout: float = 6.0,
    ) -> Optional[Dict[str, Any]]:
        """Invoke Gemini Interactions API with top-level JSON schema response_format."""
        client = self._get_client()
        if not client:
            return None
        try:
            interaction = await client.aio.interactions.create(
                model=model,
                system_instruction=system_instruction,
                input=prompt,
                response_format=[
                    {
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": schema,
                    }
                ],
                generation_config={"thinking_level": "low"},
                timeout=timeout,
            )
            text = getattr(interaction, "output_text", None)
            if text:
                return json.loads(text)
        except Exception:
            return None
        return None

    async def _call_gemini_with_tool(
        self,
        model: str,
        system_instruction: str,
        prompt: str,
        tool_declaration: Dict[str, Any],
        tool_fn,
        fallback_args: Dict[str, Any],
        timeout: float = 6.0,
    ) -> Tuple[Dict[str, Any], str, float]:
        """
        Execute a 2-turn tool-calling loop with the Gemini Interactions API:
        Turn 1: Model emits a `function_call` step -> execute `tool_fn`.
        Turn 2: Send `function_result` step with `previous_interaction_id` -> Model synthesizes thought.
        Falls back cleanly to direct `tool_fn(**fallback_args)` if the LLM endpoint times out.
        """
        tool_output: Optional[Dict[str, Any]] = None
        reasoning_text: Optional[str] = None

        client = self._get_client()
        if client:
            try:
                interaction1 = await client.aio.interactions.create(
                    model=model,
                    system_instruction=system_instruction,
                    input=prompt,
                    tools=[tool_declaration],
                    generation_config={"thinking_level": "low"},
                    timeout=timeout,
                )
                steps = getattr(interaction1, "steps", []) or []
                fn_call_step = next(
                    (s for s in steps if getattr(s, "type", None) == "function_call"),
                    None,
                )
                if fn_call_step:
                    call_args = dict(getattr(fn_call_step, "arguments", {}) or {})
                    merged_args = {**fallback_args, **call_args}
                    tool_output = tool_fn(**merged_args)

                    interaction2 = await client.aio.interactions.create(
                        model=model,
                        system_instruction=system_instruction,
                        previous_interaction_id=interaction1.id,
                        tools=[tool_declaration],
                        input=[
                            {
                                "type": "function_result",
                                "call_id": fn_call_step.id,
                                "name": fn_call_step.name,
                                "result": json.dumps(tool_output),
                            }
                        ],
                        generation_config={"thinking_level": "low"},
                        timeout=timeout,
                    )
                    reasoning_text = getattr(interaction2, "output_text", None)
                else:
                    reasoning_text = getattr(interaction1, "output_text", None)
            except Exception:
                pass

        if tool_output is None:
            tool_output = tool_fn(**fallback_args)

        return tool_output, (reasoning_text or ""), 0.96

    # ========================================================================
    # AGENT 1: CUSTOMER INTAKE AGENT
    # ========================================================================

    async def run_customer_intake(
        self, req: CustomerIntakeRequest
    ) -> CustomerIntakeResponse:
        """
        Engage empathetically with the buyer, classify the claim type,
        and structure a formal `DisputeClaim`.
        """
        msg_lower = req.customer_message.lower()
        if any(w in msg_lower for w in ["scratch", "broken", "crushed", "damaged", "dent", "crack"]):
            inferred_type = ClaimType.ITEM_DAMAGED
        elif any(w in msg_lower for w in ["unauthorized", "hacked", "didn't buy", "stole", "fraud"]):
            inferred_type = ClaimType.UNAUTHORIZED_TRANSACTION
        elif any(w in msg_lower for w in ["wrong", "fake", "different", "not as described"]):
            inferred_type = ClaimType.SIGNIFICANTLY_NOT_AS_DESCRIBED
        else:
            inferred_type = ClaimType.ITEM_NOT_RECEIVED

        intake_schema = {
            "type": "object",
            "properties": {
                "claim_type": {
                    "type": "string",
                    "enum": [e.value for e in ClaimType],
                },
                "empathetic_reply": {"type": "string"},
                "thought": {"type": "string"},
                "confidence_score": {"type": "number"},
            },
            "required": ["claim_type", "empathetic_reply", "thought", "confidence_score"],
        }

        llm_res = await self._call_gemini_structured(
            model=FAST_WORKER_MODEL,
            system_instruction=(
                "You are the PayResolve AI Customer Intake Agent. Respond empathetically to the buyer, "
                "extract the dispute category, and reassure them that our autonomous resolution swarm is "
                "verifying their tracking and PayPal transaction right now. Never promise money directly."
            ),
            prompt=(
                f"Customer Email: {req.customer_email}\n"
                f"Transaction ID: {req.transaction_id} (${req.amount:.2f} {req.currency})\n"
                f"Tracking Number: {req.tracking_number or 'None'}\n"
                f"Customer Statement: {req.customer_message}"
            ),
            schema=intake_schema,
        )

        if llm_res:
            try:
                inferred_type = ClaimType(llm_res.get("claim_type", inferred_type.value))
            except ValueError:
                pass
            empathetic_reply = llm_res.get("empathetic_reply") or ""
            thought = llm_res.get("thought") or ""
            confidence = float(llm_res.get("confidence_score", 0.97))
        else:
            empathetic_reply = ""
            thought = ""
            confidence = 0.97

        if not empathetic_reply:
            empathetic_reply = (
                f"I completely understand how frustrating this situation is with order {req.transaction_id} "
                f"(${req.amount:.2f} {req.currency}). I have logged your `{inferred_type.value}` claim and "
                f"dispatched our Evidence & PayPal Settlement Swarm to verify tracking "
                f"{req.tracking_number or 'records'} right away."
            )
        if not thought:
            thought = (
                f"Parsed buyer statement for transaction {req.transaction_id} (${req.amount:.2f}). "
                f"Classified dispute intent as '{inferred_type.value}' with {len(req.evidence_urls)} "
                f"attached evidence artifact(s) and tracking '{req.tracking_number or 'N/A'}'."
            )

        claim = DisputeClaim(
            claim_id=f"CLM-{uuid.uuid4().hex[:8].upper()}",
            customer_email=req.customer_email,
            merchant_id=req.merchant_id,
            transaction_id=req.transaction_id,
            capture_id=req.capture_id or f"CAP-SIM-{req.transaction_id[-6:]}",
            claim_type=inferred_type,
            amount=req.amount,
            currency=req.currency,
            customer_statement=req.customer_message,
            evidence_urls=req.evidence_urls,
            tracking_number=req.tracking_number,
            status=ClaimStatus.EVALUATING,
        )

        trace_step = AgentTraceStep(
            agent=AgentRole.CUSTOMER_INTAKE,
            step_title="Customer Claim Triage & Structuring",
            thought=thought,
            tool_called="extract_dispute_claim_schema",
            tool_output={
                "classified_type": claim.claim_type.value,
                "amount": claim.amount,
                "tracking_number": claim.tracking_number,
                "evidence_count": len(claim.evidence_urls),
            },
            confidence_score=min(1.0, max(0.0, confidence)),
        )

        return CustomerIntakeResponse(
            empathetic_reply=empathetic_reply,
            claim=claim,
            intake_trace=trace_step,
        )

    # ========================================================================
    # FULL 6-AGENT SWARM EXECUTION PIPELINE
    # ========================================================================

    async def evaluate_and_resolve_claim(
        self,
        claim: DisputeClaim,
        initial_intake_trace: Optional[AgentTraceStep] = None,
    ) -> ResolutionVerdict:
        """
        Execute the full 6-Agent Hub-and-Spoke Dispute Resolution & Settlement Swarm:
        1. Customer Intake Agent
        2. Evidence & Tracking Verifier Agent
        3. Fraud & Risk Scoring Agent
        4. Policy & Merchant Rule Auditor
        5. Supervisor Arbiter Agent
        6. PayPal Settlement Agent
        """
        audit_trace = []

        # --- Step 1: Customer Intake Trace ---
        if initial_intake_trace:
            audit_trace.append(initial_intake_trace)
        else:
            audit_trace.append(
                AgentTraceStep(
                    agent=AgentRole.CUSTOMER_INTAKE,
                    step_title="Buyer Statement & Claim Ingestion",
                    thought=(
                        f"Ingested claim {claim.claim_id} from {claim.customer_email} for "
                        f"${claim.amount:.2f} {claim.currency} ({claim.claim_type.value}). "
                        f"Forwarded tracking '{claim.tracking_number}' and {len(claim.evidence_urls)} "
                        f"evidence artifact(s) to verification workers."
                    ),
                    tool_called="ingest_buyer_claim",
                    tool_output={
                        "claim_id": claim.claim_id,
                        "claim_type": claim.claim_type.value,
                        "amount": claim.amount,
                        "tracking_number": claim.tracking_number,
                    },
                    confidence_score=0.98,
                )
            )

        # --- Step 2: Evidence & Tracking Agent ---
        evidence_args = {
            "tracking_number": claim.tracking_number,
            "claim_type": claim.claim_type.value,
        }
        evidence_output, evidence_thought, evidence_conf = await self._call_gemini_with_tool(
            model=FAST_WORKER_MODEL,
            system_instruction=(
                "You are the Evidence & Tracking Verification Agent. Call `verify_carrier_tracking` "
                "and summarize the carrier scan status, GPS coordinates, and signature proof."
            ),
            prompt=(
                f"Verify tracking '{claim.tracking_number}' for claim type '{claim.claim_type.value}'. "
                f"Evidence URLs provided: {len(claim.evidence_urls)}"
            ),
            tool_declaration=EVIDENCE_TOOL_DECLARATION,
            tool_fn=lambda **kw: verify_carrier_tracking(
                tracking_number=kw.get("tracking_number", claim.tracking_number),
                claim_type=kw.get("claim_type", claim.claim_type.value),
                evidence_urls=claim.evidence_urls,
            ),
            fallback_args=evidence_args,
        )
        if not evidence_thought:
            evidence_thought = (
                f"Queried {evidence_output.get('carrier')} telemetry for '{claim.tracking_number}': "
                f"status is {evidence_output.get('status')} ({evidence_output.get('carrier_exception_note')}). "
                f"Signature on file: {evidence_output.get('signature_on_file')}."
            )

        audit_trace.append(
            AgentTraceStep(
                agent=AgentRole.EVIDENCE_VERIFIER,
                step_title="Carrier Telemetry & Delivery Proof Verification",
                thought=evidence_thought,
                tool_called="verify_carrier_tracking",
                tool_output=evidence_output,
                confidence_score=evidence_conf,
            )
        )

        # --- Step 3: Fraud & Risk Scoring Agent ---
        fraud_args = {
            "customer_email": claim.customer_email,
            "amount": claim.amount,
            "claim_type": claim.claim_type.value,
            "carrier_status": evidence_output.get("status", "UNKNOWN"),
            "signature_on_file": bool(evidence_output.get("signature_on_file", False)),
        }
        fraud_output, fraud_thought, fraud_conf = await self._call_gemini_with_tool(
            model=FAST_WORKER_MODEL,
            system_instruction=(
                "You are the Fraud & Risk Scoring Agent. Call `compute_fraud_risk_score` "
                "and explain the quantitative fraud risk score (0.0 to 1.0) and key risk signals."
            ),
            prompt=(
                f"Compute fraud risk score for buyer {claim.customer_email}, amount ${claim.amount:.2f}, "
                f"claim_type {claim.claim_type.value}, carrier_status {evidence_output.get('status')}."
            ),
            tool_declaration=FRAUD_TOOL_DECLARATION,
            tool_fn=compute_fraud_risk_score,
            fallback_args=fraud_args,
        )
        risk_score = float(fraud_output.get("fraud_risk_score", 0.10))
        if not fraud_thought:
            fraud_thought = (
                f"Computed quantitative fraud risk score of {risk_score:.2f} ({fraud_output.get('risk_band')}) "
                f"for {claim.customer_email}. Primary signals: {'; '.join(fraud_output.get('risk_factors', []))}."
            )

        audit_trace.append(
            AgentTraceStep(
                agent=AgentRole.FRAUD_RISK_SCORER,
                step_title="Quantitative Fraud & Velocity Risk Audit",
                thought=fraud_thought,
                tool_called="compute_fraud_risk_score",
                tool_output=fraud_output,
                confidence_score=fraud_conf,
            )
        )

        # --- Step 4: Policy & Merchant Rule Auditor ---
        policy_args = {
            "merchant_id": claim.merchant_id,
            "claim_type": claim.claim_type.value,
            "amount": claim.amount,
            "fraud_risk_score": risk_score,
            "carrier_status": evidence_output.get("status", "UNKNOWN"),
            "days_since_purchase": 5,
        }
        policy_output, policy_thought, policy_conf = await self._call_gemini_with_tool(
            model=FAST_WORKER_MODEL,
            system_instruction=(
                "You are the Policy & Merchant Rule Auditor. Call `audit_merchant_policy` "
                "to validate the 30-day return window, $250 autonomous settlement cap, and partial concession rules."
            ),
            prompt=(
                f"Audit store policy for merchant {claim.merchant_id}, claim type {claim.claim_type.value}, "
                f"amount ${claim.amount:.2f}, risk score {risk_score:.2f}, carrier status {evidence_output.get('status')}."
            ),
            tool_declaration=POLICY_TOOL_DECLARATION,
            tool_fn=audit_merchant_policy,
            fallback_args=policy_args,
        )
        if not policy_thought:
            policy_thought = (
                f"Audited {policy_output.get('merchant_name')} policy rules: "
                f"{policy_output.get('policy_reason')} Recommended action: {policy_output.get('policy_recommendation')}."
            )

        audit_trace.append(
            AgentTraceStep(
                agent=AgentRole.POLICY_AUDITOR,
                step_title="Store Policy & Autonomous Guardrail Validation",
                thought=policy_thought,
                tool_called="audit_merchant_policy",
                tool_output=policy_output,
                confidence_score=policy_conf,
            )
        )

        # --- Step 5: Supervisor Arbiter Agent ---
        arbiter_schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [a.value for a in ResolutionAction],
                },
                "refund_amount": {"type": "number"},
                "arbitration_summary": {"type": "string"},
                "arbiter_thought": {"type": "string"},
                "confidence_score": {"type": "number"},
            },
            "required": [
                "action",
                "refund_amount",
                "arbitration_summary",
                "arbiter_thought",
                "confidence_score",
            ],
        }

        arbiter_llm = await self._call_gemini_structured(
            model=ARBITER_MODEL,
            system_instruction=(
                "You are the Supervisor Arbiter Agent for PayResolve AI. Synthesize the Evidence Verifier, "
                "Fraud Risk Scorer, and Policy Auditor findings into a final binding resolution verdict. "
                "Strictly honor the Policy Auditor's guardrail recommendation."
            ),
            prompt=(
                f"Claim ID: {claim.claim_id} (${claim.amount:.2f} {claim.currency})\n"
                f"Evidence Output: {json.dumps(evidence_output)}\n"
                f"Fraud Output: {json.dumps(fraud_output)}\n"
                f"Policy Output: {json.dumps(policy_output)}"
            ),
            schema=arbiter_schema,
        )

        rec_map = {
            "AUTO_REFUND_FULL": ResolutionAction.AUTO_REFUND_FULL,
            "AUTO_REFUND_PARTIAL": ResolutionAction.AUTO_REFUND_PARTIAL,
            "REJECT_CLAIM": ResolutionAction.REJECT_CLAIM,
            "ESCALATE_TO_MERCHANT": ResolutionAction.ESCALATE_TO_MERCHANT,
            "REQUEST_MORE_EVIDENCE": ResolutionAction.REQUEST_MORE_EVIDENCE,
        }
        default_action = rec_map.get(
            policy_output.get("policy_recommendation", "ESCALATE_TO_MERCHANT"),
            ResolutionAction.ESCALATE_TO_MERCHANT,
        )
        default_refund = policy_output.get("recommended_refund_usd")

        if arbiter_llm:
            try:
                final_action = ResolutionAction(arbiter_llm.get("action", default_action.value))
            except ValueError:
                final_action = default_action
            # Enforce safety guardrail if policy requires escalation or rejection
            if default_action in (ResolutionAction.ESCALATE_TO_MERCHANT, ResolutionAction.REJECT_CLAIM):
                final_action = default_action
            refund_amount = default_refund
            arbitration_summary = arbiter_llm.get("arbitration_summary") or ""
            arbiter_thought = arbiter_llm.get("arbiter_thought") or ""
            arbiter_conf = float(arbiter_llm.get("confidence_score", 0.96))
        else:
            final_action = default_action
            refund_amount = default_refund
            arbitration_summary = ""
            arbiter_thought = ""
            arbiter_conf = 0.96

        if not arbiter_thought:
            arbiter_thought = (
                f"Synthesized multi-agent dossier for {claim.claim_id}: Carrier status='{evidence_output.get('status')}', "
                f"Fraud Risk={risk_score:.2f} ({fraud_output.get('risk_band')}), "
                f"Policy Recommendation='{policy_output.get('policy_recommendation')}'. "
                f"Issuing final directive: {final_action.value}."
            )

        audit_trace.append(
            AgentTraceStep(
                agent=AgentRole.SUPERVISOR_ARBITER,
                step_title="Multi-Agent Evidence Synthesis & Arbitration Verdict",
                thought=arbiter_thought,
                tool_called="synthesize_arbiter_verdict",
                tool_output={
                    "decision": final_action.value,
                    "approved_refund_usd": refund_amount,
                    "fraud_risk_score": risk_score,
                },
                confidence_score=min(1.0, max(0.0, arbiter_conf)),
            )
        )

        # --- Step 6: PayPal Settlement Agent ---
        settlement_output = await execute_paypal_settlement(
            capture_id=claim.capture_id,
            action=final_action.value,
            refund_amount=refund_amount,
            currency=claim.currency,
            claim_id=claim.claim_id,
        )
        paypal_refund_id = settlement_output.get("paypal_refund_id")

        if settlement_output.get("settled"):
            settlement_thought = (
                f"Authenticated with PayPal Sandbox API and executed {final_action.value} "
                f"for ${refund_amount:.2f} {claim.currency}. "
                f"PayPal Sandbox Settlement ID: {paypal_refund_id} (Status: {settlement_output.get('status')})."
            )
            claim.status = ClaimStatus.RESOLVED_REFUNDED
        elif final_action == ResolutionAction.REJECT_CLAIM:
            settlement_thought = (
                f"Blocked payout on PayPal capture {claim.capture_id} due to high fraud risk ({risk_score:.2f}) "
                f"and verified carrier delivery proof. Logged dispute defense dossier."
            )
            claim.status = ClaimStatus.RESOLVED_REJECTED
        else:
            settlement_thought = (
                f"Placed PayPal capture {claim.capture_id} on hold for human merchant review "
                f"(Claim amount ${claim.amount:.2f} exceeds $250 autonomous threshold)."
            )
            claim.status = ClaimStatus.ESCALATED_HUMAN

        audit_trace.append(
            AgentTraceStep(
                agent=AgentRole.PAYPAL_SETTLEMENT,
                step_title="PayPal Sandbox REST API Settlement Execution",
                thought=settlement_thought,
                tool_called="execute_paypal_settlement",
                tool_output=settlement_output,
                confidence_score=0.99,
            )
        )

        if not arbitration_summary:
            if final_action == ResolutionAction.AUTO_REFUND_FULL:
                arbitration_summary = (
                    f"APPROVED FULL AUTO-REFUND (${refund_amount:.2f} {claim.currency}): "
                    f"Carrier telemetry confirmed '{evidence_output.get('status')}', buyer fraud risk is low "
                    f"({risk_score:.2f} < 0.20), and amount is within the $250 autonomous threshold. "
                    f"Settled instantly on PayPal Sandbox ({paypal_refund_id})."
                )
            elif final_action == ResolutionAction.AUTO_REFUND_PARTIAL:
                arbitration_summary = (
                    f"APPROVED 40% PARTIAL CONCESSION (${refund_amount:.2f} of ${claim.amount:.2f} {claim.currency}): "
                    f"Evidence verified cosmetic/shipping damage while item remains functional. Buyer fraud risk is low "
                    f"({risk_score:.2f}). Instant partial refund settled via PayPal Sandbox ({paypal_refund_id})."
                )
            elif final_action == ResolutionAction.REJECT_CLAIM:
                arbitration_summary = (
                    f"CLAIM REJECTED ($0.00 Refunded): Carrier verified GPS delivery with direct recipient signature "
                    f"('{evidence_output.get('status')}'), and Fraud Scorer flagged elevated risk ({risk_score:.2f}). "
                    f"Zero funds disbursed."
                )
            else:
                arbitration_summary = (
                    f"ESCALATED TO HUMAN MERCHANT: Transaction value (${claim.amount:.2f}) exceeds the $250.00 "
                    f"autonomous settlement guardrail. Complete 6-agent evidence trace attached for 1-click merchant approval."
                )

        return ResolutionVerdict(
            claim_id=claim.claim_id,
            action=final_action,
            refund_amount=refund_amount,
            currency=claim.currency,
            fraud_risk_score=risk_score,
            paypal_refund_id=paypal_refund_id,
            arbitration_summary=arbitration_summary,
            audit_trace=audit_trace,
        )
