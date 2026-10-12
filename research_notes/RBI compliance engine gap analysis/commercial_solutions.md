# Commercial Solutions for Banking Complaint Management and Regulatory Compliance (India + Global)

Research date: 2026-10-12. About 16 search/fetch calls. Most vendor material is marketing; verified facts (regulator documents, bank policy documents) are labelled. Where a claim comes only from a vendor or a vendor-quoted article, it is marked **[vendor claim]**.

---

## Q1. Indian complaint / grievance platforms used by banks — which advertise RBI IOS / Internal Ombudsman (IO) compliance?

### Takeaway
Indian banks run complaint handling mostly on general-purpose CRM / case-management or BPM platforms (CRMNext/Businessnext, Newgen, Salesforce, Kapture and similar) set up for bank-specific category/TAT matrices. The one bank-confirmed fact (HDFC Bank's policy naming CRMNext) shows the standard features: categorisation, TAT per sub-category, auto-escalation, reference numbers. I found **no vendor source that explicitly advertises RBI Internal Ombudsman Directions 2026 / RB-IOS 2026 compliance workflows**, such as three-status classification, auto-transfer to IO, IO/RBIO case handling or compensation calculation. RBI's January 2026 IO Directions now require a "fully automated" CMS with auto-escalation, so there is a clear, recently created requirement that vendors do not yet visibly market against.

### Cited Findings
**CRMNext (now Businessnext)**
- HDFC Bank's Grievance Redressal Policy (a primary bank document) says complaints are logged in CRMNext, which records and categorises grievances by type, keeps TAT for each category/sub-category, has "an auto escalation mechanism for cases not resolved within defined TAT", and issues a reference number as acknowledgement. Credit-card grievances are logged in Vision Plus instead. — [HDFC Bank Grievance Redressal Policy](https://v1.hdfcbank.com/assets/pdf/grievance_redressal_policy.pdf)
- Kotak Mahindra Bank went live with CRMNext. Coverage focuses on sales and customer journeys, not specifically grievances. — [IBS Intelligence](https://ibsintelligence.com/ibsi-news/kotak-mahindra-bank-goes-live-with-crmnext-in-india)
- CRMNext won the Asian Banker CRM Technology Implementation Award in 2014 (first Indian product company to do so). Axis is named as a client in award coverage. — [BIS Infotech](https://www.bisinfotech.com/crmnext-first-indian-product-company-to-bag-asian-banker-crm-technology-implementation-award-2014/); customer list at [businessnext.com/customers](https://www.businessnext.com/customers/) (not fetched)
- Kotak publishes per-complaint-type TATs in working days. Customers get an SMS/email with the exact resolution TAT once a complaint is logged, which implies a category-to-TAT matrix inside the CRM. — [Kotak TAT page](https://www.kotak.com/en/customer-service/grievance-redressal/personal-banking/turnaround-time.html)

**Newgen (NewgenONE)**
- Newgen markets "financial service request management", described as end-to-end case management from first contact to resolution. — [Newgen retail banking page](https://newgensoft.com/sg/solutions/industries/financial-institutions/retail-banking/financial-service-request-management)
- Its case studies: a "Fortune 500 global banking leader" service-request upgrade, and BankVic (Australia) complaint management with SLA management and audit visibility. Neither is an Indian bank, and neither mentions RBI IO. — [Newgen global bank case study](https://landing.newgensoft.com/hubfs/_2020%20Website%20files/Case%20studies/A%20Fortune%20500%20Global%20Banking%20Leader%20Upgrades%20its%20Customer%20Service%20Request%20Management%20with%20Newgen%20%20(1).pdf); [BankVic case study](https://newgensoft.com/au/resources/bankvic-raises-the-bar-in-complaint-management-with-newgenone-platform)

**Kapture CX**
- Banking pitch is about "inefficient complaint and feedback management", with omnichannel intake and SLA-driven ticket routing. No RBI-specific claims. **[vendor claim]** — [Kapture banking deck](https://www.slideshare.net/slideshow/kapturecrm-for-banking/115598058)

**Salesforce Financial Services Cloud / Agentforce** (used in India; no Indian bank complaint deployment found)
- The Spring '26 Agentforce for Financial Services deck lists a "Complaint Management Agent" that searches case history, identifies systemic issues and drafts "compliant responses". **[vendor claim]** — [Salesforce Agentforce FS deck](https://www.salesforce.com/en-us/wp-content/uploads/sites/4/Industry%20-%20Financial%20Services/EXTERNAL-260-Releasely-Slide-Deck-Agentforce-Financial-Services-.pdf)
- Salesforce's public-sector complaint subagent uses data objects named Complaint, Regulatory Code and Regulatory Code Violation. Its example scenario is fictional. — [Salesforce public engagement](https://www.salesforce.com/agentforce/use-cases/government/public-engagement/)
- Deloitte built a Salesforce "Complaints accelerator" (2023) with omnichannel intake and RCA dashboards. — [Deloitte FSConnect slide](https://www.deloitte.com/content/dam/assets-shared/docs/industries/financial-services/2023/gx-FSConnect-slide-6.pdf)

**Regulatory requirement that these products must now meet (verified via law-firm/press summaries of RBI Directions)**
- In January 2026 RBI issued Internal Ombudsman Directions (separate versions for commercial banks, SFBs, NBFCs, CICs), replacing the 2023 Master Direction. Banks and eligible NBFCs must run a **fully automated complaint management system** that gives the IO and Deputy IO access. Unresolved grievances are **auto-escalated** to the IO once classified as "partially resolved" or "wholly rejected", using three status categories (fully resolved / partially resolved / wholly rejected). — [Business Standard, 14 Jan 2026](https://www.business-standard.com/finance/news/rbi-mandates-auto-escalation-of-unresolved-complaints-to-internal-ombudsman-126011401228_1.html); [Vinod Kothari note](https://vinodkothari.com/wp-content/uploads/2026/01/Internal-Ombudsman_Final.pdf); [TaxGuru](https://taxguru.in/?p=1018375)
- IO timelines for banks: at least 10 days for IO review where RBI/NPCI/card-network rules prescribe a resolution timeline, 20 days otherwise. A final decision must reach the complainant within 30 days. NBFCs: a complaint may not be closed by the same branch/unit (clause 14(4)). Certain clauses (number of IOs, three-category classification) had a 30 June 2026 deadline. Secondary summaries differ on exact timelines, so check the RBI text. — [same sources](https://vinodkothari.com/wp-content/uploads/2026/01/Internal-Ombudsman_Final.pdf); [adda247 summary](https://currentaffairs.adda247.com/rbi-mandates-auto-transfer-of-unresolved-complaints-to-internal-ombudsman/)
- The revised Reserve Bank Integrated Ombudsman Scheme 2026 took effect on 1 July 2026 (replacing RB-IOS 2021). Escalation is allowed if the RE does not reply within 30 days. Compensation for consequential loss is up to Rs 30 lakh, with no cap on the disputed amount. A CRPC handles receipt. — [BofA India summary of IOS 2026](https://business.bofa.com/content/dam/flagship/in/en/regulatory-legal-and-policy-documents/Salient-features-and-Integrated-Ombudsman-Scheme-2026.pdf); [Vision IAS](https://visionias.in/current-affairs/upsc-daily-news-summary/article/2026-01-17/the-hindu/economy/rbi-issues-revised-integrated-ombudsman-scheme-to-hear-complaints-against-banks-nbfcs)
- KPMG India (Aug 2026) lists the operational pain points in bank grievance processes: duplicate complaints, inaccurate classification, TAT-monitoring problems, staff training gaps, and growth of digital-channel complaints. The lifecycle stages are receipt, consolidation, classification, routing, resolution and reporting. No vendors are named. — [KPMG India](https://kpmg.com/in/en/insights/2026/08/from-dissent-to-delight-managing-information-asymmetry-in-customer-grievance-process.html)

### Inferences
- The established Indian pattern is a CRM case object, a category/sub-category taxonomy, a TAT matrix, a time-based escalation hierarchy, and a reference number. These are generic SLA engines. The KPMG pain points (duplicates, misclassification, TAT monitoring) suggest the incumbents do not solve classification quality or de-duplication well.
- The 2026 IO Directions add **state-based** escalation (on resolution outcome, not only elapsed time), segregation-of-duties rules (no same-unit closure for NBFCs) and IO-specific review windows. Incumbent CRMs can be configured for these, but none were found marketing them as packaged features. This is a market gap.
- No vendor was found offering automated computation of RB-IOS compensation or of TAT-linked compensation under RBI's harmonised failed-transaction TAT framework.

### Gaps
- No primary sources found for Nucleus Software, Intellect Design, Kiya.ai, Finacle CRM, TCS BaNCS, Microsoft Dynamics, Freshworks, Zoho, Ameyo/Exotel, Gnani.ai, Yellow.ai or Senseforth complaint modules or for which Indian banks use them for grievances. (Search returned nothing bank- or RBI-specific for these.)
- No public architecture or tech-stack disclosure for CRMNext's grievance module.
- No independent evaluations (Gartner/Forrester) specific to Indian bank complaint management were found.

---

## Q2. RegTech for regulatory compliance / change management (Indian and global)

### Takeaway
The RegTech market has two separate halves. (a) **Compliance-obligation tracking** tools are driven in India by RBI's January 2024 circular mandating tech-based compliance monitoring; examples are TeamLease RegTech RegTrack and Jocata. (b) **Global regulatory-intelligence / change-management** tools (CUBE, Corlytics, Ascent) parse regulatory text into obligations and map them to controls. Neither half connects to the complaint-handling floor. Obligation registers stop at policy/control mapping and do not execute case-level rules such as TATs, escalation or compensation.

### Cited Findings
**India: the driver**
- RBI circular RBI/2023-24/117 (31 Jan 2024) requires REs (SCBs, SFBs, payment banks, UCBs Tier III/IV, upper/middle-layer NBFCs, HFCs, CICs) to adopt comprehensive, enterprise-wide, workflow-based compliance monitoring tools. These must identify, assess, monitor and manage compliance requirements, escalate non-compliance, record competent-authority approval for deviations, and provide a unified senior-management dashboard. A reported dashboard deadline is 30 June 2024. — [ClearTax summary](https://cleartax.in/s/internal-compliance-monitoring-rbi-circular-117); [TeamLease RegTech blog](https://teamleaseregtech.com/blogs/102/compliance-management-systems-made-mandatory-by-rbi-for-banks); [AMLegals](https://amlegals.com/regtech-in-india-revolutionizing-compliance-in-a-digital-economy/)

**TeamLease RegTech — RegTrack for Financial Institutions**
- Has a deviation workflow built for the RBI circular (request deviation, approval by CCO/director). Groups requirements into Policy, Procedure, Disclosures, Customer Communication, Reporting and Automation. Claims 3,300+ entities, 25M+ compliance instances, and a legal database of 1,536 Acts / 69,233 compliances. **[vendor claim]** — [RegTrack product page](https://teamleaseregtech.com/product-services/regtrack-financial-institutions/)

**Jocata — One Case Manager**
- Launched against the RBI single-dashboard circular. It consolidates AML, CFT, fraud and sanctions alerts on one platform. This is financial-crime case management, not customer complaints. — [CXOToday](https://cxotoday.com/press-release/jocata-launches-one-case-manager-enabling-financial-institutions-comply-by-rbis-single-dashboard-circular/)

**Nelito Systems**
- Banking software vendor (runner-up in RegTech at the Global FinTech Innovation Awards). Its blog argues RBI CIMS reporting needs automated data pipelines. No circular-tracking product page found. — [Nelito blog on RBI compliance automation](https://www.nelito.com/blog/how-can-banks-automate-rbi-compliance-and-regulatory-reporting.html); [IBS Intelligence](https://ibsintelligence.com/?p=523252)

**CUBE (RegPlatform, RegBrain)**
- RegPlatform is powered by a purpose-built regulatory AI engine (RegBrain). It reportedly monitors about 10,000 issuing bodies across 750 jurisdictions, turns regulatory content into "structured, contextualised intelligence", and aligns external rules with internal controls and policies. **[vendor claim, via Microsoft partner blog]** — [Microsoft UK industry blog](https://www.microsoft.com/en-gb/industry/blog/?p=71106); [CB Insights profile](https://www.cbinsights.com/company/cube-global)
- In Feb 2026 CUBE acquired 4CRisk.ai, which maps corporate policies and procedures to obligations, controls and risks. — [same Microsoft blog / company profiles](https://www.microsoft.com/en-gb/industry/blog/?p=71106)

**Corlytics**
- Hybrid AI plus human-validation design across horizon scanning, regulatory change, obligations analysis, and policy/control mapping. Overlapping obligations are consolidated by ML. LLMs suggest policy/control enhancements in gap analysis. Users are prompted to update the traceability matrix when rules change. — [fintech.global: explainable AI](https://fintech.global/2025/11/11/is-explainable-ai-the-missing-link-in-regulatory-compliance/); [fintech.global AML forum](https://fintech.global/aml-tech-forum-usa/2025/12/11/can-data-make-sense-of-an-ever-changing-rulebook/); [Corlytics regulatory monitoring](https://www.corlytics.com/solutions/regulatory-monitoring/)
- Chartis named it a Category Leader in the 2025 RiskTech Quadrant for Regulatory Intelligence Solutions. It claims to be the first RegTech with ISO 42001 certification. — [A-Team Insight](https://a-teaminsight.com/blog/managing-cognitive-dissonance-in-regulatory-compliance-with-corlytics/?brand=ati); [Corlytics news](https://www.corlytics.com/?p=15542)

**Ascent RegTech (AscentFocus)**
- AI pipelines extract each obligation as an individual, versioned data object into a regulatory library of 400,000+ global obligations. Features include applicability assessment, "Rule Compare" redlines, and GRC integration to map obligations to policies/controls. Claims patented technology and to be the only solution extracting every obligation as an individual object. **[vendor claim]** — [fintech.global RegTech100 profile](https://fintech.global/2025/10/13/how-ascentai-is-powering-the-next-generation-of-regulatory-compliance-automation/); [Ascent: obligations-based approach](https://ascentregtech.com/?p=313582)

**Pega (global complaints / disputes)**
- Pega's complaints brief (2021, insurance-framed) describes a flow of intake, investigation/assignment, resolution, correspondence and reporting, with every action captured in an audit trail for regulatory tracking. It cites USAA. — [Pega complaints executive brief](https://www.pega.com/system/files/resources/pdf/complaints-executive-brief.pdf)
- Pega Smart Dispute has packaged consumer-protection SLAs for Reg E/Reg Z (US), C-86 (Canada) and Section 75 (UK). This is a concrete example of **regulation-specific SLA packs**. — [Pega Smart Dispute](https://pega.com/industries/financial-services/smart-dispute)

### Inferences
- Pega Smart Dispute's per-regulation SLA packs are the closest global analogue to what an "RBI IO/RB-IOS pack" would be. No equivalent RBI pack was found from any vendor.
- Indian compliance tools (RegTrack) model obligations as **periodic tasks with owners and deviations**, while global tools model them as **parsed text objects mapped to controls**. Neither makes obligations executable rules applied to individual complaints.

### Gaps
- No usable sources found in this pass for Wolters Kluwer OneSumX, MetricStream, IBM OpenPages, SAI360, NICE Actimize, Appian, ServiceNow complaint management, Verint, Qualtrics/Clarabridge, Theta Lake, Signzy, IDfy, Perfios, Clari5, FinShield, Fintellix/Aptivaa, Corpository or "Comply360". (Comply360 returned no results at all.)
- No Indian bank was confirmed as a customer of CUBE, Corlytics or Ascent.
- RegTrack bank-customer names were not found.

---

## Q3. How vendors use LLMs/AI in production for compliance; accuracy and human-in-the-loop

### Takeaway
LLM use in production is concentrated in (1) **regulatory text to obligation extraction and mapping** (Corlytics, Ascent, CUBE) and (2) **agent-assist summarisation and drafting** in case handling (Pega GenAI, Salesforce Agentforce). All vendors frame these as human-in-the-loop. Reported accuracy figures are vendor self-reports with no independent audit. No vendor publishes complaint-classification accuracy for banking.

### Cited Findings
- Corlytics targets **99%+ accuracy** for its models against a cited **~98% human benchmark**, validated by backtesting and SME review. These are executive-quoted figures with ambiguous wording, and no independent audit was found. — [fintech.global](https://fintech.global/aml-tech-forum-usa/2025/12/11/can-data-make-sense-of-an-ever-changing-rulebook/)
- Corlytics' rationale for human-in-the-loop: subtle phrasing changes can reshape obligations, so analysts validate outputs and are given "the full context of compliance determinations". — [fintech.global: explainable AI](https://fintech.global/2025/11/11/is-explainable-ai-the-missing-link-in-regulatory-compliance/)
- Simmons & Simmons (a law firm, not a vendor) runs a hybrid generative-AI regulatory analysis workflow in which **all LLM outputs are reviewed by lawyers**. — [Simmons & Simmons case study](https://www.simmons-simmons.com/en/publications/cmpfm506100biut6kwnu801wd/case-study-hybrid-ai-regulatory-analysis)
- Pega GenAI in Smart Dispute: GenAI Coach (employee guidance), Knowledge Buddy (RAG over dispute-procedure knowledge), and Voice AI/GenAI summaries of calls and case histories. **[vendor claim]** — [Agile Brand Guide on Pega Smart Dispute](https://agilebrandguide.com/gen-ai-and-automation-enhancements-help-banks-accelerate-payment-disputes-and-claims-with-new-edition-of-pega-smart-dispute/); [Pega agentic automation PDF](https://pega.com/system/files/resources/pdf/pega-pega-smart-dispute-agentic-automation.pdf)
- Salesforce Agentforce Complaint Management Agent drafts "compliant responses" and spots systemic issues, with "guardrails". No accuracy figures. **[vendor claim]** — [Salesforce deck](https://www.salesforce.com/en-us/wp-content/uploads/sites/4/Industry%20-%20Financial%20Services/EXTERNAL-260-Releasely-Slide-Deck-Agentforce-Financial-Services-.pdf)
- A Grazitti case study claims "3x faster complaint insights" with an Agentforce agent. This is a partner claim. — [Grazitti](https://www.grazitti.com/resource/case-study/3x-faster-complaint-insights-with-agentforce-agent/)

### Inferences
- Vendor LLM usage is **advisory** (summarise, draft, suggest, extract). Decisions with regulatory consequence (escalate, compensate, close) are left to humans or to static configured rules. None of the sources describe a **deterministic rule layer whose every decision is traceable back to a specific regulatory clause** with an LLM limited to interpretation. That combination is an open design space.
- "Explainability" in vendor marketing means showing the source text or context to a reviewer, not producing a decision trace (rule ID, clause, input facts, output).

### Gaps
- No published accuracy for complaint classification, response QA or obligation-to-control mapping from CUBE, Ascent, Pega or Salesforce.
- No production LLM complaint-handling deployments at Indian banks were found documented.

---

## Q4. RBI's own systems (CMS, CRPC, DAKSH, AI initiatives) and bank data exchange

### Takeaway
RBI's CMS (launched June 2019) is a web portal. REs participate through Principal Nodal Officer / Nodal Officer logins and report generation. **No public API for bank-side system-to-system integration was found.** DAKSH (Oct 2022) is RBI's supervisory compliance-tracking workflow. RBI plans to embed AI in CMS in phases (Phase I chatbot, Phase II complaint processing), and RBIH has proposed an Automated Grievance Redressal system with intent detection and classification. These are plans, not confirmed deployments.

### Cited Findings
- CMS gives the public a single window for complaints against any RE. Complaints are routed to the relevant Ombudsman office / RBI Regional Office. REs get access via Principal Nodal Officers and Nodal Officers, with reports for monitoring and **root-cause analysis**. — [RBI press release (2019)](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=47383); [SCC Online](https://www.scconline.com/blog/post/2019/06/26/grievance-redressal-process-complaint-management-system-launched-by-reserve-bank-of-india/)
- The RBI Governor (2019) urged banks to use CMS data to reduce TAT and for RCA. — [RBI speech](https://www.rbi.org.in/Scripts/BS_SpeechesView.aspx?Id=1077)
- RB-IOS runs 24 ORBIOs plus the CRPC. FY2024-25 saw **13.34 lakh complaints, up 13.55% YoY**. Average TAT for unauthorised digital-payment complaints rose from **36.3 days (FY23) to 68.3 days (FY25)**. — [Tribune India (Rajya Sabha reply)](https://www.tribuneindia.com/news/business/ai-enabled-tools-to-streamline-complaint-handling-at-rbi-mos-finance); [Outlook Money](https://www.outlookmoney.com/banking/rbi-ombudsman-disposal-falls-to-93-in-fy25-when-to-approach-for-complaint-redressal)
- RBI's annual report says it plans to embed AI in CMS to ease lodging and ensure "greater consistency in the decision-making process". The phased upgrade is a Phase I conversational chatbot, then Phase II advanced processing. — [Regulation Asia](https://www.regulationasia.com/articles/rbi-to-roll-out-ai-tools-to-speed-up-complaint-handling); [Tribune India](https://www.tribuneindia.com/news/business/ai-enabled-tools-to-streamline-complaint-handling-at-rbi-mos-finance)
- Governor Malhotra (March 2025) said AI could categorise complaints by urgency, complexity or subject, and that AI should complement human judgment, not replace it. — [Moneylife](https://www.moneylife.in/article/rbi-governor-pushes-for-ai-to-resolve-bank-customer-complaints/76663.html); [Central Banking](https://www.centralbanking.com/central-banks/governance/7972515/rbi-hails-ais-potential-in-addressing-customer-grievances)
- RBIH proposed an Automated Grievance Redressal (AGR) system: intent identification, complaint-category classification, translation/transliteration, multimodal I/O. This is a proposal. — [RBIH AGR](https://rbihub.in/?p=17770)
- DAKSH (launched 6 Oct 2022) is a web-based end-to-end workflow application for RBI to monitor REs' compliance requirements, communications, inspection planning, cyber-incident reporting and MIS. — [RBI press release](https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=54503); [CCAF](https://lab.ccaf.io/news/the-reserve-bank-of-india-has-launched-a-daksh)
- MuleHunter.AI is an RBIH mule-account detection tool piloted in two PSBs. It is **not** a complaint-classification tool. — [Business Standard](https://www.business-standard.com/amp/finance/news/what-is-mulehunter-ai-rbi-s-latest-tool-against-financial-fraud-explained-124120600865_1.html)
- A Nelito blog claims REs must integrate with **CIMS** (RBI's Centralised Information Management System) through automated pipelines. This is a vendor source and concerns regulatory returns, not complaints. — [Nelito](https://www.nelito.com/blog/how-can-banks-automate-rbi-compliance-and-regulatory-reporting.html)

### Inferences
- Bank-to-RBI complaint data exchange appears to be **portal-mediated** (nodal officer UI, uploads, reports). Bank systems therefore need to hold the authoritative record that can answer RBIO queries, such as timelines, IO review evidence and reasoned decisions. A system that keeps an audit-ready, clause-linked decision trail would fit this gap.
- Rising RB-IOS volume and the doubling of digital-fraud complaint TAT create pressure to resolve correctly at the bank or IO stage before cases reach RBIO.

### Gaps
- No official RBI documentation on a CMS API, data schema or file format for REs.
- No current (2024–2026) public detail on DAKSH upgrades or its data requirements.
- No confirmation that RBI's CMS AI Phase II is live.

---

## Q5. Common architectural patterns, and what none of the products do well

### Takeaway
The products repeat the same building blocks: case objects, a category taxonomy, a TAT/SLA matrix and time-based escalation (CRM/BPM). GRC tools add an obligation register mapped to controls and policies, AI regulatory-change extraction, a deviation/approval workflow, dashboards and audit trails. No product found closes the loop between the regulatory text and individual complaint decisions with machine-checkable, clause-cited reasoning.

### Cited Findings
- SLA/TAT matrix plus auto-escalation in CRM: HDFC/CRMNext — [HDFC policy](https://v1.hdfcbank.com/assets/pdf/grievance_redressal_policy.pdf); Salesforce FSC milestones and SLA letters — [Silverline](https://silverlinecrm.com/?p=9199)
- Audit trail of every action for regulatory tracking: Pega — [Pega brief](https://www.pega.com/system/files/resources/pdf/complaints-executive-brief.pdf)
- Obligations as versioned data objects plus GRC mapping: Ascent — [fintech.global](https://fintech.global/2025/10/13/how-ascentai-is-powering-the-next-generation-of-regulatory-compliance-automation/)
- Obligation, policy, control traceability matrix with HITL: Corlytics — [fintech.global](https://fintech.global/2025/11/11/is-explainable-ai-the-missing-link-in-regulatory-compliance/)
- Deviation workflow and unified dashboard per RBI circular: TeamLease RegTrack — [RegTrack](https://teamleaseregtech.com/product-services/regtrack-financial-institutions/)
- Regulation-specific SLA packs: Pega Smart Dispute — [Pega](https://pega.com/industries/financial-services/smart-dispute)
- RCA dashboards: Deloitte Salesforce accelerator — [Deloitte](https://www.deloitte.com/content/dam/assets-shared/docs/industries/financial-services/2023/gx-FSConnect-slide-6.pdf)

### Inferences (synthesis: what none of them visibly do well)
1. **No RBI-native complaint rule pack.** Nobody markets packaged rules for IO Directions 2026 (three-status outcome, auto-transfer to IO, 10/20-day IO windows, 30-day final decision, no same-unit closure) or IOS 2026 (30-day escalation, compensation caps). Banks hand-configure these in generic CRMs.
2. **Regulatory change does not reach case handling.** Obligation registers (CUBE/Corlytics/Ascent/RegTrack) map to policies and controls. Complaint CRMs hold static TAT tables. When RBI changes a timeline, as in the Oct 2025 draft to Jan 2026 final, someone must reconfigure manually. No product links a parsed obligation to an executable case rule.
3. **No decision-level explainability.** Audit trails record *who did what*, not *which clause required it and why*. Vendor "explainable AI" means showing source text to reviewers.
4. **Classification quality is unsolved.** KPMG still lists misclassification and duplicates as top problems. Vendor LLMs summarise and draft, and no published banking complaint-classification accuracy exists.
5. **Compensation calculation** under RBI TAT-harmonisation / IOS rules is not offered as a feature by any vendor found.
6. **Weak RBI CMS integration.** RBI CMS is portal-based, with no documented API. Bank systems do not reconcile automatically with RBIO cases.
7. **Systemic RCA tied to regulation.** RCA exists as dashboards (Deloitte/Salesforce, Agentforce "systemic issues"), but not as cross-complaint obligation-breach detection, such as "this product repeatedly breaches clause X".
8. **Indian languages.** Only the RBIH AGR *proposal* addresses translation/transliteration. No vendor evidence was found for Indic-language complaint classification in production.

### Gaps
- Rule-engine choices (Drools/DMN), event sourcing and data-lake designs were not disclosed by any vendor in the sources found. Statements about them would be speculation.
- No XBRL / CIMS complaint-reporting specifics were found (CIMS is referenced only for regulatory returns).
- Analyst reports (Gartner, Forrester, Celent, Chartis RiskTech100 full lists) were not accessible. Only the Chartis Corlytics mention was found.
