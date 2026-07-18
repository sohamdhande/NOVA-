import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.knowledge_routes import router, PreviewRequest

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test():
    with open("founder_court.txt", "w") as f:
        f.write("""2. Executive Summary

FounderCourt (FC) is an AI-native system designed to help organizations detect when the original reasoning behind an expensive strategic commitment may no longer hold.

Companies make major commitments—such as aggressive hiring, market expansion, product investments, acquisitions, or infrastructure spending—based on assumptions that are true or believed to be true at the time.

The problem is that execution continues while reality changes.

Revenue may miss expectations. Pipeline may deteriorate. Churn may increase. A critical partnership may fail. Market conditions may shift. Yet the original commitment can continue because organizations monitor metrics and projects, but often do not systematically reconnect changing evidence to the specific assumptions that justified the original decision.

FounderCourt's core insight is:

Important strategic commitments can outlive the assumptions that justified them.

FC is initially testing a narrow version of this problem with growth-stage startup founders, CEOs, and CFOs.

The initial decision wedge is:

A significant hiring commitment based on a revenue plan.

For example:

"We are hiring 20 people because we expect revenue to reach $X."

That commitment may depend on 2–5 measurable assumptions:

Pipeline coverage remains above 3× target.
Win rate remains above 25%.
Churn remains below 5%.
Burn remains within plan.
Runway remains above 18 months.

Before prospective monitoring begins, leadership defines explicit reconsideration conditions, referred to internally as Kill Criteria.

For example:

"If pipeline coverage remains below 3× target for three consecutive weekly measurements, this hiring commitment must be formally reconsidered."

FC does not automatically change the decision and does not tell leadership to fire employees, stop expansion, or take another strategic action.

FC says:

"You previously agreed that this condition would require reconsideration. That condition now exists. The reasoning supporting the original commitment may no longer hold."

Humans retain final authority.

The immediate validation mechanism is the Decision Autopsy: a retrospective analysis of a real historical strategic commitment that reconstructs what was decided, why it was decided, what assumptions supported it, when evidence began materially challenging those assumptions, and when leadership actually reconsidered the commitment.

The difference between those two points is called the Reconsideration Gap.

FC's current objective is not to build the complete long-term platform. It is to prove, using real company data, that Reconsideration Gaps exist, matter to executives, and create enough value that CEOs or CFOs will pay for prospective monitoring.

The long-term vision is to build a system that preserves the reasoning behind consequential organizational commitments and uses AI to detect when changing evidence, hidden dependencies, or changing organizational narratives indicate that those commitments should be reconsidered.

3. The Problem
3.1 Strategic Commitments Are Made at One Point in Time

Organizations make consequential commitments based on their current understanding of reality.

Examples include:

Hiring 20–100 employees.
Expanding into a new geography.
Increasing sales capacity.
Building major infrastructure.
Committing significant marketing spend.
Delaying fundraising.
Launching a new business unit.
Acquiring another company.
Entering a long-term partnership.
Making a large capital investment.

These commitments are rarely arbitrary.

They are based on assumptions.

For example:

"We should hire 20 additional employees because revenue will grow 80%, pipeline coverage will remain above 3×, churn will remain below 5%, and we have sufficient runway."

The company approves the commitment and begins execution.

The decision then becomes operational reality.

But the assumptions that justified it can change.

3.2 Companies Monitor Metrics, but Not Necessarily Decision Logic

Companies already have dashboards.

They have:

CRM systems.
Financial dashboards.
FP&A tools.
BI platforms.
Project management software.
Board reporting.
OKRs.
Analytics tools.

These systems can tell leadership:

"Pipeline coverage is now 2.1×."

But they may not automatically answer:

"Six months ago, you approved hiring 20 employees because pipeline coverage was expected to remain above 3×. You explicitly agreed that sustained coverage below that level would require reconsideration. That condition now exists."

The difference is the connection between:

Current Evidence

and:

Original Strategic Commitment

and:

Original Reasoning

and:

Pre-agreed Reconsideration Conditions

FounderCourt is designed around maintaining that connection.

3.3 The Reconsideration Gap

FC defines a potential Reconsideration Gap as the time between:

The point when available evidence materially challenges a critical assumption behind an active commitment.

and:

The point when leadership actually reopens or formally reconsideres that commitment.

Example:

January:

Company approves aggressive hiring based on expected revenue growth.

March:

Pipeline coverage and conversion deteriorate enough to materially challenge the original revenue assumptions.

July:

Leadership freezes hiring.

Potential Reconsideration Gap:

March → July = approximately four months

FC does not claim:

"We would have saved the company $5 million."

That would require proving causality.

Instead, FC makes the narrower claim:

"Evidence materially challenging the assumptions supporting this commitment existed approximately four months before leadership formally reconsidered it."

The executive decides whether that gap mattered.

3.4 Why Existing Processes May Miss This

The problem can occur because:

Leadership attention moves to new problems.
Original assumptions are forgotten.
Decision rationale is buried in board decks and meeting notes.
Metrics are monitored independently of the decisions they justified.
Nobody explicitly owns the responsibility of reopening past decisions.
Organizations gradually move the goalposts.
The narrative supporting a decision changes without formal acknowledgment.
Hindsight changes how people remember the original decision.
Executives are overloaded with information.
Bad news may travel slowly through organizations.

FC's thesis is that companies have systems for tracking execution, but may lack a persistent system for tracking whether the reasoning behind important commitments still holds.

3.5 Known Structural Challenges

FC does not assume this is an easy problem.

Previous research identified several major risks.

Data Entry Friction

Executives may not want to manually document assumptions.

FC therefore explores using AI to extract commitments and assumptions from existing documents rather than forcing users to start from a blank page.

Alert Fatigue

If FC constantly tells executives that something changed, it becomes noise.

The initial system therefore relies on a small number of explicit, pre-agreed reconsideration conditions and human verification.

Integration Paradox

Different assumptions require fundamentally different evidence systems.

Financial assumptions may require CRM or financial data.

Regulatory assumptions may require semantic analysis of legal documents.

Partnership assumptions may depend on qualitative information.

FC therefore starts with quantitative assumptions rather than attempting universal assumption monitoring.

Psychological Resistance

Documenting the original reasoning behind decisions creates accountability.

FC initially targets CEOs, founders, and CFOs monitoring commitments they personally own rather than positioning FC as a surveillance system used by executives to monitor subordinate managers.

Materiality

Detecting that something changed is easier than determining whether it changed enough to deserve executive attention.

This remains one of FC's hardest long-term technical problems.

Trust

Strategic decisions involve sensitive information.

FC will eventually need strong security, permissions, evidence provenance, auditability, and transparent reasoning.

4. Solution & Product
4.1 Current Product Hypothesis

FounderCourt helps leadership maintain awareness of whether the assumptions supporting an expensive strategic commitment are still holding.

The initial workflow is:

Strategic Commitment

→ Original Rationale

→ 2–5 Critical Assumptions

→ Pre-agreed Kill Criteria

→ Evidence Monitoring

→ Condition Breached

→ Human Verification

→ Reconsideration Alert

→ Leadership Reviews

→ Human Decision

FC does not make the final decision.

4.2 Initial Wedge

The initial proposed wedge is:

Hiring commitments built on revenue plans.

Example:

"We will hire 20 additional employees because we expect ARR to reach $20M."

Potential assumptions:

Pipeline coverage remains above 3×.
Win rate remains above 25%.
Churn remains below 5%.
Revenue growth remains above an agreed threshold.
Runway remains above 18 months.

Example reconsideration condition:

"Pipeline coverage below 3× for three consecutive weekly measurements triggers formal reconsideration of the hiring plan."

This wedge is deliberately chosen because the underlying assumptions are relatively quantitative and measurable.

4.3 Decision Autopsy

The Decision Autopsy is FC's first validation product.

It retrospectively analyzes one historical commitment.

The process asks:

What was decided?
When was it decided?
Why was it decided?
What assumptions supported it?
What outcomes were expected?
What evidence was available at the time?
When did evidence first materially challenge a critical assumption?
When did leadership actually reconsider the commitment?
Was there a Reconsideration Gap?
Does leadership believe earlier awareness would have mattered?

The purpose is not to judge executives with hindsight.

The purpose is to reconstruct the decision using evidence available at each point in time.

4.4 Prospective Monitoring

If the Decision Autopsy validates the problem, FC moves from retrospective analysis to prospective monitoring.

Initially, this is concierge-first.

No complex integrations are required.

The workflow is:

CEO/CFO selects commitment

→ FC structures assumptions

→ Leadership approves assumptions

→ Leadership approves Kill Criteria

→ Agreed metrics collected manually

→ Thresholds evaluated

→ Potential breach manually verified

→ Leadership alerted

→ Response recorded

This deliberately separates two questions:

Is this valuable?

from:

Can this be automated?

FC should prove the first before investing heavily in the second.

4.5 AI in FounderCourt

FC does not use AI simply to appear AI-native.

AI is used where understanding unstructured language, reasoning, context, and relationships creates value.

Strategic Commitment Extraction

AI reads:

Board decks.
Strategy documents.
Meeting transcripts.
Planning documents.
Executive memos.

It proposes:

What was decided.
Why it was decided.
Expected outcomes.
Explicit assumptions.
Potential implicit assumptions.
Assumption Extraction

AI identifies load-bearing assumptions behind a commitment.

For example:

"We're hiring 20 salespeople to accelerate enterprise growth."

AI may identify potential assumptions around:

Enterprise demand.
Pipeline.
Sales productivity.
Ramp time.
Win rate.
Cash runway.

Humans approve critical assumptions.

Falsifiability Engine

AI helps transform:

"Enterprise demand should remain strong."

into something potentially measurable:

"Qualified enterprise pipeline remains above 3× quarterly enterprise revenue target."

AI proposes.

Humans approve.

Narrative Drift Detection

FC preserves the original rationale behind a strategic commitment.

Later, AI compares new organizational narratives against the original rationale.

Example:

Original:

"We are expanding into Europe because we expect €10M ARR within 18 months."

Later:

"Europe should primarily be evaluated as a long-term strategic brand investment."

FC could identify:

"The strategic rationale appears to have changed from near-term revenue generation to long-term brand investment. Has leadership formally changed the thesis supporting this commitment?"

This is intended as evidence for human review, not an accusation of dishonesty.

Contradiction Detection

AI can identify new information that appears inconsistent with assumptions supporting an active commitment.

Hidden Dependency Discovery

Long term, AI may identify that multiple apparently independent commitments rely on the same underlying assumption.

For example:

Europe Expansion

+ Hire 80 Employees

+ Delay Fundraising

may all implicitly depend on:

European revenue reaches $10M

A weakening assumption could therefore expose multiple commitments.

Decision Replay

Long term, FC could use temporal retrieval to reconstruct:

"What information was actually available when this decision was made?"

This could help distinguish:

Bad reasoning.
Bad luck.
Good reasoning followed by changed conditions.
Ignored warning signals.
Hindsight rewriting.
4.6 What AI Does Not Do

FC deliberately keeps certain responsibilities outside generative AI.

Numerical Kill Criterion evaluation → Deterministic

Financial calculations → Deterministic

Basic threshold monitoring → Deterministic

Quantitative anomaly detection → Statistical ML where appropriate

Consequential alert verification during early stages → Human

Final strategic decision → Human

The architectural principle is:

AI understands reasoning and context. Deterministic systems enforce explicit rules. Humans retain authority.

4.7 Long-Term Product Vision

If the initial wedge is validated, FC may evolve toward:

Strategic Commitment Contracts

Structured records stating:

We are doing X because we believe A/B/C. We expect Y by date Z. If K occurs, we agree to reconsider.

Decision Digital Twins

Living representations of major strategic commitments.

Temporal Decision Graph

A historical graph connecting:

Decision

→ Assumption

→ Evidence

→ Dependency

→ Change

→ Reconsideration

→ Outcome

Chronicle

Persistent organizational decision memory.

Decision Debt

Identification of commitments operating with:

Stale evidence.
Breached Kill Criteria.
Unresolved contradictions.
Overdue reviews.
Strategic Exposure Map

Portfolio-level understanding of strategic commitments and potentially exposed capital.

Cascading Decision Risk

Understanding how one deteriorating assumption could affect multiple connected commitments.

These are long-term hypotheses, not current validated product requirements.

5. Why Now

Modern foundation models create new technical possibilities for understanding unstructured organizational reasoning.

Historically, the reasoning behind decisions has been distributed across:

Board decks.
Emails.
Meeting transcripts.
Strategy documents.
Financial plans.
Internal reports.

Traditional software could store these documents but struggled to extract and maintain structured representations of the reasoning contained within them.

Modern AI can increasingly:

Extract commitments from unstructured documents.
Identify explicit and implicit assumptions.
Compare reasoning across time.
Detect semantic contradictions.
Connect evidence with assumptions.
Analyze longitudinal changes in strategic narratives.

This makes it potentially economical to build systems that track not just:

What is the company doing?

but:

Why did the company decide to do it, what needed to remain true, and does that reasoning still hold?

At the same time, companies are making increasingly complex decisions with more data, more software, and faster-changing markets.

FC's "why now" thesis is:

Foundation models make previously unstructured organizational reasoning machine-readable, creating the possibility of continuously connecting strategic commitments to the assumptions and evidence that justified them.

6. Market Opportunity

The initial market is deliberately narrow:

Growth-stage startups where founders, CEOs, and CFOs make significant hiring and capital-allocation commitments based on measurable growth assumptions.

Potential initial users include:

Founder/CEOs.
CFOs.
Finance leaders.
Chiefs of Staff.
Strategy leaders.

The initial wedge is not intended to represent FC's total market.

If the core mechanism works, the same underlying problem potentially exists across:

Hiring.
Market expansion.
Capital expenditure.
Product investment.
M&A.
Fundraising strategy.
Infrastructure commitments.
Enterprise transformation.
Investment committees.

Long-term customer segments could include:

Growth-stage startups.
Large enterprises.
Boards.
Private equity firms.
Venture capital firms.
Investment committees.
Strategy organizations.

The long-term market thesis is that organizations spend enormous amounts of capital executing strategic commitments but lack dedicated infrastructure for maintaining the integrity of the reasoning behind those commitments.

This market thesis remains unvalidated and should not be confused with demonstrated demand.

7. Business Model

The exact business model is not yet validated.

The initial approach should be paid concierge pilots.

Potential structure:

Decision Autopsy

A one-time paid or initially free/low-cost retrospective engagement used to prove value and generate evidence.

Commitment Monitoring

Recurring payment for monitoring a defined number of active strategic commitments.

Potential pricing dimensions could eventually include:

Number of active commitments.
Number of monitored assumptions.
Organization size.
Data complexity.
Strategic exposure.
Enterprise features.

The likely long-term model is B2B recurring software revenue.

However, pricing should not be finalized before willingness-to-pay testing.

The immediate commercial milestone is:

Get one CEO or CFO to pay FC to monitor the assumptions behind one real strategic commitment.

8. Traction & Milestones
Current Traction

FC is currently idea-stage and pre-product.

Current reported progress:

Two technical student co-founders.
10 founder customer-discovery conversations.
All 10 founders reportedly identified or confirmed the underlying problem.
Initial broad concept narrowed significantly based on research.
Initial customer hypothesis defined.
Initial decision wedge defined.
Decision Autopsy validation methodology designed.
Concierge-first validation strategy designed.
AI architecture narrowed to specific use cases.

The 10 founder conversations are early qualitative evidence.

They do not prove:

Willingness to pay.
Product-market fit.
Retention.
Data-sharing willingness.
Product adoption.

The current YC-readiness research assessed FC at 58/100 for application readiness and 14/100 for business validation, explicitly separating the two concepts.

Immediate Milestones

The evidence ladder is:

10 Founder Interviews

→ 1 Real Decision Autopsy

→ Confirmed Reconsideration Gap

→ Founder Confirms Gap Mattered

→ Prospective Monitoring Requested

→ First Paid Pilot

→ First Material Alert

→ Decision Reconsidered

→ Customer Continues Monitoring

→ First Renewal

The single highest-leverage immediate milestone is one real Decision Autopsy. The YC research similarly identified this as the strongest next proof-of-execution signal.

9. Competitive Landscape

FC operates adjacent to several existing categories:

Decision intelligence.
FP&A.
Strategic Portfolio Management.
Enterprise risk management.
Business intelligence.
AI decision support.
Decision journals.
Multi-agent AI systems.

Previously researched adjacent products and projects include DecisionX, Cloverpop, Dotwork, and Mira/thesis-monitoring approaches.

FC should not claim:

"Nobody has ever monitored assumptions."

That is not defensible.

The narrower differentiation hypothesis is:

Specific Strategic Commitment

→ Original Rationale

→ Explicit Assumptions

→ Pre-committed Reconsideration Conditions

→ Evidence Changes

→ Original Reasoning Potentially Breaks

→ Human Reconsideration

Compared with operational decision systems, FC is initially focused on relatively infrequent, expensive strategic commitments.

Compared with dashboards, FC connects metrics back to the original decision logic.

Compared with generic AI, FC aims to accumulate longitudinal organizational context.

Compared with decision journals, FC aims to move beyond passive documentation toward active reconsideration triggers.

Compared with enterprise platforms, FC initially attempts a lightweight, CEO/CFO-led deployment with minimal integration.

The long-term moat hypothesis is not an individual AI model.

It is the accumulated:

Strategic Commitments

Original Reasoning
Assumption History
Evidence History
Kill Criteria
Narrative Evolution
Confirmed Dependencies
Alerts
Human Feedback
Outcomes

This could eventually form a proprietary Temporal Decision Graph.

This moat does not exist yet.

It must be earned through adoption and accumulated data.

10. Go-to-Market

The initial GTM strategy is founder-led and highly manual.

Target

Growth-stage founder/CEO or CFO.

Entry Product

Decision Autopsy.

Initial Motion

Founder outreach:

"Tell us about a major commitment your company made that looked correct when approved but should have been reconsidered earlier because something changed."

Identify a historical case.

Run the Decision Autopsy.

Show the potential Reconsideration Gap.

Ask:

"Would knowing this earlier have mattered?"

If yes:

"Would you like us to monitor the assumptions behind your next major commitment?"

This creates the conversion path:

Customer Discovery

→ Decision Autopsy

→ Demonstrated Reconsideration Gap

→ Prospective Monitoring

→ Paid Pilot

→ Recurring Monitoring

The first GTM objective is not scale.

It is learning.

FC should initially acquire customers manually, work directly with them, observe how decisions are actually made, and understand what executives consider materially important.

11. Team

FounderCourt currently has two technical student co-founders.

The founders are capable of building the initial technical product themselves rather than outsourcing core development.

They are currently in college.

If accepted into YC, the founders have stated that they are prepared to work full-time on FC during the batch and arrange the necessary college permission to participate in San Francisco.

The team is currently strongest in:

Technical ability.
Product research.
Willingness to iterate on the thesis.
Competitive research.
Narrowing the product based on criticism.

The team still needs to demonstrate:

Shipping velocity.
Ability to build a working prototype quickly.
Ability to obtain real customer data.
Ability to convert discovery conversations into usage.
Sales ability.
Willingness to abandon hypotheses contradicted by evidence.

For YC specifically, the strongest way to demonstrate founder quality now is through action:

Idea

→ 10 Founder Conversations

→ Real Decision Autopsy

→ Prototype

→ Application

The corrected YC analysis identifies proof of execution—not lack of revenue—as FC's weakest current application signal.

12. Roadmap & Risks
Phase 0 — Current

Goal:

Validate the problem.

Actions:

Complete founder interviews.
Obtain one real historical strategic decision.
Run first Decision Autopsy.
Identify whether a genuine Reconsideration Gap exists.
Ask whether earlier awareness would have mattered.

Do not build the full platform.

Phase 1 — Prototype

Build:

Strategic Commitment Extraction.
Assumption Extraction.
Basic Decision Autopsy workflow.
Simple timeline reconstruction.

Goal:

Demonstrate FC's core mechanism.

Phase 2 — Concierge Monitoring

Monitor one active commitment manually.

Define:

2–5 assumptions.
Kill Criteria.
Data sources.
Monitoring cadence.

Deliver human-verified alerts.

Goal:

Prove prospective value.

Phase 3 — Paid Pilots

Convert successful Autopsy users into paid monitoring.

Measure:

Material alerts confirmed.
Alerts already known vs. genuinely new.
Decisions reconsidered.
Customer desire to continue.
Willingness to expand monitoring.

Goal:

Prove willingness to pay and early retention.

Phase 4 — Selective Automation

Automate only repeated workflows.

Potentially:

Data ingestion.
Threshold monitoring.
Strategic Commitment Extraction.
Assumption Extraction.
Evidence classification.

Goal:

Improve scalability without sacrificing trust.

Phase 5 — AI-Native Intelligence

Potential capabilities:

Narrative Drift Detection.
Contradiction Detection.
Temporal Decision Replay.
Hidden Dependency Discovery.

Goal:

Move from explicit monitoring toward deeper organizational decision intelligence.

Phase 6 — Decision Infrastructure

Potential long-term architecture:

Strategic Commitment Contracts.
Decision Digital Twins.
Temporal Decision Graph.
Chronicle.
Decision Debt.
Cascading Decision Risk.
Strategic Exposure Map.
Outcome Learning.

This phase depends entirely on earlier validation.

Primary Risks
Problem Frequency

Major strategic commitments may not occur frequently enough to support strong retention.

Willingness to Pay

Executives may recognize the problem but not pay to solve it.

Data Access

Customers may refuse access to sensitive information.

Alert Fatigue

Poor alerts could destroy trust quickly.

False Positives

Incorrectly flagging a major commitment before a board meeting could damage FC's credibility.

Psychological Resistance

Organizations may resist preserving decision accountability.

Integration Complexity

Different assumptions may require incompatible evidence pipelines.

Generic AI Commoditization

Foundation models may commoditize individual AI capabilities.

Category Risk

"Decision Integrity" is not currently an established purchasing category.

Attribution

FC may struggle to quantify ROI without making unjustified claims about avoided losses.

Consulting Trap

Manual Decision Autopsies could become services work rather than scalable software if the underlying process cannot be standardized.

Technical Materiality Problem

Determining when evidence is important enough to justify executive attention remains a difficult technical challenge.

13. Financials & The Ask
Current Financial Status

FC is currently pre-revenue.

Current state:

Revenue: $0.
Paying customers: 0.
Active production users: 0.
Completed Decision Autopsies: 0.
Confirmed Reconsideration Gaps: 0.
Paid monitoring pilots: 0.

This is consistent with FC's current idea-stage status but means the business thesis remains unvalidated.

Near-Term Financial Objective

The first meaningful financial milestone is not ARR scale.

It is:

One real customer paying for one real strategic commitment to be monitored.

The next milestones are:

First Paid Pilot

→ Multiple Paid Pilots

→ Customer Continues Paying

→ First Renewal

→ Expansion to Additional Commitments

→ Repeatable Pricing

Only after these milestones should FC develop detailed revenue forecasts.

Any multi-year financial projection today would be highly speculative.

Capital Strategy

At the current stage, FC should remain extremely capital-efficient.

The founders should avoid spending heavily on:

Enterprise infrastructure before demand.
Complex integrations.
Large-scale model training.
Large teams.
Extensive marketing.
Full Decision Graph architecture.

The founders' primary resources should be directed toward:

Customer discovery.
Decision Autopsies.
Prototype development.
Concierge pilots.
AI evaluation.
Customer acquisition experiments.
The Ask

For YC, the ask is not:

"Fund a fully validated decision-intelligence company."

It is:

"Back two technical founders who have identified a potentially important organizational problem, validated the problem qualitatively with 10 founders, narrowed it to a concrete initial wedge, and are rapidly testing whether AI can create a new system for detecting when the reasoning behind expensive strategic commitments breaks."

The immediate goal before or during the YC process is to move from:

Research

to:

Proof of Mechanism

by completing the first real Decision Autopsy.

Then:

Proof of Mechanism

to:

Proof of Value

through prospective monitoring.

Then:

Proof of Value

to:

Proof of Business

through paid pilots and retention.

The current YC research places FC at 58/100 application readiness while explicitly describing the startup as idea-stage, pre-prototype, with strong early problem validation but no completed proof-of-mechanism artifact.

The immediate ask is therefore:

Support FounderCourt in validating and building the first AI-native system that preserves the reasoning behind consequential organizational commitments and tells leadership when that reasoning may no longer hold.

The long-term ambition remains significantly larger:

Build the organizational intelligence layer that remembers why companies made their biggest bets, understands what those bets depend on, and helps leadership recognize when reality has changed enough to reconsider them.
""")

    with open("founder_court.txt", "r") as f:
        content = f.read()

    req = {
        "source_type": "markdown",
        "content": content,
        "title": "FC Strategy"
    }
    response = client.post("/preview", json=req)
    print("Response status:", response.status_code)
    try:
        data = response.json()
        print("Keys:", data.keys())
        print("Diagnostics:", data.get("diagnostics"))
        print("Warnings:", data.get("warnings"))
        for k in data.keys():
            if k not in ['diagnostics', 'warnings']:
                val = data.get(k)
                if isinstance(val, list):
                    print(f"{k}: {len(val)} items")
    except Exception as e:
        print("Error parsing JSON:", e)

test()
