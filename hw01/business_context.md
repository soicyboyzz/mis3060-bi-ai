# Business Context Exploration

## Question 1: Credit Risk Metrics

**Prompt:**
"Wildcat's loan data includes credit score, debt-to-income ratio, and annual income
for each borrower. In consumer lending, how are these three variables typically used
together to assess credit risk, and where does each one tend to break down as a
predictor on its own?"

**Summary of response:**
These three variables each tell you something different about a borrower, which is exactly why lenders don't rely on just one. Credit score looks backward at how someone has handled debt in the past, DTI looks at the present — how much of their income is already spoken for by other obligations — and income just tells you the scale of what they're working with. The catch is that each one has a blind spot on its own: a credit score won't catch a job loss that happened last month, DTI can't tell the difference between a steady paycheck and an unpredictable one, and a high income doesn't mean much if it's already stretched thin by other debt. Really, the useful information tends to show up when you look at how these variables interact rather than trusting any single one by itself.

**Follow-up question:**
Do borrowers who look risky on all three measures at once (low score, high DTI, low income) actually default at meaningfully higher rates in Wildcat's data than borrowers who are only weak on one of the three?

## Question 2: Portfolio Committee Priorities

**Prompt:**
"Wildcat's loan portfolio is split across Auto, Personal, Home Improvement, Education,
and Business loans. What does a portfolio committee typically want to see in a
quarterly credit review for a lender with this kind of purpose mix, and how might the
priorities differ across those five categories?"

**Summary of response:**
A portfolio committee is generally looking for the same handful of things each quarter — how the loan mix is shifting, how loans are moving between current, delinquent, and default, how different origination cohorts are aging, whether risk is too concentrated anywhere, and whether pricing actually covers the losses a segment is producing. What changes is how much weight each of those gets depending on the loan type. Auto loans lean on collateral value since there's a car backing the loan, personal loans get watched closely because there's nothing backing them at all, home improvement sits somewhere in between depending on whether it's secured, education loans are judged more on what happens after graduation than on how they're performing right now, and business loans get the most individual attention just because every business is different. You can already see some of this playing out in Wildcat's numbers — education loans showing the highest DTI among defaults, or business defaults carrying a noticeably higher rate than current business loans — though the sample sizes are small enough that none of it should be treated as settled yet.

**Follow-up question:**
How has Wildcat's loan mix shifted by origination year — is the portfolio drifting toward any one purpose over time, and does that shift line up with any change in default or delinquency rates?

## Question 3: Delinquency vs. Default

**Prompt:**
"Wildcat's loans are tagged as Current, Paid Off, Default, or Delinquent. What's the
practical difference between delinquency and default in consumer lending, and how
should a lender think about the transition between those two states?"

**Summary of response:**
Delinquency and default aren't really two levels of the same problem — they're two different stages. Delinquency just means a payment or two has been missed, but the lender still thinks the borrower might catch up, so the loan stays in a kind of holding pattern. Default is the point where the lender gives up on that idea and treats the loan as a loss, which usually means it gets written off, sent to collections, and reported to the credit bureaus. What actually matters for a lender isn't the default number itself but the roll rate — how many delinquent loans keep sliding toward default versus how many recover — since by the time something is officially in default, it's usually too late to do anything cheap about it. The catch with Wildcat's data specifically is that it only shows one snapshot in time, so there's no way to see that roll rate directly — the best we can do is compare delinquent and default loans side by side and see if they already look similar.

**Follow-up question:**
Within Wildcat's current Delinquent loans, do the borrower profiles (credit score, DTI, income) look more similar to Default loans or to Current loans — in other words, which of today's delinquencies look like they're already trending toward default?
