# PayResolve AI: Autonomous Multi-Agent Dispute & Resolution Swarm

> **Built for the PayPal AI Hackathon: Build What's Next with PayPal and AI**

PayResolve AI is an intelligent multi-agent platform that automates customer dispute triage, fraud detection, and instant resolution settlement using the PayPal Developer Platform (Sandbox) and state-of-the-art LLMs.

---

## 🌟 The Problem
E-commerce disputes and chargebacks cost merchants billions annually and trap customers in multi-week resolution loops. Merchants struggle to manually verify tracking numbers, cross-check return policies, detect fraudulent claims, and issue refunds quickly.

## 💡 The Solution: Multi-Agent Resolution Swarm
PayResolve AI deploys specialized collaborative AI agents to handle dispute workflows end-to-end:

1. **Customer Advocacy Agent:** Engages directly with the buyer to gather facts, receipts, photos, and intent with empathetic natural dialogue.
2. **Evidence Verification Agent:** Validates shipping tracking numbers, carrier status, delivery timestamps, and order metadata.
3. **Fraud & Risk Scoring Agent:** Evaluates buyer claim history, anomaly signals, and merchant policies to determine fraud likelihood.
4. **PayPal Settlement Agent:** Interfaces directly with the PayPal REST API to inspect capture data, execute partial/full refunds, or manage dispute records in the sandbox.
5. **Supervisor Arbiter Agent:** Synthesizes multi-agent evidence into a verifiable audit trail, executes safe auto-resolution under threshold rules, or escalates edge cases to a human merchant dashboard.

---

## 🛠️ Tech Stack
- **Backend:** Python / FastAPI, Asynchronous Multi-Agent Architecture
- **AI Core:** Google Gemini 2.5/Flash / LLM function calling & reasoning
- **Payments:** PayPal REST APIs (v2/checkout/orders, v2/payments/captures, v1/customer/disputes, sandbox mode)
- **Frontend:** React / Vite + Tailwind CSS (Interactive Swarm Visualizer & Merchant Console)

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-username/PayResolve-AI.git
cd PayPal_AI_Hackathon
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and supply your credentials:
```bash
cp .env.example .env
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
