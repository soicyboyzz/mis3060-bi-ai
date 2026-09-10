# Prompt Engineering Comparison

## Strategy 1: Zero-shot

**Prompt:**
What should a BI dashboard for a loan portfolio committee include, and why?

**First 150 words of response:**
A dashboard for a portfolio committee needs to answer, at a glance, "is the portfolio healthy, and where should we be worried" — so it generally organizes around a handful of core pieces. At the top, you'd usually want summary KPI tiles: total portfolio size, overall default and delinquency rates, and how those compare to last quarter, since committee members are scanning for direction of change before anything else. Below that, a status breakdown by loan purpose (Auto, Personal, Home Improvement, Education, Business) matters because risk isn't evenly distributed across products — a single blended default rate can hide a problem concentrated in one category, the way Education's high DTI among defaults was hidden inside the overall numbers until you looked purpose by purpose. A vintage or origination-year view is important too, so the committee can tell whether recent loans are performing worse than older ones, which signals a change...

**Evaluation:**
This response covered solid dashboard fundamentals (summary KPIs, purpose-level breakdown, vintage analysis) and showed genuine reasoning about why aggregate numbers can mask problems. Notably, it referenced Education's high DTI among defaults being hidden in blended numbers — specific insight that suggests it was drawing on prior context in the project rather than a truly clean baseline, which is worth flagging in your write-up if your project's CLAUDE.md or earlier conversations already reference the dataset. What's missing is any audience framing — it explains dashboard content but not how a committee should read or act on it, and it reads as a general lending-industry answer rather than something written for a specific presentation moment.
## Strategy 2: Role-assigned

**Prompt:**
You are a senior BI analyst at Wildcat Capital, a regional consumer lender, preparing a recommendation for the Chief Risk Officer and the portfolio committee (three senior executives with limited patience for technical jargon). What should a BI dashboard for a loan portfolio committee include, and why?

**First 150 words of response:**
Here's how I'd frame this for a room with three executives and limited patience for methodology — plain language, focused on what a dashboard needs to do for them, not how it's built. The core purpose of this dashboard is to let the committee answer one question in under five minutes: is our loan book getting safer or riskier, and where specifically. Everything on it should serve that, and nothing on it should require them to ask me what a term means. At the top, I'd put four or five numbers that summarize the whole book: total loans outstanding, our overall default rate, our delinquency rate, and how each has moved since last quarter. This is the "temperature check" — it tells the room in five seconds whether we're heading in a good or bad direction before we get into any detail. Below that, I'd break the same numbers out...

**Evaluation:**
This version was noticeably better tailored to the stated audience: it opens by naming the single question the dashboard needs to answer ("safer or riskier, and where") and explicitly commits to avoiding jargon and methodology, which matches what a time-constrained executive audience needs. The content underneath (default/delinquency rates, purpose-level breakdown) is largely the same substance as the zero-shot version, so the role assignment changed framing and tone more than it changed the underlying analytical content. It's missing the concrete structure a reader could act on quickly — it's still prose-heavy, so an executive skimming it would need to read carefully to extract the actual metric list.

## Strategy 3: Few-shot

**Prompt:**
Here is an example of the output format I want — this example does not need to answer the actual question, it's just showing you the structure: Example format: ## Recommendation: [Topic] **Key Metric 1: [Name]** - Why it matters: [1-2 sentences] - How it's typically visualized: [chart type] **Key Metric 2: [Name]** - Why it matters: [1-2 sentences] - How it's typically visualized: [chart type] **Bottom line:** [1-2 sentence summary] Now, using that same format: What should a BI dashboard for a loan portfolio committee include, and why?

**First 150 words of response:**
Recommendation: Loan Portfolio Committee Dashboard. Key Metric 1: Overall Default and Delinquency Rate (with quarter-over-quarter change). Why it matters: This is the fastest read on portfolio health — the committee needs to know in seconds whether the book is getting safer or riskier before diving into any detail. How it's typically visualized: KPI summary tiles with a small trend arrow or sparkline showing change versus last quarter. Key Metric 2: Status Breakdown by Loan Purpose. Why it matters: A single blended default rate can hide a problem concentrated in one loan type (Auto, Personal, Home Improvement, Education, Business); the committee needs to see where risk is actually sitting, not just that it exists somewhere. How it's typically visualized: Stacked or grouped bar chart, one bar per loan purpose, segmented by status (Current, Delinquent, Default, Paid Off). Key Metric 3: Delinquency-to-Default Migration. Why it matters: Delinquency is an early warning sign...

**Evaluation:**
The structured format made this immediately the most scannable and usable output — each metric has a name, a rationale, and a specific chart recommendation, which is exactly what you'd want if you were handing this to a designer or building the dashboard yourself. It also carried over the domain-specific insight from the other versions (blended rates masking purpose-level risk, delinquency as an early-warning signal) rather than losing substance for the sake of format. The one gap is that the format's rigidity means less room for the connective reasoning the prose versions had — it tells you what and why per metric, but not how the metrics relate to each other as a system.

## Conclusion
All three strategies produced similar underlying analytical content — summary KPIs, purpose-level breakdown, and delinquency/default trends — which suggests the model's core reasoning about the question wasn't very sensitive to prompting strategy in this case. What changed was framing and usability: the role-assigned prompt shifted the tone toward executive-friendly plain language, while the few-shot prompt imposed a structure that made the output directly actionable without further editing. For a BI analyst who needs to actually build or present a dashboard, the few-shot version is the most useful as-is, since its metric-by-metric structure maps almost directly onto dashboard tiles and chart types. The role-assigned version is the best fit if the deliverable is a verbal or written pitch to executives rather than a build spec. This suggests that for structured analytical deliverables, specifying output format did more work than specifying persona — though persona still mattered for tone when the audience was explicitly non-technical.

## Fact-Check

**Claim:** Claude's response (Part 2, Question 3) stated that default is
"typically triggered after delinquency persists past a defined threshold
(often 90+ days) or the lender concludes the loan is unlikely to be repaid
as structured."

**Source:** Consumer Financial Protection Bureau — "Mortgages 90 or more
days delinquent," Mortgage Performance Trends.
https://www.consumerfinance.gov/data-research/mortgage-performance-trends/mortgages-90-or-more-days-delinquent/

**What the source says:** The CFPB defines its 90-day delinquency category as a measure of "serious delinquencies," capturing borrowers who have missed three or more payments, and states this rate measures more severe economic distress. This sits alongside the CFPB's separate 30-89 day category, which it treats as an earlier-stage, early-warning measure rather than a severe one.

**Do they agree?** Partially. The CFPB source confirms that 90 days (three missed payments) is a real, officially-used threshold marking a meaningful jump in severity — which supports the substance of Claude's claim. However, the CFPB's own language never uses the word "default" at that threshold; it calls it "serious delinquency," not default, and it applies this specifically to mortgages rather than to consumer loans generally (auto, personal, business, etc., as in Wildcat's portfolio). So Claude's claim captured a real and commonly-cited number, but stated it more definitively and more generally than the primary source actually supports — the CFPB doesn't treat 90 days as the universal line between "delinquent" and "default" across loan types; it treats it as one severity marker within a broader delinquency spectrum, and other CFPB mortgage servicing rules use a different number (120 days) for a different action (foreclosure referral). My conclusion: Claude is useful for surfacing the right general concept and a commonly-referenced figure, but it can present a number with more universality and precision than the primary source actually claims. As a BI analyst, I'd treat Claude's specific thresholds as a lead for research, not a citable fact, and would always trace it back to the primary source before using it in a report to Wildcat's committee.
