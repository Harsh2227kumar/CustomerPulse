# Adjacent RBI / Indian Regulatory Obligations for an AI Complaint-Intelligence Engine (status as of 12 Oct 2026)

> Scope: obligations adjacent to complaint handling (fraud, KYC/AML, data protection, IT/outsourcing/cyber, AI/model governance, record retention) and how each touches an LLM (Amazon Bedrock) + vector-search complaint/compliance engine for an Indian commercial bank.
>
> **Big structural change to note up front:** On 28 Nov 2025 RBI consolidated ~9,000+ circulars into 238–244 entity-wise "Reserve Bank of India (Commercial Banks – X) Directions, 2025" and repealed the old Master Directions (incl. KYC MD 2016). On 31 Jul 2026 RBI issued a second wave (Fraud Risk Management Directions 2026; Cybersecurity/Technology Risk Directions; Digital Payment Security Controls Directions). Any rule-engine citing "MD KYC 2016" or "MD FRM 15 Jul 2024" must now map to the new instrument names, while substance is largely carried over.
>
> Labels used: **[IN FORCE]**, **[FUTURE-DATED]** (issued, not yet effective), **[DRAFT]**, **[ADVISORY]** (non-binding report), **[UNVERIFIED]** (only secondary source / conflict).

## Q1. Fraud Risk Management (FRM) – classification, FMR, EWS, red-flagging, natural justice, complaint→fraud link, LEA/I4C/1930/CFCFRMS/MuleHunter.AI

### Takeaway
The 15 Jul 2024 FRM Master Directions were repealed and replaced for commercial banks by the RBI (Commercial Banks – Fraud Risk Management) Directions, 2026 (31 Jul 2026, effective immediately), which keep the core architecture (EWS/red-flagging, FMR reporting, natural justice) but drop monthly certificates/flash reports and recommend LEA reporting for frauds ≥ ₹1 lakh. Separately, customer complaints of fraudulent electronic transactions are about to get a new liability/compensation regime from 1 Jan 2027, so the complaint engine must be the trigger point for fraud workflows.

### Cited Findings
**Instrument status**
- [IN FORCE] RBI notified the RBI (Commercial Banks – Fraud Risk Management) Directions, 2026 on 31.07.2026, effective the same day, consolidating/repealing/superseding the 2024 fraud directions; a savings clause keeps actions taken under the 2024 regime alive — [Mondaq](https://www.mondaq.com/rbi-consolidates-and-notifies-rbi-(commercial-banks-fraud-risk-management)-directions-2026/1833526)
- Scope 2026: only commercial banks, corresponding new banks and SBI; Local Area Banks, Payments Banks, RRBs and AIFIs moved to separate directions — [Mondaq](https://www.mondaq.com/rbi-consolidates-and-notifies-rbi-(commercial-banks-fraud-risk-management)-directions-2026/1833526)
- 2024 predecessor: Master Directions on Fraud Risk Management in Commercial Banks (incl. RRBs) and AIFIs, RBI/DOS/2024-25/118, 15 Jul 2024, which superseded the 2016 Fraud Classification & Reporting directions and rescinded 36 circulars — [RBI](https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12702); [SCC Online](https://www.scconline.com/blog/post/2024/07/17/rbi-revises-master-directions-on-fraud-risk-management-in-regulated-entities-legal-news)

**Timelines (from 2024 MD; carried into 2026 per secondary sources – re-verify clause numbers in 2026 text)**
- Red-flagged account (RFA) decision is at individual-bank level; status must be reported on CRILC within 7 days — [ELP / KPMG summaries](https://elplaw.in/wp-content/uploads/2024/07/RBI-Revised-Master-Directions-on-Fraud-Risk-Management-July-2024.pdf); [KPMG](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2024/09/boardroom-briefing-rbis-new-guidelines-on-strengthening-fraud-risk-management.pdf)
- Decision to classify an RFA as fraud or otherwise within 180 days of red-flagging — [KPMG](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2024/09/boardroom-briefing-rbis-new-guidelines-on-strengthening-fraud-risk-management.pdf); [Grant Thornton](https://www.grantthornton.in/globalassets/1.-member-firms/india/assets/pdfs/services/rbi-master-directions-on-fraud-risk-management.pdf)
- FMR reporting timeline reduced to 14 days (from 21 days) under the 2024 MD — [KPMG](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2024/09/boardroom-briefing-rbis-new-guidelines-on-strengthening-fraud-risk-management.pdf); [TaxTMI](https://www.taxtmi.com/rss_feed_blog?id=867642)
- Natural justice before fraud classification: show-cause notice, minimum 21 days to respond, reasoned order (following SBI v. Rajesh Agarwal, SC 2023) — [TaxTMI](https://www.taxtmi.com/rss_feed_blog?id=867642); [IndiaLaw](https://www.indialaw.in/blog/banking-and-finance/rbi-issues-revised-master-directions-on-fraud/)
- 2026 change: natural-justice requirement now expressly covers all persons/entities classified as fraud plus promoters and whole-time/executive directors wherever classification has civil consequences (penal measures, caution listing) — [Mondaq](https://www.mondaq.com/rbi-consolidates-and-notifies-rbi-(commercial-banks-fraud-risk-management)-directions-2026/1833526)
- 2026 change: board sets the threshold for cases going to the Special Committee of the Board for Monitoring & Follow-up of Frauds (SCBMF) — [Mondaq](https://www.mondaq.com/rbi-consolidates-and-notifies-rbi-(commercial-banks-fraud-risk-management)-directions-2026/1833526)
- 2026 change: banks "advised" to report all frauds of ₹1 lakh and above to law-enforcement agencies (linked to s.33 BNSS) — [Mondaq](https://www.mondaq.com/rbi-consolidates-and-notifies-rbi-(commercial-banks-fraud-risk-management)-directions-2026/1833526)
- 2026 change: FMR online portal/FUA retained; separate monthly certificates and flash reports removed — reporting runs through FMR/CFR; court-ordered FMR withdrawal/name removal may be actioned immediately then informed to a WTD — [Mondaq](https://www.mondaq.com/rbi-consolidates-and-notifies-rbi-(commercial-banks-fraud-risk-management)-directions-2026/1833526)

**Customer complaints of unauthorised/fraudulent e-transactions (the complaint→fraud bridge)**
- [FUTURE-DATED] RBI press release 24 Jun 2026 issued Responsible Business Conduct (Commercial Banks) Third Amendment Directions, 2026 (and equivalents for SFBs, PBs, LABs, RRBs, UCBs, RCBs), effective 1 Jan 2027. They (i) extend customer-liability limits from "unauthorised" to other categories of fraudulent electronic banking transactions, (ii) reduce bank complaint-processing time for such complaints, (iii) introduce a compensation mechanism for small-value frauds — [RBI press release](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63011)
- [DRAFT figures – final may differ] The March 2026 draft proposed: burden of proving customer liability lies on bank; zero liability for bank negligence or timely-reported third-party breach; small-value fraud up to ₹50,000 compensated up to ₹25,000 or 85% of loss; complaints resolved within 30 days; draft effective date was 1 Jul 2026 (moved to 1 Jan 2027 in final) — [Angel One](https://oga-prod.angelone.in/news/economy/rbi-proposes-new-rules-effective-july-1-2026-safeguards-against-digital-banking-fraud); [ELP](https://elplaw.in/wp-content/uploads/2026/06/RBI-Tightens-Customer-Protection-Framework-for-Fraudulent-Electronic-Banking-Transactions.pdf); [RBI](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63011)
- Final directions require banks to reverse eligible transactions without loss of interest to customers — [ELP / secondary summary of final](https://elplaw.in/wp-content/uploads/2026/06/RBI-Tightens-Customer-Protection-Framework-for-Fraudulent-Electronic-Banking-Transactions.pdf)
- The March 2026 PIB release frames the revision as replacing the 2017 limited-liability instructions and pairing it with AI-driven fraud analytics and anti-mule safeguards — [TaxHeal / PIB](https://www.taxheal.com/rbi-strengthens-framework-on-unauthorised-electronic-banking-transactions.html)

**Ecosystem reporting: I4C / 1930 / CFCFRMS / MuleHunter.AI / IDPIC**
- CFCFRMS (under I4C, launched 2021) integrates State/UT police with banks; victims call 1930, police create a ticket on CFCFRMS routed to victim's bank and beneficiary bank/wallet for real-time hold — [Taxguru / NCRP SOP sources](https://taxguru.in/?p=1031955); [MP High Court SOP](https://mpsja.mphc.gov.in/Joti/pdf/LU/SOP%20FOR%20NCRP-CFCFRMS,%20CUSTODY,%20RESTORATION%20MONEY%20&%20GRIEVANCE%20REDRESSAL.pdf)
- A comprehensive SOP for NCRP-CFCFRMS (hold, restoration, suspension, grievance timelines) issued 2 Jan 2026 — [prashantkanha.com (secondary)](https://www.prashantkanha.com/ncrp-cfcfrms-cyber-fraud-sop-2026/) [UNVERIFIED against MHA original]
- CFCFRMS 2.0 platform reported 29 Jul 2026; ~₹11,158 cr saved from 32.8 lakh complaints and 1,586 entities onboarded by June 2026 — [SuperKalam (PIB digest)](https://superkalam.com/current-affairs/29-07-2026/cfcfrms-2-0-platform-27181ced-b1eb-4f42-acee-14b9c920682f) [secondary]
- MuleHunter.AI (built by RBIH) assigns mule-probability scores to accounts; live in 26 banks as of 31 Mar 2026, 4 more in progress; Finance Ministry has asked banks to adopt it — [Outlook Business](https://www.outlookbusiness.com/economy-and-policy/finance-ministry-asks-banks-to-use-mulehunterai-to-check-digital-fraud); [Business Standard](https://www.business-standard.com/amp/finance/news/what-is-mulehunter-ai-rbi-s-latest-tool-against-financial-fraud-explained-124120600865_1.html); [TaxHeal/PIB](https://www.taxheal.com/rbi-strengthens-framework-on-unauthorised-electronic-banking-transactions.html)
- Indian Digital Payment Intelligence Corporation (IDPIC), s.8 company incorporated 16 Oct 2025, mandate: real-time detection/prevention of digital payment fraud using AI/ML — [TaxHeal/PIB](https://www.taxheal.com/rbi-strengthens-framework-on-unauthorised-electronic-banking-transactions.html)
- Banks advised to deploy real-time transaction monitoring, AI/ML pattern detection and network analytics for mule networks — [TaxHeal/PIB](https://www.taxheal.com/rbi-strengthens-framework-on-unauthorised-electronic-banking-transactions.html)

### Inferences
- **Machine-checkable rules for the engine:** (a) any complaint classified as "unauthorised/fraudulent e-transaction" must spawn a fraud case ID and start clocks: FMR ≤14 days from detection/classification (verify 2026 clause), LEA referral flag if amount ≥ ₹1 lakh, from 1 Jan 2027 the new reduced complaint-resolution TAT and compensation eligibility check (≤₹50k draft threshold – parameterise, don't hard-code); (b) cluster detection across complaints (vector similarity on narratives, shared beneficiary account/UPI handle/device) is a natural EWS input and should feed RFA review, with 7-day CRILC and 180-day classification timers for credit accounts; (c) the engine must never auto-label a customer/borrower as "fraud" — natural justice (SCN, ≥21 days, reasoned order) means AI output can only be "suspected/flag for review".
- Complaint narratives frequently contain 1930 acknowledgement/NCRP numbers; extraction of these as structured fields enables reconciliation with CFCFRMS tickets and avoids duplicate handling.
- Removal of monthly certificates in 2026 increases reliance on FMR data accuracy — an audit trail linking complaint → fraud case → FMR is a strong value proposition.

### Gaps
- Exact clause text of the 2026 FRM Directions (whether 14-day FMR, 7/180-day RFA timelines, EWS annex are unchanged) was not retrieved; only Mondaq summary of changes. Verify on rbi.org.in.
- Final numeric parameters of the 1 Jan 2027 customer-liability/compensation regime (customer reporting windows, compensation cap, resolution TAT, shadow-credit days) not confirmed — press release gives only themes. The 2017 baseline (zero liability if reported within 3 working days, limited liability 4–7 days, shadow credit within 10 working days, resolution within 90 days) is from prior knowledge and was not re-verified this session.
- Whether bank systems must push data to/receive from MuleHunter.AI or CFCFRMS via API (and whether that is mandatory) not confirmed.

## Q2. KYC (Master Direction 2016 → Commercial Banks – KYC Directions 2025): periodic updation, notices, low-risk relief, account freezing; complaint relevance

### Takeaway
KYC MD 2016 was repealed on 28 Nov 2025 and replaced "as-is" by the RBI (Commercial Banks – Know Your Customer) Directions, 2025; the June 2025 amendment's low-risk relief (allow all transactions, update within 1 year of due date or by 30 Jun 2026, whichever later) and the mandatory 3+3 intimation regime (from 1 Jan 2026) are the rules most relevant to "account frozen/blocked for KYC" complaints. No extension beyond 30 Jun 2026 was found.

### Cited Findings
- [IN FORCE] On 28 Nov 2025 RBI issued the consolidated RBI (Commercial Banks – Know Your Customer) Directions, 2025 and concurrently repealed KYC MD 2016; consolidation was on an "as-is" basis with minor editorial reorganisation — [JSA Prism Dec 2025](https://www.jsalaw.com/wp-content/uploads/2025/12/JSA-Prism-FinTech-December-2025-KYC-Master-Directions.Final_.pdf); [Mondaq](https://webiis08.mondaq.com/india/diversity-equity-inclusion/1725628/navigating-reserve-bank-of-indias-new-kyc-master-directions)
- Overall consolidation: ~9,000+ circulars into 238 (later cited as 244) function-wise directions; ~9,445 circulars repealed — [Taxscan](https://www.taxscan.in/top-stories/rbi-issues-238-consolidated-master-directions-9000-circulars-guidelines-reorganised-1439158); [TeamLease RegTech](https://teamleaseregtech.com/updates/article/49882/rbi-notified-244-new-master-directions-and-repealed-withdrew-9445-circulars/); [News On Air](https://www.newsonair.gov.in/rbi-repeals-9000-circulars-consolidates-rules-into-244-master-directions-to-ease-compliance/)
- KYC (Amendment) Directions, 2025 issued 12 Jun 2025, effective immediately: for low-risk individual customers, RE shall allow all transactions and ensure KYC updation within one year of its falling due or up to 30 Jun 2026, whichever is later, with regular monitoring; applies also where updation had already fallen due — [K&S Partners](https://ksandk.com/newsletter/rbi-kyc-amendment-2025/); [Taxguru](https://taxguru.in/rbi/reserve-bank-india-know-customer-kyc-amendment-directions-2025.html); [SS Rana](https://ssrana.in/articles/kyc-simplified-rbis-customer-centric-kyc-amendment-explained/)
- Notices: at least 3 advance intimations before due date (at least 1 by letter) and at least 3 reminders after due date (at least 1 by letter); implementation no later than 1 Jan 2026 — [Conventus Law](https://conventuslaw.com/report/india-rbi-issues-new-kyc-amendment-directions-2025/); [Lexplosion](https://lexplosion.in/rbi-amends-kyc-master-directions-to-introduce-additional-requirements-regarding-updation-periodic-updation-of-kyc/)
- Business Correspondents may collect self-declarations for unchanged KYC/address updates, captured electronically after biometric e-KYC; ultimate responsibility remains with the bank — [K&S Partners](https://ksandk.com/newsletter/rbi-kyc-amendment-2025/); [SS Rana](https://ssrana.in/articles/kyc-simplified-rbis-customer-centric-kyc-amendment-explained/)
- Press coverage framed the amendment as protecting low-risk accounts from freezing pending re-KYC — [Outlook Business](https://www.outlookbusiness.com/economy-and-policy/low-risk-accounts-safe-from-freeze-as-rbi-extends-kyc-deadline)
- No 2026 circular extending the 30 Jun 2026 low-risk deadline was found in searches — [search of K&S, Taxguru, SS Rana, Conventus coverage above] (absence of evidence; see Gaps)

### Inferences
- **Complaint taxonomy hook:** "Account frozen / debit-blocked / partial freeze due to KYC" complaints should be checked against: customer risk category; KYC due date (risk-based periodicity – commonly 2/8/10 years for high/medium/low – see Gaps); whether ≥3 pre-due and ≥3 post-due intimations (≥1 by letter each) were sent and logged; for low-risk individuals, whether freezing occurred before max(due date + 1 yr, 30 Jun 2026) → if so, likely deficiency in service. This is fully machine-checkable if the engine can query CBS/KYC metadata.
- Because 30 Jun 2026 has passed, low-risk customers whose due date was before ~30 Jun 2025 are now outside relief; those with later due dates still have 1-year windows — the engine needs per-customer date arithmetic, not a single cut-off. (My reading; no source states this computation explicitly.)
- Citations in AI-drafted responses must reference the 2025 Commercial Banks KYC Directions, not MD 2016 (repealed).
- KYC data (Aadhaar/PAN/OVD numbers) commonly appears in complaint text — must be masked before LLM prompts/embedding (also Aadhaar Act restrictions and DPDP minimisation).

### Gaps
- Periodicity 2/8/10 years (high/medium/low risk) is longstanding KYC MD rule from prior knowledge; not re-verified in the 2025 consolidated text this session.
- Whether RBI extended the low-risk relief beyond 30 Jun 2026 (e.g., Jul–Oct 2026 circular) – not found; verify on RBI notifications.
- Exact paragraph numbers in the 2025 Commercial Banks KYC Directions; rules on partial freezing (credits allowed/debits blocked) not retrieved.

## Q3. RBI FREE-AI Framework (13 Aug 2025) and subsequent AI/model guidance

### Takeaway
FREE-AI is an [ADVISORY] committee report (7 Sutras, 6 pillars, 26 recommendations), not binding directions; RBI's first binding-track follow-up is the [DRAFT] Guidance on Regulatory Principles for Model Risk Management, 2026 (24 Jun 2026, comments closed 24 Jul 2026), which would require a board-approved MRM framework covering all models including AI/ML and third-party models. For an AI complaint engine, Recs 14–18 and 20–25 (board AI policy, DPDP-aligned data lifecycle, lifecycle governance with human oversight, product approval, consumer protection incl. AI disclosure and recourse, red teaming, BCP, incident reporting, inventory, audit, disclosures) are the de-facto design checklist supervisors will use.

### Cited Findings
- FREE-AI report released 13 Aug 2025 by committee chaired by Prof. Pushpak Bhattacharyya (IIT Bombay); constituted 26 Dec 2024; 7 Sutras, 26 recommendations under six pillars — [RBI press release](https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=61018); [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)
- Six pillars: Infrastructure, Policy, Capacity, Governance, Protection, Assurance — [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306); [Fintech Global](https://fintech.global/2025/08/18/rbi-panel-calls-for-ai-framework-in-finance-sector/)
- 7 Sutras: (1) Trust is the Foundation; (2) People First – AI supports human decisions, humans retain final authority/override, citizens should be made aware when dealing with AI; (3) Innovation over Restraint; (4) Fairness and Equity; (5) Accountability – deploying entity remains accountable, cannot delegate to the model; (6) Understandable by Design – explainability as core design feature; (7) Safety, Resilience and Sustainability — [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)
- Report states existing legal framework broadly sufficient but recommends AI-specific changes to RBI directions on outsourcing, cybersecurity, digital lending, customer service and fraud risk management; suggests RBI may issue consolidated AI Guidance — [cybersigmacs (secondary)](https://cybersigmacs.com/blog/rbi-ai-guidelines-model-risk-management-2026/); [RBI report, Rec 6](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)
- Key recommendations (all from [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)):
  - Rec 8 AI liability framework: graded liability; REs remain liable for customer losses; supervisory leniency only for one-off issues where safeguards followed, not repeated breaches/gross negligence/failure to fix known issues.
  - Rec 10 Capacity building in REs: AI competence for Board/C-suite; training for staff using AI.
  - Rec 14 Board-approved AI policy: governance, accountability, risk appetite, safeguards, auditability, consumer protection, disclosures, model lifecycle, liability.
  - Rec 15 Data lifecycle governance: controls on collection, access, use, retention, deletion in AI systems aligned with DPDP Act.
  - Rec 16 AI system governance: full lifecycle documentation, validation, drift/degradation monitoring; governance before deploying autonomous AI; human oversight for medium- and high-risk uses.
  - Rec 17 Product approval: all AI-enabled products through product approval with AI-specific risk evaluation.
  - Rec 18 Consumer protection: board-approved framework on transparency, fairness, accessible recourse; covers disclosure of AI use, grievance redressal and human escalation (paras 4.4.54–55).
  - Rec 19 Cybersecurity: identify AI-specific security risks, strengthen controls.
  - Rec 20 Red teaming: structured adversarial testing across lifecycle; medium/high-risk at least semi-annually, plus trigger-based.
  - Rec 21 BCP for AI: AI-specific degradation scenarios, fallback mechanisms, periodic drills.
  - Rec 22 AI incident reporting: dedicated framework, good-faith approach encouraging prompt disclosure.
  - Rec 23 AI inventory: internal inventory updated at least half-yearly, available for audit; regulators to keep anonymised sector repository.
  - Rec 24 AI audit: risk-based audit of data, models, outputs; internal audit for all, third-party audit for high-risk; framework reviewed at least every 2 years.
  - Rec 25 AI disclosures in annual reports and websites (format to be specified by regulators).
  - Rec 26 Voluntary AI compliance toolkit (fairness, transparency, accountability, robustness).
  - Annexures IV–V suggest AI-specific outsourcing contract clauses and third-party vendor scope/liability.
- Report section 3.2.3.4 suggests REs give customers means to challenge and seek clarification on AI decisions — [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)
- [DRAFT] RBI released Draft Guidance on Regulatory Principles for Model Risk Management, 2026 on 24 Jun 2026, covering all models including AI/ML used by REs (commercial banks, co-op banks, SFBs, PBs, NBFCs, ARCs, CICs, AIFIs); requires board-approved Model Risk Management Framework covering in-house, third-party and hybrid models; comments due 24 Jul 2026 via Connect 2 Regulate — [RBI Connect2Regulate](https://www.rbi.org.in/Scripts/Bs_Connect2RegulateDetails.aspx?prid=487); [C4S](https://c4scourses.in/?p=32082)
- The MRM draft follows the 5 Aug 2024 draft "Regulatory Principles for Management of Model Risks in Credit" — [RBI Connect2Regulate](https://www.rbi.org.in/Scripts/Bs_Connect2RegulateDetails.aspx?prid=487)
- Secondary commentary: draft emphasises accountability for externally supplied models (understand, validate, monitor even if not built in-house) — [cybersigmacs](https://cybersigmacs.com/blog/rbi-ai-model-risk-management-2026/) [UNVERIFIED vs draft text]
- As of mid-July 2026 final MRM guidance had not been issued — [cybersigmacs](https://cybersigmacs.com/blog/rbi-ai-guidelines-model-risk-management-2026/); no final version found as of Oct 2026 searches.

### Inferences
- **Which FREE-AI items apply to AI-drafted complaint responses and AI classification:**
  - AI classification of complaints (category, severity, fraud/regulatory flags, TAT routing) and AI-drafted replies are customer-impacting → likely "medium risk" under Rec 16/20 → human-in-the-loop approval before sending, semi-annual red teaming (prompt injection via complaint text, hallucinated regulation citations, biased tone), drift monitoring on classification accuracy.
  - Rec 23 → register each Bedrock model/version, prompt template version, embedding model and vector index as inventory items; refresh at least half-yearly.
  - Rec 18 + Sutra 2 → if customers receive AI-generated text or interact with a bot, disclose AI involvement and offer human escalation; final replies should be attributable to an accountable human officer.
  - Rec 22 → log "AI incidents" (wrong classification causing missed TAT/escalation, hallucinated policy, PII leak in output) in a dedicated register, separate from cyber incidents.
  - Rec 24/Sutra 6 → store input, retrieved passages (RAG citations), model output, human edits and final decision per complaint — this gives explainability and an audit trail.
  - Rec 8 → the bank is liable for AI-caused outcomes; vendor (AWS/model provider) cannot be blamed — contract clauses per Annexures IV–V.
  - Rec 17 → the engine itself must go through the bank's product/IT approval process before production.
- Under a future MRM framework, LLM classifiers and scoring would likely count as "models" requiring validation and independent review; designing evaluation datasets and validation reports now reduces later friction.

### Gaps
- Whether RBI has issued any binding AI direction (beyond the draft MRM guidance) by Oct 2026 — none found.
- Paras 4.4.54–55 (exact wording on AI disclosure/human escalation) not quoted verbatim.
- No definitive definition of "medium/high risk" AI use found in retrieved text.

## Q4. DPDP Act 2023 & DPDP Rules 2025 – phasing, consent, purpose limitation, retention, breach notification, SDF, cross-border, RBI data localisation

### Takeaway
DPDP Rules 2025 were notified 13/14 Nov 2025 with an 18-month phase-in: most substantive obligations (notice/consent, security safeguards incl. 1-year log retention, breach notification with 72-hour detailed report, SDF DPIA/audit/algorithmic due diligence) bite from ~13 May 2027, so in Oct 2026 they are [FUTURE-DATED] but must be designed for now. Cross-border transfer is permitted by default (negative list, none notified as of mid-2026), but the RBI 2018 payment-data localisation direction remains the binding constraint for payment data sent to cloud LLMs.

### Cited Findings
- MeitY notified DPDP Rules on 13 Nov 2025 (gazette sometimes cited 14 Nov) — [Hogan Lovells](https://www.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-); [AZB](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/); [Storyboard18](https://www.storyboard18.com/amp/digital/breaking-govt-notifies-final-dpdp-rules-sets-staggered-rollout-with-key-obligations-for-data-fiduciaries-84201.htm)
- Phasing: Rules 1, 2 and 17–21 (Board) immediate; Rule 4 (consent manager registration) after 1 year (~13 Nov 2026); remaining rules incl. Rules 3, 5–16, 22–23 after 18 months (~13/14 May 2027) — [Storyboard18](https://www.storyboard18.com/amp/digital/breaking-govt-notifies-final-dpdp-rules-sets-staggered-rollout-with-key-obligations-for-data-fiduciaries-84201.htm); [TCSA](https://www.tcsa.in/resources/dpdp-rules-2025-implementation-roadmap); [Protiviti](https://www.protiviti.com/sites/default/files/2025-11/flash_compliance_update_dpdp_rules-2025.pdf)
- Conflict: Hogan Lovells' table places "intimation of breaches" in a 13 Nov 2026 bucket, conflicting with others who place Rule 7 at 18 months; Moore Singhi suggests immediate effect (outlier) — [Hogan Lovells](https://www.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-); [Moore Singhi](https://www.moore-singhi.singhico.com/pdf/Digital_Personal_Data_Protection_Rules.pdf) [UNVERIFIED – check gazette]
- Rule 7 breach: intimation to Board and affected Data Principals without delay; detailed report to Board within 72 hours of becoming aware (extendable on written request); Konfirmity reads the 72h clock as applying only to the detailed Board report — [KS&K](https://ksandk.com/md/data-protection-and-data-privacy/dpdp-data-breach-notification-timeline/); [Konfirmity](https://www.konfirmity.com/blog/dpdp-breach-notification)
- Penalties: up to ₹200 crore for failing to notify a breach; up to ₹250 crore for failing reasonable security safeguards — [KS&K](https://ksandk.com/md/data-protection-and-data-privacy/dpdp-data-breach-notification-timeline/)
- Rule 6 security safeguards: retain logs and related processing records for at least 1 year (unless longer required by law) for detection/investigation/remediation — [iPleaders](https://blog.ipleaders.in/dpdp-rules-2025-operational-compliance-guide/); [India Briefing](https://www.india-briefing.com/news/dpdp-rules-2025-india-data-protection-law-compliance-40769.html)
- Rule 13 Significant Data Fiduciaries: annual DPIA and independent data audit, report to Board; algorithmic due diligence – verify technical measures/algorithmic software do not pose risk to Data Principal rights; data localisation if notified; applies upon SDF designation — [Lawrbit](https://www.lawrbit.com/article/digital-personal-data-protection-rules-2025); [Scrut](https://www.scrut.io/post/dpdp-rules); [Seclore](https://www.seclore.com/fundamentals/dpdp-rules-2025-compliance-guide/)
- Section 16 cross-border: default-allow; Central Government may restrict transfer to notified countries; no restricted list notified as of mid-2026 (sources differ on wording) — [Treelife](https://treelife.in/compliance/data-localisation-in-india/); [TCSA](https://www.tcsa.in/frameworks/dpdp/cross-border-transfer)
- Sectoral rules (RBI/SEBI/IRDAI) continue to apply on top of DPDP and are typically stricter — [Treelife](https://treelife.in/compliance/data-localisation-in-india/)
- RBI payment data storage direction (DPSS.CO.OD No.2785/06.08.005/2017-18, 6 Apr 2018): entire payment system data stored only in India (covers banks offering digital payments); processing abroad allowed only if data deleted abroad within one business day or 24 hours, whichever earlier, with full copy in India; penalties under s.26 PSS Act — [Treelife](https://treelife.in/compliance/data-localisation-in-india/); [Opsio](https://opsiocloud.com/knowledge-base/data-localization-in-india-rbi/)
- FREE-AI Rec 15 explicitly ties AI data lifecycle (retention, deletion) to DPDP — [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)

### Inferences
- **Bedrock region choice:** Complaint narratives about failed/unauthorised UPI/card transactions contain payment system data (transaction IDs, amounts, VPA, card fragments). Using an India region (AWS Mumbai ap-south-1 / Hyderabad ap-south-2) for Bedrock inference, embeddings and the vector store is the safe design; cross-region inference profiles that route outside India would need the 24-hour deletion analysis and are best disabled. (Engineering inference; confirm model availability per region.)
- **Purpose limitation/minimisation:** Complaint data collected for grievance redress can be processed for redress and regulatory compliance (legitimate-use grounds under the Act), but reuse for model training/fine-tuning or marketing analytics needs separate analysis; pseudonymise PII (name, account no., Aadhaar, PAN, phone) before prompts and embeddings; keep re-identification map in bank-controlled store.
- **Erasure vs retention conflict:** DPDP erasure requests do not override statutory retention (PMLA/RBI); vector embeddings derived from complaints must be deletable/re-indexable when the retention period expires — design tombstoning per complaint ID across vector DB, logs and LLM caches.
- **Breach runbook:** a PII leak via LLM output or vector store is simultaneously a DPDP breach (Board + principals, 72h detailed report from ~May 2027), a cyber incident (RBI 6h via DAKSH; CERT-In 6h), and a FREE-AI AI incident — engine should support one incident record with three clocks.
- Large banks are plausible SDF designees → annual DPIA and "algorithmic due diligence" would directly cover the LLM classifier.

### Gaps
- Gazette text of Rules 6, 7, 13 not read directly; Rule 7 effective date conflict unresolved.
- No SDF designation notification found for banks as of Oct 2026.
- Whether RBI has issued any clarification on LLM/cloud processing of payment data under the 2018 direction – not found.

## Q5. IT Governance, IT Outsourcing, Cyber incident reporting, audit logs, cloud (2023 MDs → 31 Jul 2026 Technology Directions)

### Takeaway
The Nov 2023 MD on IT Governance, Risk, Controls and Assurance (effective 1 Apr 2024) has been followed by the 31 Jul 2026 "Cybersecurity, Technology: Risk, Resilience and Assurance Framework Directions" and "Digital Payment Security Controls Directions" (effective immediately), which require cyber-incident reporting to RBI within 6 hours via DAKSH plus notification to CERT-In (itself a 6-hour obligation since 2022). Hosting an LLM engine is an IT-outsourcing/third-party arrangement requiring board-level governance, VA/PT, DR drills and contractual controls.

### Cited Findings
- MD on IT Governance, Risk, Controls and Assurance Practices issued Nov 2023, effective 1 Apr 2024, applicable to banks and NBFCs — [Lexplosion](https://lexplosion.in/?p=136132); [Open Security Architecture](https://opensecurityarchitecture.org/frameworks/rbi-csf)
- 2016 Cyber Security Framework required incident reporting to RBI within 2–6 hours; audit-log controls in Annex 1.16 (maintenance, monitoring & analysis of audit logs) and 1.17 (audit log settings) — [Open Security Architecture](https://opensecurityarchitecture.org/frameworks/rbi-csf/controls)
- [IN FORCE] On 31 Jul 2026 RBI issued the Cybersecurity, Technology: Risk, Resilience and Assurance Framework Directions and the Digital Payment Security Controls Directions, effective immediately, forming an entity-wise architecture for technology governance, cybersecurity, operational resilience and payment security — [KPMG](https://kpmg.com/in/en/insights/2026/09/rbis-technology-focused-master-directions-issued-on-31-july-2026.html)
- Cyber incidents must be reported within 6 hours of detection via RBI DAKSH, with proactive notification to CERT-In — [KPMG](https://kpmg.com/in/en/insights/2026/09/rbis-technology-focused-master-directions-issued-on-31-july-2026.html)
- VA at least every 6 months and PT at least every 12 months for critical systems and DMZ customer-facing systems; DR drills for critical systems at least half-yearly, with major issues fixed and re-tested before next cycle — [KPMG](https://kpmg.com/in/en/insights/2026/09/rbis-technology-focused-master-directions-issued-on-31-july-2026.html)
- Cyber directions contain a third-party arrangements section for arrangements outside the scope of the RBI "managing risks in outsourcing" directions; governance responsibility extends to board, senior management, risk, compliance — [KPMG](https://kpmg.com/in/en/insights/2026/09/rbis-technology-focused-master-directions-issued-on-31-july-2026.html)
- Digital Payment Security Controls apply to any digital payment product incl. non-financial transactions (balance enquiry, PIN set, mobile banking registration, OTP); board-approved policy for digital payment products required — [KPMG](https://kpmg.com/in/en/insights/2026/09/rbis-technology-focused-master-directions-issued-on-31-july-2026.html)
- CERT-In Directions of 28 Apr 2022: specified incident types reported to CERT-In within 6 hours — [cybersigmacs / secondary](https://cybersigmacs.com/blog/rbi-cyber-security-framework-guide/) (well-established; also maintain ICT logs 180 days in India – see Gaps)
- FREE-AI notes AI-specific cyber risks (Rec 19) and suggests AI-specific outsourcing clauses (Annex IV) — [RBI report](https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?UrlPage=&ID=1306)

### Inferences
- The complaint engine (and Bedrock as a sub-processor) is a material third-party/outsourced IT service: needs board-approved outsourcing risk assessment, right-to-audit and RBI-access clauses, data location commitments, exit/BCP plan, and concentration-risk assessment for AWS.
- Customer-facing components (portal, chatbot) fall under DMZ VA/PT cadence (6/12 months); if the engine is deemed critical (it drives regulatory TATs), half-yearly DR drills apply — align with FREE-AI Rec 21 AI-BCP (fallback to rules-based classification/manual queue if Bedrock unavailable).
- Logs: keep immutable audit logs (prompt, retrieved context IDs, output, reviewer, timestamps) ≥ 180 days in India (CERT-In) and ≥ 1 year (DPDP Rule 6, from 2027); in practice align with complaint-record retention (Q6), whichever longest.
- Complaints reporting phishing, SIM-swap, app compromise may themselves be cyber incidents — the engine should flag candidates for the CISO's 6-hour DAKSH assessment.

### Gaps
- Which 2023 instruments (IT Governance MD, Outsourcing of IT Services MD Apr 2023, CSF 2016) were formally repealed by the 31 Jul 2026 directions not confirmed (KPMG page doesn't list them).
- Specific log-retention periods under RBI directions not found. CERT-In 180-day log retention requirement is from prior knowledge, not re-verified this session.
- RBI's position on cloud (community/public cloud frameworks) in the 2026 directions not retrieved.

## Q6. Record retention for complaint records and evidence

### Takeaway
PMLA s.12 (as amended 2012) and the KYC Directions require transaction records for at least 5 years from the transaction and identification/KYC records for at least 5 years after the relationship ends/account closes; fraud cases, litigation and DPDP log rules can extend this. No RBI-specified complaint-record-specific retention period was found in this research.

### Cited Findings
- Post-2012 PMLA amendment, records to be maintained and preserved for at least five years (earlier ten years under 2009 amendment) — [RBI circular](https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx?Id=8959); [RBI PDF](https://website.rbi.org.in/documents/87730/39710850/AP149C250614F.pdf)
- Rule 3 PML Rules transaction records: cash transactions > ₹10 lakh, integrally connected cash series, counterfeit currency, suspicious transactions; must capture nature, amount, currency, date, parties to permit reconstruction — [RBI circular](https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx?Id=8959)
- KYC identification/address records: at least 5 years after business relationship ends; some bank policies: 5 years from cessation of relationship or account closure, whichever later — [Utkarsh SFB Record Management Policy](https://www.utkarsh.bank.in/uploads/policy/Record_Management_Policy.pdf); [Protium policy](https://protium.co.in/wp-content/uploads/2026/05/Preservation-of-Records-Policy.pdf)
- For loan customers the clock may start after loan closure (vendor commentary on V-CIP records) — [Gridlines](https://gridlines.io/blogs/video-kyc-audit-trail/) [commentary]
- DPDP Rule 6: processing logs minimum 1 year (from ~May 2027) — [iPleaders](https://blog.ipleaders.in/dpdp-rules-2025-operational-compliance-guide/)
- Bank record-retention policies (e.g., Equitas, slice) set category-wise periods under board policy — [Equitas](https://ir.equitasbank.com/wp-content/uploads/2022/03/ESFB_Record-Retention-and-Archival-Policy.pdf); [slice](https://slice.bank.in/documents/Policies/record-retention-policy.pdf)

### Inferences
- Default retention rule for the engine: complaint record + evidence + AI audit trail = max(5 years from complaint closure [aligning with PMLA where complaint concerns a transaction], 5 years after account closure where linked to KYC/fraud, until fraud case/litigation/Ombudsman proceedings closed + bank-policy buffer). Encode as a policy table, not constants.
- Legal-hold flag must suspend DPDP erasure and vector-index deletion for complaints linked to fraud cases, LEA requests or CFCFRMS tickets.
- Embeddings, LLM prompts/outputs and reviewer edits are "records" of the decision; retention and deletion must cascade consistently.

### Gaps
- No RBI direction specifying a retention period for customer complaint records themselves was found (bank board policies govern; Banking Regulation Act preservation rules not researched).
- Current paragraph numbering of record-keeping chapter in 2025 Commercial Banks KYC Directions not verified.
- Retention for FMR/fraud case files under 2026 FRM Directions not found.
