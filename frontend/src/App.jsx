import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Sparkles,
  Play,
  Send,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  UserCheck,
  DollarSign,
  Clock,
  Activity,
  Terminal,
  RefreshCw,
  ExternalLink,
  Layers,
  Award,
  FileText,
  ChevronRight,
  Lock,
} from 'lucide-react';
import SwarmTopologyDAG, {
  AGENT_METADATA,
  ORDERED_AGENT_KEYS,
} from './components/SwarmTopologyDAG';

const ACTION_STYLES = {
  auto_refund_full: {
    label: 'INSTANT FULL REFUND SETTLED',
    badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    bannerClass: 'from-emerald-950/90 via-slate-900 to-slate-900 border-emerald-500/50',
    icon: CheckCircle2,
    iconColor: 'text-emerald-400',
  },
  auto_refund_partial: {
    label: '40% PARTIAL CONCESSION SETTLED',
    badgeClass: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
    bannerClass: 'from-sky-950/90 via-slate-900 to-slate-900 border-sky-500/50',
    icon: CheckCircle2,
    iconColor: 'text-sky-400',
  },
  reject_claim: {
    label: 'FRAUD / DELIVERY VERIFIED — CLAIM REJECTED',
    badgeClass: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    bannerClass: 'from-rose-950/90 via-slate-900 to-slate-900 border-rose-500/50',
    icon: XCircle,
    iconColor: 'text-rose-400',
  },
  escalate_to_merchant: {
    label: 'ESCALATED TO HUMAN MERCHANT (> $250 CAP)',
    badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    bannerClass: 'from-amber-950/90 via-slate-900 to-slate-900 border-amber-500/50',
    icon: AlertTriangle,
    iconColor: 'text-amber-400',
  },
  request_more_evidence: {
    label: 'ADDITIONAL BUYER EVIDENCE REQUESTED',
    badgeClass: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    bannerClass: 'from-purple-950/90 via-slate-900 to-slate-900 border-purple-500/50',
    icon: FileText,
    iconColor: 'text-purple-400',
  },
};

export default function App() {
  const [paypalStatus, setPaypalStatus] = useState({
    connected: false,
    loading: true,
    api_base: 'https://api-m.sandbox.paypal.com',
    token_prefix: null,
  });
  const [scenarios, setScenarios] = useState([]);
  const [activeScenarioId, setActiveScenarioId] = useState('clean_inr_refund');

  // Active simulation / claim state
  const [currentClaim, setCurrentClaim] = useState(null);
  const [empatheticReply, setEmpatheticReply] = useState('');
  const [currentVerdict, setCurrentVerdict] = useState(null);
  const [isRunningSwarm, setIsRunningSwarm] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const [selectedAgentId, setSelectedAgentId] = useState('supervisor_arbiter');

  // Merchant Dashboard History & Metrics
  const [disputeHistory, setDisputeHistory] = useState([]);
  const [metrics, setMetrics] = useState({
    total_claims: 0,
    auto_resolved_count: 0,
    total_disputed_usd: 0,
    total_refunded_usd: 0,
    fraud_blocked_usd: 0,
    chargeback_fees_saved_usd: 0,
  });

  // Custom Buyer Dispute Form State
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customForm, setCustomForm] = useState({
    customer_email: 'sarah.connor@example.com',
    transaction_id: 'TXN-PP-551902',
    amount: '95.00',
    tracking_number: '1Z999AA10123456784',
    customer_message:
      'My package has been stuck in transit at the UPS hub for 9 days and never arrived. Can I please get a refund?',
  });

  // Live PayPal Order generator state
  const [liveOrderResult, setLiveOrderResult] = useState(null);
  const [creatingOrder, setCreatingOrder] = useState(false);
  const [manualOverrideLoading, setManualOverrideLoading] = useState(false);

  // Initial load: Check PayPal Sandbox Status, Load Scenarios, and Run Default Scenario 1
  useEffect(() => {
    fetchPayPalStatus();
    fetchScenariosAndInitialize();
  }, []);

  async function fetchPayPalStatus() {
    try {
      setPaypalStatus((prev) => ({ ...prev, loading: true }));
      const res = await fetch('/api/paypal/status');
      if (res.ok) {
        const data = await res.json();
        setPaypalStatus({ ...data, loading: false });
      } else {
        setPaypalStatus((prev) => ({ ...prev, connected: false, loading: false }));
      }
    } catch {
      setPaypalStatus((prev) => ({ ...prev, connected: false, loading: false }));
    }
  }

  async function fetchDisputesSummary() {
    try {
      const res = await fetch('/api/disputes');
      if (res.ok) {
        const data = await res.json();
        setDisputeHistory(data.items || []);
        if (data.metrics) setMetrics(data.metrics);
      }
    } catch {
      // ignore
    }
  }

  async function fetchScenariosAndInitialize() {
    try {
      const res = await fetch('/api/disputes/scenarios');
      if (res.ok) {
        const list = await res.json();
        setScenarios(list);
        if (list.length > 0) {
          await runScenarioSimulation(list[0].scenario_id);
        }
      }
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    }
  }

  function animateSwarmSteps(verdictData) {
    const stepsCount = verdictData?.audit_trace?.length || 6;
    setActiveStepIndex(0);
    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      if (step < stepsCount) {
        setActiveStepIndex(step);
        const agentKey = ORDERED_AGENT_KEYS[step];
        if (agentKey) setSelectedAgentId(agentKey);
      } else {
        clearInterval(interval);
        setIsRunningSwarm(false);
        setActiveStepIndex(stepsCount);
        setSelectedAgentId('supervisor_arbiter');
      }
    }, 260);
  }

  async function runScenarioSimulation(scenarioId) {
    setActiveScenarioId(scenarioId);
    setShowCustomForm(false);
    setIsRunningSwarm(true);
    setActiveStepIndex(0);
    setSelectedAgentId('customer_intake');

    try {
      const res = await fetch(`/api/disputes/simulate/${scenarioId}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Simulation request failed');
      const data = await res.json();
      setCurrentClaim(data.claim);
      setEmpatheticReply(data.empathetic_intake_reply);
      setCurrentVerdict(data.verdict);
      animateSwarmSteps(data.verdict);
      await fetchDisputesSummary();
    } catch (err) {
      console.error(err);
      setIsRunningSwarm(false);
    }
  }

  async function runAllFourScenarios() {
    for (const sc of scenarios) {
      await fetch(`/api/disputes/simulate/${sc.scenario_id}`, { method: 'POST' });
    }
    await fetchDisputesSummary();
  }

  async function handleCustomDisputeSubmit(e) {
    e.preventDefault();
    setIsRunningSwarm(true);
    setActiveStepIndex(0);
    setSelectedAgentId('customer_intake');

    try {
      // Step 1: Customer Intake Agent
      const intakeRes = await fetch('/api/disputes/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_email: customForm.customer_email,
          merchant_id: 'MERCH-TECHGEAR-01',
          transaction_id: customForm.transaction_id,
          amount: parseFloat(customForm.amount) || 89.99,
          currency: 'USD',
          customer_message: customForm.customer_message,
          tracking_number: customForm.tracking_number || null,
          evidence_urls: ['https://assets.payresolve.ai/evidence/custom-upload.png'],
        }),
      });
      const intakeData = await intakeRes.json();
      setCurrentClaim(intakeData.claim);
      setEmpatheticReply(intakeData.empathetic_reply);

      // Step 2: Full 6-Agent Swarm Resolution
      const resolveRes = await fetch('/api/disputes/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(intakeData.claim),
      });
      const verdictData = await resolveRes.json();
      setCurrentVerdict(verdictData);
      setShowCustomForm(false);
      animateSwarmSteps(verdictData);
      await fetchDisputesSummary();
    } catch (err) {
      console.error('Custom dispute error:', err);
      setIsRunningSwarm(false);
    }
  }

  async function handleCreateSandboxOrder() {
    setCreatingOrder(true);
    try {
      const res = await fetch('/api/paypal/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_value: currentClaim ? String(currentClaim.amount) : '89.99',
          currency_code: 'USD',
          description: 'PayResolve AI Live Sandbox Test Order',
        }),
      });
      const data = await res.json();
      setLiveOrderResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingOrder(false);
    }
  }

  async function handleMerchantManualApproveRefund() {
    if (!currentClaim) return;
    setManualOverrideLoading(true);
    try {
      const capId = currentClaim.capture_id || `CAP-${currentClaim.transaction_id}`;
      const res = await fetch(`/api/paypal/captures/${capId}/refund`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_value: String(currentClaim.amount),
          currency_code: currentClaim.currency || 'USD',
          note_to_payer: `Merchant Approved Escalated Claim ${currentClaim.claim_id}`,
        }),
      });
      if (res.ok) {
        const refundData = await res.json();
        setCurrentVerdict((prev) => ({
          ...prev,
          action: 'auto_refund_full',
          refund_amount: currentClaim.amount,
          paypal_refund_id: refundData.id,
          arbitration_summary: `MERCHANT OVERRIDE APPROVED ($${currentClaim.amount.toFixed(
            2
          )}): Human merchant approved full settlement on PayPal Sandbox (${refundData.id}).`,
        }));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setManualOverrideLoading(false);
    }
  }

  const selectedTraceStep =
    currentVerdict?.audit_trace?.find((s) => s.agent === selectedAgentId) ||
    currentVerdict?.audit_trace?.[currentVerdict.audit_trace.length - 1];

  const selectedMeta = AGENT_METADATA[selectedAgentId] || AGENT_METADATA.supervisor_arbiter;
  const actionStyle =
    ACTION_STYLES[currentVerdict?.action] || ACTION_STYLES.escalate_to_merchant;
  const VerdictIcon = actionStyle.icon;

  const riskScore = currentVerdict?.fraud_risk_score ?? 0;
  const riskPercent = Math.round(riskScore * 100);
  const riskColor =
    riskScore < 0.2
      ? 'text-emerald-400 bg-emerald-500'
      : riskScore < 0.6
      ? 'text-amber-400 bg-amber-500'
      : 'text-rose-400 bg-rose-500';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* =====================================================================
          TOP NAVIGATION & PAYPAL SANDBOX LIVE STATUS BAR
         ===================================================================== */}
      <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/90 border-b border-slate-800/80 px-6 py-3.5">
        <div className="max-w-[1440px] mx-auto flex flex-wrap items-center justify-between gap-4">
          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-sky-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-white via-sky-200 to-cyan-300 bg-clip-text text-transparent">
                  PayResolve AI
                </h1>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-sky-300 border border-sky-500/30">
                  Agentic Commerce Swarm
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Autonomous Multi-Agent Dispute Triage, Fraud Scoring & Instant PayPal Sandbox Settlement
              </p>
            </div>
          </div>

          {/* Right Status Controls */}
          <div className="flex flex-wrap items-center gap-3">
            {/* PayPal Sandbox Live Connection Pill */}
            <div className="flex items-center gap-2.5 bg-slate-900/90 border border-slate-800 px-3.5 py-1.5 rounded-xl text-xs">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  paypalStatus.connected
                    ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
                    : 'bg-amber-400 animate-pulse'
                }`}
              />
              <div>
                <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                  PayPal Sandbox REST API
                  {paypalStatus.token_prefix && (
                    <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded">
                      OAuth: {paypalStatus.token_prefix}
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-400 font-mono">
                  {paypalStatus.api_base}
                </div>
              </div>
              <button
                onClick={fetchPayPalStatus}
                title="Re-verify PayPal Sandbox OAuth2 Token"
                className="ml-1 p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-sky-300 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${paypalStatus.loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Create Live Sandbox Order Button */}
            <button
              onClick={handleCreateSandboxOrder}
              disabled={creatingOrder}
              className="flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-500 hover:to-sky-400 text-white shadow-md shadow-blue-950/50 transition-all disabled:opacity-50"
            >
              <DollarSign className="w-3.5 h-3.5" />
              {creatingOrder ? 'Creating Sandbox Order...' : 'Create Live PayPal Order'}
            </button>
          </div>
        </div>

        {/* Optional Live Order Created Toast Banner */}
        {liveOrderResult && (
          <div className="max-w-[1440px] mx-auto mt-3 p-3 rounded-xl bg-blue-950/60 border border-sky-500/40 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>
                Created Live PayPal Sandbox Order{' '}
                <strong className="font-mono text-sky-300">{liveOrderResult.id}</strong> (Status:{' '}
                <span className="font-mono text-emerald-300">{liveOrderResult.status}</span>) via{' '}
                <code className="text-slate-300">POST /v2/checkout/orders</code>
              </span>
            </div>
            <div className="flex items-center gap-3">
              {liveOrderResult.links?.find((l) => l.rel === 'approve') && (
                <a
                  href={liveOrderResult.links.find((l) => l.rel === 'approve').href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-sky-300 hover:text-sky-200 underline font-medium"
                >
                  Open PayPal Sandbox Checkout <ExternalLink className="w-3 h-3" />
                </a>
              )}
              <button
                onClick={() => setLiveOrderResult(null)}
                className="text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}
      </header>

      {/* =====================================================================
          MAIN DASHBOARD CONTENT
         ===================================================================== */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-6 py-5 space-y-5">
        {/* 1. MERCHANT FINANCIAL IMPACT KPI RIBBON */}
        <section className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Claims Triaged</span>
              <Layers className="w-4 h-4 text-sky-400" />
            </div>
            <div className="text-2xl font-extrabold text-white mt-1">
              {metrics.total_claims}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              ${metrics.total_disputed_usd.toFixed(2)} total volume
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Resolution Speed</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-extrabold text-cyan-300 mt-1">1.8 sec</div>
            <div className="text-[11px] text-emerald-400 mt-0.5">
              vs. 14-day manual queue
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Settled via PayPal</span>
              <DollarSign className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-extrabold text-emerald-400 mt-1">
              ${metrics.total_refunded_usd.toFixed(2)}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Auto-refunded in Sandbox
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Fraud Claims Blocked</span>
              <Lock className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-extrabold text-rose-400 mt-1">
              ${metrics.fraud_blocked_usd.toFixed(2)}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Protected via GPS + Signature
            </div>
          </div>

          <div className="col-span-2 md:col-span-1 bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Chargeback Fees Saved</span>
              <Award className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-extrabold text-amber-300 mt-1">
              ${metrics.chargeback_fees_saved_usd.toFixed(2)}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              $20.00 saved per pre-claim
            </div>
          </div>
        </section>

        {/* 2. SCENARIO LAUNCHER BAR */}
        <section className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Interactive Dispute Simulation Scenarios (One-Click Live Swarm Execution)
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowCustomForm(!showCustomForm)}
                className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                  showCustomForm
                    ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                    : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white'
                }`}
              >
                + Custom Buyer Claim
              </button>
              <button
                onClick={runAllFourScenarios}
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 border border-slate-700 font-medium transition-colors"
              >
                Run All 4 Scenarios
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {scenarios.map((sc) => {
              const isSelected = activeScenarioId === sc.scenario_id && !showCustomForm;
              return (
                <button
                  key={sc.scenario_id}
                  onClick={() => runScenarioSimulation(sc.scenario_id)}
                  disabled={isRunningSwarm}
                  className={`text-left p-3.5 rounded-xl border transition-all flex flex-col justify-between ${
                    isSelected
                      ? 'bg-gradient-to-br from-blue-950/90 to-slate-900 border-sky-400 ring-1 ring-sky-400/40 shadow-lg'
                      : 'bg-slate-950/70 border-slate-800/90 hover:border-slate-700 hover:bg-slate-900'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-sky-300 border border-slate-700">
                        {sc.claim_preview.claim_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-bold text-white font-mono">
                        ${sc.claim_preview.amount.toFixed(2)}
                      </span>
                    </div>
                    <h3 className="text-xs font-bold text-slate-100 mt-2">
                      {sc.title}
                    </h3>
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                      {sc.description}
                    </p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-sky-400 font-medium">
                    <span>Trigger 6-Agent Swarm</span>
                    <Play className="w-3.5 h-3.5 fill-current" />
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* 3. SPLIT SCREEN: BUYER DISPUTE PORTAL (LEFT) & LIVE SWARM VISUALIZER (RIGHT) */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* LEFT COLUMN (5 COLS): BUYER CONVERSATIONAL PORTAL */}
          <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-sky-400">
                  Buyer Experience Portal
                </span>
                <h2 className="text-base font-bold text-white">
                  Conversational Dispute Intake & Instant Receipt
                </h2>
              </div>
              {currentClaim && (
                <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
                  {currentClaim.claim_id}
                </span>
              )}
            </div>

            {showCustomForm ? (
              <form onSubmit={handleCustomDisputeSubmit} className="space-y-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Buyer Email</label>
                  <input
                    type="email"
                    required
                    value={customForm.customer_email}
                    onChange={(e) =>
                      setCustomForm({ ...customForm, customer_email: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white focus:border-sky-500 focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">
                      Transaction ID
                    </label>
                    <input
                      type="text"
                      required
                      value={customForm.transaction_id}
                      onChange={(e) =>
                        setCustomForm({ ...customForm, transaction_id: e.target.value })
                      }
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white font-mono focus:border-sky-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">
                      Disputed Amount ($ USD)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={customForm.amount}
                      onChange={(e) =>
                        setCustomForm({ ...customForm, amount: e.target.value })
                      }
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white font-mono focus:border-sky-500 focus:outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Carrier Tracking Number
                  </label>
                  <input
                    type="text"
                    value={customForm.tracking_number}
                    onChange={(e) =>
                      setCustomForm({ ...customForm, tracking_number: e.target.value })
                    }
                    placeholder="e.g. 1Z999AA10123456784 or USPS-9400111899223"
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white font-mono focus:border-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Buyer Statement
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={customForm.customer_message}
                    onChange={(e) =>
                      setCustomForm({ ...customForm, customer_message: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white focus:border-sky-500 focus:outline-none"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCustomForm(false)}
                    className="px-3 py-2 rounded-lg bg-slate-800 text-xs text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isRunningSwarm}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-xs font-bold text-slate-950"
                  >
                    <Send className="w-3.5 h-3.5" /> Submit to Swarm
                  </button>
                </div>
              </form>
            ) : currentClaim ? (
              <div className="space-y-4">
                {/* Order & Tracking Metadata Bar */}
                <div className="grid grid-cols-2 gap-2.5 bg-slate-950/80 p-3 rounded-xl border border-slate-800/80 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Customer</span>
                    <span className="font-medium text-slate-200 truncate block">
                      {currentClaim.customer_email}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">
                      Transaction / Capture
                    </span>
                    <span className="font-mono text-sky-300">
                      {currentClaim.transaction_id}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">
                      Carrier Tracking
                    </span>
                    <span className="font-mono text-amber-300">
                      {currentClaim.tracking_number || 'None Provided'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">
                      Disputed Amount
                    </span>
                    <span className="font-mono font-bold text-white">
                      ${currentClaim.amount.toFixed(2)} {currentClaim.currency}
                    </span>
                  </div>
                </div>

                {/* Chat Thread */}
                <div className="space-y-3">
                  {/* Buyer Message Bubble */}
                  <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl rounded-tl-sm p-3.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                      <span className="font-semibold text-slate-200">
                        Buyer ({currentClaim.customer_email})
                      </span>
                      <span className="font-mono uppercase text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-sky-300">
                        {currentClaim.claim_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      “{currentClaim.customer_statement}”
                    </p>
                  </div>

                  {/* Customer Intake Agent Empathetic Reply Bubble */}
                  <div className="bg-gradient-to-br from-blue-950/70 to-slate-900 border border-sky-500/30 rounded-2xl rounded-tr-sm p-3.5">
                    <div className="flex items-center justify-between text-[11px] text-sky-300 mb-1">
                      <span className="font-semibold flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" /> PayResolve Intake Agent
                      </span>
                      <span className="font-mono text-[10px] text-slate-400">
                        Instant Triage
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      {empatheticReply}
                    </p>
                  </div>
                </div>

                {/* Live Settlement Receipt Card (shown once Verdict arrives) */}
                {currentVerdict && (
                  <div
                    className={`rounded-xl p-4 border bg-gradient-to-br ${actionStyle.bannerClass}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <VerdictIcon className={`w-5 h-5 ${actionStyle.iconColor}`} />
                        <div>
                          <span
                            className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${actionStyle.badgeClass}`}
                          >
                            {actionStyle.label}
                          </span>
                          <h4 className="text-xs font-bold text-white mt-1.5">
                            {currentVerdict.action === 'auto_refund_full' ||
                            currentVerdict.action === 'auto_refund_partial'
                              ? `Refund Issued: $${(
                                  currentVerdict.refund_amount || 0
                                ).toFixed(2)} ${currentVerdict.currency}`
                              : currentVerdict.action === 'reject_claim'
                              ? 'Payout Blocked ($0.00 Disbursed)'
                              : 'Held for Human Merchant Approval'}
                          </h4>
                        </div>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 mt-2.5 leading-relaxed">
                      {currentVerdict.arbitration_summary}
                    </p>

                    {currentVerdict.paypal_refund_id && (
                      <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">
                          PayPal Sandbox Settlement ID:
                        </span>
                        <span className="font-mono font-bold text-emerald-300 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/30">
                          {currentVerdict.paypal_refund_id}
                        </span>
                      </div>
                    )}

                    {currentVerdict.action === 'escalate_to_merchant' && (
                      <div className="mt-3 pt-3 border-t border-amber-500/30 flex items-center justify-between gap-2">
                        <span className="text-[11px] text-amber-200">
                          Human-in-the-Loop Merchant Override:
                        </span>
                        <button
                          onClick={handleMerchantManualApproveRefund}
                          disabled={manualOverrideLoading}
                          className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-all"
                        >
                          {manualOverrideLoading
                            ? 'Executing PayPal Refund...'
                            : `Approve $${currentClaim.amount.toFixed(2)} PayPal Refund`}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : null}
          </div>

          {/* RIGHT COLUMN (7 COLS): LIVE 6-AGENT SWARM DAG & AUDIT INSPECTOR */}
          <div className="lg:col-span-7 space-y-4">
            {/* 6-Agent Interactive Topology DAG */}
            <SwarmTopologyDAG
              auditTrace={currentVerdict?.audit_trace || []}
              activeStepIndex={activeStepIndex}
              isRunning={isRunningSwarm}
              selectedAgentId={selectedAgentId}
              onSelectAgent={(id) => setSelectedAgentId(id)}
            />

            {/* Fraud Risk Score Gauge & Selected Agent Deep-Dive Inspector */}
            {currentVerdict && (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                {/* Quantitative Fraud Risk Gauge Card (4 cols) */}
                <div className="md:col-span-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                      Fraud & Velocity Score
                    </span>
                    <div className="flex items-baseline justify-between mt-2">
                      <span
                        className={`text-3xl font-extrabold font-mono ${
                          riskColor.split(' ')[0]
                        }`}
                      >
                        {riskScore.toFixed(2)}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        Threshold &lt; 0.20
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden mt-3">
                      <div
                        className={`h-full transition-all duration-500 ${
                          riskColor.split(' ')[1]
                        }`}
                        style={{ width: `${Math.max(4, riskPercent)}%` }}
                      />
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Auto-Settlement Limit:</span>
                      <span className="font-mono text-slate-200">$250.00 USD</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Return Policy Window:</span>
                      <span className="font-mono text-slate-200">30 Days</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Guardrail Status:</span>
                      <span className="font-mono text-sky-300">
                        {riskScore < 0.2 ? 'PASS (SAFE)' : 'FLAGGED'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Selected Agent Reasoning & Tool Output JSON Inspector (8 cols) */}
                <div className="md:col-span-8 bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
                  {selectedTraceStep ? (
                    <div>
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                        <div className="flex items-center gap-2">
                          <Terminal className="w-4 h-4 text-sky-400" />
                          <h4 className="text-xs font-bold text-white">
                            {selectedMeta.name} — {selectedTraceStep.step_title}
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                          Tool: {selectedTraceStep.tool_called}()
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 mt-3 leading-relaxed">
                        {selectedTraceStep.thought}
                      </p>

                      {selectedTraceStep.tool_output && (
                        <div className="mt-3">
                          <div className="text-[10px] font-mono uppercase text-slate-400 mb-1">
                            Structured Tool Output Payload (JSON):
                          </div>
                          <pre className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-[11px] font-mono text-cyan-300 overflow-x-auto max-h-44">
                            {JSON.stringify(selectedTraceStep.tool_output, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* 4. MERCHANT AUDIT LOG TABLE (RECENT SWARM EXECUTIONS) */}
        {disputeHistory.length > 0 && (
          <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Merchant Audit Ledger & Real-Time PayPal Sandbox Settlements
                </h3>
              </div>
              <span className="text-xs text-slate-400">
                Click any row to inspect its 6-agent trace
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] text-slate-400 uppercase font-mono">
                    <th className="py-2.5 px-3">Claim ID</th>
                    <th className="py-2.5 px-3">Buyer</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Disputed</th>
                    <th className="py-2.5 px-3">Fraud Risk</th>
                    <th className="py-2.5 px-3">Swarm Verdict</th>
                    <th className="py-2.5 px-3">PayPal Sandbox ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {disputeHistory.map(({ claim, verdict }) => {
                    const style =
                      ACTION_STYLES[verdict?.action] || ACTION_STYLES.escalate_to_merchant;
                    return (
                      <tr
                        key={claim.claim_id}
                        onClick={() => {
                          setCurrentClaim(claim);
                          setCurrentVerdict(verdict);
                          setSelectedAgentId('supervisor_arbiter');
                        }}
                        className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                      >
                        <td className="py-2.5 px-3 font-mono font-bold text-sky-300">
                          {claim.claim_id}
                        </td>
                        <td className="py-2.5 px-3 text-slate-200">
                          {claim.customer_email}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {claim.claim_type}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-white font-semibold">
                          ${claim.amount.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          <span
                            className={`px-2 py-0.5 rounded ${
                              (verdict?.fraud_risk_score || 0) < 0.2
                                ? 'bg-emerald-500/10 text-emerald-300'
                                : (verdict?.fraud_risk_score || 0) < 0.6
                                ? 'bg-amber-500/10 text-amber-300'
                                : 'bg-rose-500/10 text-rose-300'
                            }`}
                          >
                            {(verdict?.fraud_risk_score ?? 0).toFixed(2)}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${style.badgeClass}`}
                          >
                            {verdict?.action}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-emerald-300">
                          {verdict?.paypal_refund_id || '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

