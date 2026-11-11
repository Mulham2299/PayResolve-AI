# PayResolve AI Devpost submission copy

## Project name
PayResolve AI

## Elevator pitch (max 200 characters)
A dispute resolution app that checks shipping scans, buyer history, and store return rules before issuing or blocking refunds through the PayPal Sandbox API.

## Built with
`paypal`, `python`, `fastapi`, `react`, `tailwindcss`, `gemini`, `pydantic`, `httpx`, `render`, `postman`

## About the project

## Inspiration

When a customer opens a "package never arrived" or "item arrived damaged" dispute on an online order, someone on the merchant side has to look up the PayPal capture ID, check the carrier tracking page, read the store's return rules, and decide whether to refund the money. Waiting too long turns the complaint into a formal chargeback with a $15 to $20 dispute fee, while refunding every complaint automatically loses money on false claims.

I built PayResolve AI to automate those checks before any money moves in PayPal. It pulls the tracking status, checks the buyer's past claims, compares the request against the store's return rules, and then calls the PayPal Captures API to issue a full or partial refund when the claim is valid, or holds the funds when the evidence shows the item was delivered.

## What it does

PayResolve AI passes each dispute through six small agents that each handle one step of the investigation:

1. The Intake Agent reads the customer's message and pulls out the PayPal capture ID, order ID, tracking number, claim type, and requested refund amount.
2. The Evidence Verifier checks the carrier tracking record for that tracking number to see if the package is lost in transit, still moving, or marked delivered with a GPS scan and signature. For damaged item claims, it also checks the damage notes.
3. The Fraud Risk Scorer calculates a risk score between 0.00 and 1.00 from the buyer's account age, past refund rate, and whether their claim contradicts the carrier scan.
4. The Policy Auditor checks the merchant's return window, the partial refund cap for cosmetic damage (30%), and the dollar limit where a human manager has to approve the payout ($500).
5. The Supervisor Arbiter reads the three reports and picks one of four outcomes: `AUTO_REFUND_FULL`, `AUTO_REFUND_PARTIAL`, `REJECT_CLAIM_EVIDENCE`, or `ESCALATE_TO_HUMAN`.
6. The PayPal Settlement Agent calls `POST /v2/payments/captures/{capture_id}/refund` in the PayPal Sandbox when a full or partial refund is approved, or keeps the capture intact if the claim is rejected or escalated.

The web interface has two tabs so you can see both sides of an order. In the Customer View, you can create a real PayPal Sandbox order, capture the payment, and file a dispute on that transaction, or load one of four test cases. In the Merchant View, you can watch the six steps run in order, read the output from each agent, and inspect the PayPal refund receipt and webhook log.

## How I built it

The backend is written in Python with FastAPI and Pydantic v2. I wrote an async PayPal client (`backend/paypal/client.py`) using `httpx` that gets an OAuth 2.0 bearer token (`POST /v1/oauth2/token`) and calls the Orders v2 (`POST /v2/checkout/orders`), Captures (`GET /v2/payments/captures/{id}` and `POST /v2/payments/captures/{id}/refund`), Customer Disputes (`GET /v1/customer/disputes`), and Webhook endpoints.

The agent pipeline (`backend/agents/swarm.py` and `backend/agents/tools.py`) uses the `google-genai` SDK to run the intake, evidence, fraud, policy, and arbitration steps, with a deterministic tool fallback so the app still runs fast if an API key hits a quota limit.

The frontend (`frontend/src/App.jsx`) is a React 18 and Tailwind CSS dashboard built with Vite. It includes a live node graph (`SwarmTopologyDAG.jsx`) that updates as each step finishes. I also wrote a `pytest` suite (`tests/test_swarm_and_api.py`), a Postman collection (`docs/PayResolve_AI.postman_collection.json`), and a `render.yaml` file for deployment.

## Challenges I ran into

Early on, if a buyer wrote a polite message saying their package never showed up, the model tended to approve the refund even when the tracking record showed a signed delivery at their front door. Splitting the Evidence Verifier and Fraud Risk Scorer into separate steps before the Arbiter fixed this, because the Arbiter gets a structured report showing the GPS delivery scan and a 0.92 risk score alongside the customer's message.

Another issue came up with PayPal Sandbox order states. In PayPal's Sandbox, you cannot refund an order until a buyer has approved and captured it, and calling the refund endpoint on an uncaptured order returns `UNPROCESSABLE_ENTITY`. To make testing practical from a single dashboard, I added an endpoint (`/api/paypal/orders/{order_id}/capture-and-dispute`) that creates the order, attempts the capture, and generates a working sandbox receipt when testing without a separate checkout popup.

## Accomplishments that I'm proud of

I got the full loop working from one screen: you can create a live PayPal Sandbox order, run a dispute on it, watch the six steps verify the claim, and get the PayPal response back in a couple of seconds.

I also built four test cases into the UI that cover both happy and unhappy paths:
- A $129.99 headphones order lost in transit by USPS, which gets approved for a full PayPal refund.
- A $249.50 espresso machine with a scratched casing where the buyer wants to keep it, which gets a 30% partial refund ($74.85) based on store rules.
- An $899.00 laptop where the buyer claims it never arrived, but FedEx has a GPS scan and signature (`J. SMITH`), so the claim is rejected with $0 refunded.
- A $2,450.00 server rack that arrived with bent rails, which exceeds the store's $500 automatic refund limit and gets paused for a human manager.

## What I learned

Breaking a payout decision into small, separate checks (shipping status, buyer history, store return limits) makes it much easier to see why a claim was approved or blocked than putting everything in one prompt. Working with PayPal's Captures and Disputes APIs also showed me how much of post-purchase support can be automated once you tie `CUSTOMER.DISPUTE.CREATED` webhooks directly to shipping and policy checks.

## What's next for PayResolve AI

Next, I want to connect the Evidence Verifier to live FedEx, UPS, and USPS tracking APIs instead of simulated carrier records. I also want to use vision models to compare customer damage photos against warehouse packing photos, and use PayPal's Dispute Evidence API (`POST /v1/customer/disputes/{id}/provide-evidence`) to upload PDF evidence packages automatically when a rejected buyer files a chargeback with their bank.

## Additional info responses

### Explain how your project meets the main technology requirement
PayResolve AI uses PayPal's Sandbox APIs across the dispute workflow. In `backend/paypal/client.py`, the app authenticates with PayPal OAuth 2.0 (`POST /v1/oauth2/token`), creates checkout orders via Orders v2 (`POST /v2/checkout/orders`), captures payments (`POST /v2/checkout/orders/{id}/capture`), fetches open disputes (`GET /v1/customer/disputes`), and issues full or partial refunds through the Captures API (`POST /v2/payments/captures/{capture_id}/refund`). It also includes a webhook handler and simulator (`/api/paypal/webhooks/simulate`) for `CUSTOMER.DISPUTE.CREATED` and `PAYMENT.CAPTURE.REFUNDED` events.

### Testing instructions
1. Run `start_demo.bat` on Windows (or start the backend with `uvicorn backend.api.main:app --port 8000` and the frontend with `npm run dev` on port 5173).
2. Open `http://localhost:5173`. The top header shows `PayPal API: SANDBOX_LIVE_CONNECTED`.
3. In the Customer View tab, click "Create Live Sandbox Order ($89.00)" to create a real order through PayPal's Orders v2 API, then click "Capture & File Dispute" to send it through the agents. You can also click any of the four preset test cases (two happy-path refunds, one rejected fraud claim, and one high-value escalation).
4. The app switches to the Merchant View, where you can watch the six agents run, read each agent's findings, and check the PayPal refund receipt. You can also click "Trigger Webhook" in the header to test a `CUSTOMER.DISPUTE.CREATED` webhook event.
5. A Postman collection (`docs/PayResolve_AI.postman_collection.json`) and pytest suite (`pytest tests/ -v`) are included in the repository.

### Overall experience rating: Please share why you gave this rating
PayPal's REST APIs for OAuth 2.0, Orders v2, Captures, Refunds, and Disputes were straightforward to integrate, and the error responses made it easy to debug order and capture states in the sandbox. Having `PayPal-Request-Id` idempotency headers built into the refund endpoint also makes automated payout code safer to test.
