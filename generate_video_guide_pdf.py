import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))
        if self._pageNumber > 1:
            self.drawString(
                48,
                750,
                "PayResolve AI — 3-Minute Demo Video Script & Recording Guide",
            )
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(48, 742, letter[0] - 48, 742)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 48, 35, footer_text)
        self.drawString(
            48,
            35,
            "PayPal AI Hackathon 2026 — Target: Grand Prize ($12k) + Best Demo Delivery ($5k)",
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(48, 48, letter[0] - 48, 48)
        self.restoreState()


def build_video_guide_pdf(
    filename="docs/PayResolve_AI_Video_Script_and_Recording_Guide.pdf",
):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=48,
        rightMargin=48,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#0f172a")
    brand_blue = colors.HexColor("#003087")
    brand_cyan = colors.HexColor("#0070ba")
    text_dark = colors.HexColor("#1e293b")
    bg_light = colors.HexColor("#f8fafc")
    card_border = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=brand_blue,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=brand_cyan,
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12,
        textColor=text_dark,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-9,
        spaceAfter=2.5,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.3,
        leading=10.5,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.0,
        leading=10.2,
        textColor=text_dark,
    )

    story = []

    # HEADER
    story.append(
        Paragraph(
            "PayResolve AI: 3-Minute Demo Video Script & Recording Guide",
            title_style,
        )
    )
    story.append(
        Paragraph(
            "Engineered for the 5 Official Judging Criteria (20% Each) & the $5,000 Best Demo Delivery Prize",
            subtitle_style,
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=brand_blue, spaceAfter=8)
    )

    # META TABLE
    meta_data = [
        [
            Paragraph(
                "<b>Strict Length Limit:</b> Under 3:00 (Target: <b>2:35 – 2:45</b>)",
                body_style,
            ),
            Paragraph(
                "<b>Hosting Requirement:</b> YouTube (Public or Unlisted link)",
                body_style,
            ),
        ],
        [
            Paragraph(
                "<b>Screen to Record:</b> <code>http://localhost:5173</code> (1080p Fullscreen)",
                body_style,
            ),
            Paragraph(
                "<b>Special Prize Target:</b> Best Demo Delivery ($5k) + Agentic Commerce ($5k)",
                body_style,
            ),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[256, 260])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("BOX", (0, 0), (-1, -1), 1, card_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, card_border),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 1: RECORDING SETUP & DEVPOST RULES
    # =========================================================================
    story.append(
        Paragraph(
            "1. Pre-Recording Checklist (3 Minutes Before You Hit Record)", h1_style
        )
    )
    story.append(
        Paragraph(
            "In the official Devpost webinar, PayPal Developer Advocate Joe emphasized: <i>'Presentation is a full fifth (20%) of your score, "
            "and Best Demo Delivery is a real $5,000 prize. Judges are not required to watch beyond 3 minutes.'</i> Follow these 4 steps:",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>1. Start Both Servers:</b> Run <code>.\\start_demo</code> in your project folder so Backend (Port 8000) and Frontend (Port 5173) are running.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>2. Prepare Your Browser Window:</b> Open <code>http://localhost:5173</code> in Chrome, set zoom to <b>100%</b>, and press <b>F11</b> (or maximize window) so the dashboard looks super clean.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>3. How to Record Easily on Windows:</b> Use <b>OBS Studio</b>, <b>Loom</b>, or Windows Built-in Recorder (<b>Win + G</b> Xbox Game Bar or <b>Win + Shift + R</b> Snipping Tool with Microphone enabled).",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>4. Upload to YouTube:</b> Upload the recorded MP4 to YouTube, set visibility to <b>Public</b> or <b>Unlisted</b>, and paste the link into Step 3 on Devpost.",
            bullet_style,
        )
    )

    # =========================================================================
    # SECTION 2: HOW THIS SCRIPT HITS ALL 5 JUDGING CRITERIA
    # =========================================================================
    story.append(
        Paragraph(
            "2. How Our Script Scores 100% Across All 5 Judging Criteria", h1_style
        )
    )
    criteria_rows = [
        [
            Paragraph("<b>Judging Criterion (20% Each)</b>", table_header_style),
            Paragraph("<b>What the Judges Look For</b>", table_header_style),
            Paragraph(
                "<b>Where Our Video Proves It</b>", table_header_style
            ),
        ],
        [
            Paragraph("<b>1. Potential Impact (20%)</b>", table_cell_style),
            Paragraph(
                "Solves a real, high-value commerce problem for merchants and buyers.",
                table_cell_style,
            ),
            Paragraph(
                "<b>Scene 1 (0:00–0:30):</b> Explains how pre-claim resolution slashes 14-day ticket queues to 1.8s and saves $20+ chargeback fees.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>2. Innovation & Agentic AI (20%)</b>", table_cell_style),
            Paragraph(
                "Novel use of autonomous AI agents moving money safely with guardrails.",
                table_cell_style,
            ),
            Paragraph(
                "<b>Scene 2 (0:30–1:00):</b> Shows our 6-Agent Hub-and-Spoke DAG where Intake is isolated from Settlement to prevent prompt injection.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>3. Technical Implementation (20%)</b>", table_cell_style),
            Paragraph(
                "Deep, meaningful PayPal Sandbox integration beyond a simple checkout button.",
                table_cell_style,
            ),
            Paragraph(
                "<b>Scenes 3–6 (1:00–2:45):</b> Shows live OAuth2, Capture Refunds, 40% Partial Concessions, Webhooks, and Order Creation.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>4. Design & UX (20%)</b>", table_cell_style),
            Paragraph(
                "Shows both the Customer View and Merchant View clearly (Eddie's tip).",
                table_cell_style,
            ),
            Paragraph(
                "<b>Throughout Video:</b> Split-screen UI shows Buyer Chat on the left and Merchant 6-Agent DAG + JSON Inspector on the right.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>5. Presentation (20% + $5k)</b>", table_cell_style),
            Paragraph(
                "Clear story, both happy and unhappy paths tested, under 3 minutes.",
                table_cell_style,
            ),
            Paragraph(
                "<b>Scenes 3 & 4:</b> Walks through 2 Happy Paths (Full & Partial Refund) and 2 Unhappy Paths (Fraud Blocked & Human Escalation).",
                table_cell_style,
            ),
        ],
    ]
    criteria_table = Table(criteria_rows, colWidths=[135, 165, 216])
    criteria_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 1, card_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, card_border),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(criteria_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: WORD-FOR-WORD TIMED SCRIPT & SCREEN ACTIONS
    # =========================================================================
    story.append(
        Paragraph(
            "3. Word-for-Word Timed Script & Screen Actions (Total Time: 2:45)",
            h1_style,
        )
    )
    story.append(
        Paragraph(
            "Read the <b>Right Column</b> at a natural, confident pace while performing the mouse clicks in the <b>Left Column</b>:",
            body_style,
        )
    )

    script_rows = [
        [
            Paragraph("<b>Time & What to Click on Screen</b>", table_header_style),
            Paragraph(
                "<b>Exact Word-for-Word Script to Speak Out Loud</b>",
                table_header_style,
            ),
        ],
        [
            Paragraph(
                "<b>Scene 1: The Problem & Hook</b><br/><b>[0:00 – 0:30]</b><br/><br/>• Start on <code>http://localhost:5173</code>.<br/>• Hover over the top KPI cards (<i>1.8 sec Resolution Speed</i>, <i>Chargeback Fees Saved</i>).",
                table_cell_style,
            ),
            Paragraph(
                "“Hi! Every year, online merchants lose billions to payment disputes and $20+ chargeback fees, while customers wait up to 14 days in support queues for a simple refund. Yet 80% of disputes start as simple pre-claim inquiries.<br/><br/>"
                "We built <b>PayResolve AI</b>—an autonomous 6-Agent Dispute Resolution and Settlement Swarm powered by Google Gemini and the PayPal Developer Platform that investigates, risk-scores, and settles claims in under 2 seconds.”",
                table_cell_style,
            ),
        ],
        [
            Paragraph(
                "<b>Scene 2: Architecture & Security</b><br/><b>[0:30 – 1:05]</b><br/><br/>• Point to the green <b>PayPal Sandbox REST API</b> badge in the top-right.<br/>• Point to the <b>Left Pane</b> (Buyer Portal) and <b>Right Pane</b> (6-Agent DAG).",
                table_cell_style,
            ),
            Paragraph(
                "“PayResolve AI connects directly to the live PayPal Sandbox REST API via OAuth 2.0. Our dashboard gives you both perspectives: the Customer Dispute Portal on the left, and the Merchant’s 6-Agent Hub-and-Spoke DAG on the right.<br/><br/>"
                "Why use 6 specialized agents instead of one chatbot? Because a single chatbot with refund permissions is vulnerable to prompt injection. In our swarm, the Customer Intake Agent has zero authority to touch money—every payout must pass the Evidence Verifier, Fraud Scorer, Policy Auditor, and Supervisor Arbiter.”",
                table_cell_style,
            ),
        ],
        [
            Paragraph(
                "<b>Scene 3: Happy Paths (Full & Partial Refunds)</b><br/><b>[1:05 – 1:45]</b><br/><br/>• Click <b>Scenario 1 ($89.99 Lost Package)</b>.<br/>• Click <b>Node 02</b> & <b>Node 06</b> in the DAG.<br/>• Then click <b>Scenario 2 ($120.00 Cosmetic Scratch)</b>.",
                table_cell_style,
            ),
            Paragraph(
                "“Let’s test two happy paths. In <b>Scenario 1</b>, a VIP buyer reports a lost $89.99 keyboard. Watch the 6 agents execute: Node 2 verifies UPS tracking is stalled in Memphis; Node 3 scores a safe 0.02 fraud risk; Node 4 confirms it’s within our $250 cap; and Node 6 settles an instant full refund on the PayPal Sandbox with a live <code>PP-RFD</code> transaction ID.<br/><br/>"
                "In <b>Scenario 2</b>, studio headphones arrive with a minor box crush and scratch, but still work. Instead of losing $120 and return shipping, our Policy Auditor negotiates an instant 40% ($48.00) keep-the-item partial refund on PayPal Sandbox.”",
                table_cell_style,
            ),
        ],
        [
            Paragraph(
                "<b>Scene 4: Unhappy Paths (Fraud Blocked & Human Escalation)</b><br/><b>[1:45 – 2:20]</b><br/><br/>• Click <b>Scenario 3 ($215.00 Fraud)</b>.<br/>• Point to the red <b>0.99</b> Fraud Score.<br/>• Click <b>Scenario 4 ($480.00 Escalation)</b>.<br/>• Click the amber <b>Approve $480.00 PayPal Refund</b> button!",
                table_cell_style,
            ),
            Paragraph(
                "“Now let’s test the unhappy paths. In <b>Scenario 3</b>, a 6-day-old burner account with 3 recent disputes claims a $215 package never arrived. Our Evidence Agent detects USPS GPS delivery plus a direct recipient signature. Fraud risk spikes to 0.99, and the Swarm blocks the payout—saving $215.<br/><br/>"
                "In <b>Scenario 4</b>, a buyer disputes a $480 monitor left in an unlocked lobby. Because $480 exceeds our $250 autonomous guardrail, the Swarm pauses payout and escalates to the merchant. With one click on <b>Approve PayPal Refund</b>, the human merchant triggers the live PayPal Sandbox settlement.”",
                table_cell_style,
            ),
        ],
        [
            Paragraph(
                "<b>Scene 5: PayPal Webhooks & Live Orders</b><br/><b>[2:20 – 2:45]</b><br/><br/>• Click <b>Simulate PayPal Webhook</b> in the top header.<br/>• Scroll down to the <b>Webhook Event Logs</b> table.<br/>• Click <b>Create Live PayPal Order</b> in the header.",
                table_cell_style,
            ),
            Paragraph(
                "“Finally, PayResolve AI listens to asynchronous <code>CUSTOMER.DISPUTE.CREATED</code> PayPal Webhooks—replying with HTTP 200 OK and running the 6-agent swarm automatically—and lets us create and capture live PayPal Sandbox Checkout orders right from the console.<br/><br/>"
                "PayResolve AI turns 14-day dispute headaches into 2-second autonomous settlements. Thank you for watching!”",
                table_cell_style,
            ),
        ],
    ]

    script_table = Table(script_rows, colWidths=[150, 366])
    script_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 1, card_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, card_border),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(script_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Generated Video Guide PDF at: {os.path.abspath(filename)}")


if __name__ == "__main__":
    output_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "docs/PayResolve_AI_Video_Script_and_Recording_Guide.pdf"
    )
    build_video_guide_pdf(output_path)
