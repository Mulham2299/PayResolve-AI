from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ClaimType(str, Enum):
    ITEM_NOT_RECEIVED = "item_not_received"
    ITEM_DAMAGED = "item_damaged"
    UNAUTHORIZED_TRANSACTION = "unauthorized_transaction"
    SIGNIFICANTLY_NOT_AS_DESCRIBED = "significantly_not_as_described"


class ClaimStatus(str, Enum):
    RECEIVED = "received"
    EVALUATING = "evaluating"
    RESOLVED_REFUNDED = "resolved_refunded"
    RESOLVED_REJECTED = "resolved_rejected"
    ESCALATED_HUMAN = "escalated_human"


class AgentRole(str, Enum):
    CUSTOMER_INTAKE = "customer_intake"
    EVIDENCE_VERIFIER = "evidence_verifier"
    FRAUD_RISK_SCORER = "fraud_risk_scorer"
    POLICY_AUDITOR = "policy_auditor"
    PAYPAL_SETTLEMENT = "paypal_settlement"
    SUPERVISOR_ARBITER = "supervisor_arbiter"


class AgentTraceStep(BaseModel):
    agent: AgentRole
    step_title: str
    thought: str
    tool_called: Optional[str] = None
    tool_output: Optional[Dict[str, Any]] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DisputeClaim(BaseModel):
    claim_id: str
    customer_email: str
    merchant_id: str
    transaction_id: str
    capture_id: Optional[str] = None
    claim_type: ClaimType
    amount: float
    currency: str = "USD"
    customer_statement: str
    evidence_urls: List[str] = []
    tracking_number: Optional[str] = None
    status: ClaimStatus = ClaimStatus.RECEIVED
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResolutionAction(str, Enum):
    AUTO_REFUND_FULL = "auto_refund_full"
    AUTO_REFUND_PARTIAL = "auto_refund_partial"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"
    ESCALATE_TO_MERCHANT = "escalate_to_merchant"
    REJECT_CLAIM = "reject_claim"


class ResolutionVerdict(BaseModel):
    claim_id: str
    action: ResolutionAction
    refund_amount: Optional[float] = None
    currency: str = "USD"
    fraud_risk_score: float = Field(ge=0.0, le=1.0, description="0=Safe, 1=High Fraud Risk")
    paypal_refund_id: Optional[str] = None
    arbitration_summary: str
    audit_trace: List[AgentTraceStep] = []
    resolved_at: datetime = Field(default_factory=datetime.utcnow)


# --- PayPal Specific Models ---

class PayPalCaptureDetails(BaseModel):
    id: str
    status: str
    amount_value: str
    currency_code: str
    create_time: str
    seller_receivable_breakdown: Optional[Dict[str, Any]] = None


class PayPalRefundResult(BaseModel):
    id: str
    status: str
    amount_value: str
    currency_code: str
    create_time: str
    is_sandbox_live: bool = True
    note: Optional[str] = None


# --- API Request / Response Models ---

class CustomerIntakeRequest(BaseModel):
    customer_email: str = "buyer.demo@example.com"
    merchant_id: str = "MERCH-TECHGEAR-01"
    transaction_id: str = "TXN-9948271"
    capture_id: Optional[str] = None
    amount: float = 89.99
    currency: str = "USD"
    customer_message: str
    tracking_number: Optional[str] = None
    evidence_urls: List[str] = []


class CustomerIntakeResponse(BaseModel):
    empathetic_reply: str
    claim: DisputeClaim
    intake_trace: AgentTraceStep


class RefundTriggerRequest(BaseModel):
    amount_value: Optional[str] = None
    currency_code: str = "USD"
    note_to_payer: str = "PayResolve AI: Automated Dispute Resolution"


class CreateOrderRequest(BaseModel):
    amount_value: str = "89.99"
    currency_code: str = "USD"
    description: str = "PayResolve AI Sandbox Test Purchase"


class SimulationResultResponse(BaseModel):
    scenario_id: str
    scenario_title: str
    empathetic_intake_reply: str
    claim: DisputeClaim
    verdict: ResolutionVerdict


class PayPalWebhookPayload(BaseModel):
    id: str = "WH-2026-SANDBOX-99102"
    event_type: str = "CUSTOMER.DISPUTE.CREATED"
    resource_type: str = "dispute"
    summary: str = "A new customer dispute was created in PayPal Sandbox"
    resource: Dict[str, Any] = Field(default_factory=dict)
    create_time: Optional[str] = None


