import React from 'react';
import {
  MessageSquareHeart,
  Truck,
  ShieldAlert,
  Scale,
  Cpu,
  CreditCard,
  CheckCircle2,
  Loader2,
  CircleDot,
} from 'lucide-react';

export const AGENT_METADATA = {
  customer_intake: {
    id: 'customer_intake',
    order: 1,
    name: 'Customer Intake Agent',
    subtitle: 'Empathetic Triage & Schema Extraction',
    model: 'gemini-3.8-flash',
    icon: MessageSquareHeart,
    accent: 'from-sky-500 to-blue-600',
    border: 'border-sky-500/40',
    text: 'text-sky-400',
    bg: 'bg-sky-500/10',
  },
  evidence_verifier: {
    id: 'evidence_verifier',
    order: 2,
    name: 'Evidence & Tracking Agent',
    subtitle: 'Carrier GPS, Scan & Signature Audit',
    model: 'gemini-3.8-flash',
    icon: Truck,
    accent: 'from-cyan-500 to-teal-600',
    border: 'border-cyan-500/40',
    text: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
  fraud_risk_scorer: {
    id: 'fraud_risk_scorer',
    order: 3,
    name: 'Fraud & Risk Scorer',
    subtitle: 'Velocity & Anomaly Score (0.0–1.0)',
    model: 'gemini-3.8-flash',
    icon: ShieldAlert,
    accent: 'from-amber-500 to-orange-600',
    border: 'border-amber-500/40',
    text: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  policy_auditor: {
    id: 'policy_auditor',
    order: 4,
    name: 'Policy & Rule Auditor',
    subtitle: '30-Day Window & $250 Cap Guardrail',
    model: 'gemini-3.8-flash',
    icon: Scale,
    accent: 'from-purple-500 to-indigo-600',
    border: 'border-purple-500/40',
    text: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
  supervisor_arbiter: {
    id: 'supervisor_arbiter',
    order: 5,
    name: 'Supervisor Arbiter Hub',
    subtitle: 'Multi-Agent Synthesis & Verdict',
    model: 'gemini-4-argon',
    icon: Cpu,
    accent: 'from-blue-500 to-indigo-600',
    border: 'border-blue-500/50',
    text: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  paypal_settlement: {
    id: 'paypal_settlement',
    order: 6,
    name: 'PayPal Settlement Agent',
    subtitle: 'Live Sandbox Refund / Hold Execution',
    model: 'PayPal REST v2',
    icon: CreditCard,
    accent: 'from-emerald-500 to-teal-600',
    border: 'border-emerald-500/40',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
};

export const ORDERED_AGENT_KEYS = [
  'customer_intake',
  'evidence_verifier',
  'fraud_risk_scorer',
  'policy_auditor',
  'supervisor_arbiter',
  'paypal_settlement',
];

export default function SwarmTopologyDAG({
  auditTrace = [],
  activeStepIndex = -1,
  isRunning = false,
  selectedAgentId,
  onSelectAgent,
}) {
  const traceByAgent = {};
  auditTrace.forEach((step) => {
    traceByAgent[step.agent] = step;
  });

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-sky-400 flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            Hub-and-Spoke 6-Agent Execution Topology (DAG)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Click any node to inspect its isolated tool call, confidence score, and structured reasoning output.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Completed
          </span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span> Executing
          </span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2 h-2 rounded-full bg-slate-600"></span> Standby
          </span>
        </div>
      </div>

      {/* 6-Node Responsive Grid with Visual Flow Connectors */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {ORDERED_AGENT_KEYS.map((agentKey, idx) => {
          const meta = AGENT_METADATA[agentKey];
          const stepData = traceByAgent[agentKey];
          const IconComponent = meta.icon;

          const isCompleted = Boolean(stepData) && (!isRunning || idx <= activeStepIndex);
          const isCurrent = isRunning && idx === activeStepIndex;
          const isSelected = selectedAgentId === agentKey;

          return (
            <button
              key={agentKey}
              type="button"
              onClick={() => onSelectAgent && onSelectAgent(agentKey)}
              className={`group relative text-left rounded-xl p-3.5 transition-all duration-200 border ${
                isSelected
                  ? 'bg-slate-800/95 border-sky-400 ring-2 ring-sky-500/30 shadow-lg shadow-sky-950/50'
                  : isCurrent
                  ? 'bg-slate-800/90 border-sky-500/70 shadow-md shadow-sky-950/40'
                  : isCompleted
                  ? 'bg-slate-900/90 border-slate-700/80 hover:border-slate-600 hover:bg-slate-800/60'
                  : 'bg-slate-950/60 border-slate-800/70 opacity-65 hover:opacity-90'
              }`}
            >
              {/* Top Row: Step Number, Icon, Status */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-9 h-9 rounded-lg bg-gradient-to-br ${meta.accent} flex items-center justify-center text-white shadow-sm`}
                  >
                    <IconComponent className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        Node 0{meta.order}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {meta.model}
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-slate-100 mt-1 group-hover:text-sky-300 transition-colors">
                      {meta.name}
                    </h4>
                  </div>
                </div>

                <div className="shrink-0">
                  {isCurrent ? (
                    <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />
                  ) : isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <CircleDot className="w-4 h-4 text-slate-600" />
                  )}
                </div>
              </div>

              <p className="text-[11px] text-slate-400 mt-2 line-clamp-1">
                {stepData ? stepData.step_title : meta.subtitle}
              </p>

              {/* Bottom Pill Row: Tool Called + Confidence */}
              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between gap-2 text-[11px]">
                <span className="font-mono text-slate-300 truncate max-w-[165px]">
                  {stepData?.tool_called ? `⚡ ${stepData.tool_called}()` : '⏳ Awaiting input'}
                </span>
                {stepData && (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono text-[10px]">
                    {Math.round((stepData.confidence_score || 0.96) * 100)}% conf
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

