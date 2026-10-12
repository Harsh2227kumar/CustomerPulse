# State-of-the-art Architecture and Methods for a Bank Complaint-Handling Compliance Engine

Scope note: these notes cover methods and architecture, not the RBI rulebook itself. Items marked **[PK]** come from the researcher's prior knowledge of well-known primary sources. The URL is canonical, but the page was not re-fetched in this session, so the report writer should treat exact figures as "to verify". Items marked **[SPECULATIVE]** are design inferences, not findings.

---

## 1. Rules-as-code and machine-readable regulation: representing obligations, deadlines, effective dating and versioning

### Takeaway
Regulators have shown that machine-executable regulation is feasible, but none has turned it into production standards: BIS Ellipse, FCA/BoE DRR and Catala all reached proof of concept. The lesson that holds across them is that a precise data dictionary or common data model comes before executable rules. For a complaint engine, the pragmatic choice is a small, version-controlled rule DSL or DMN-style decision tables over a well-defined complaint data model, with effective-dated rule versions. Full formal legal languages are not needed.

### Cited Findings
- BIS Innovation Hub **Project Ellipse** Phase 1 (with MAS, Bank of England and ISDA) tested machine-executable reporting rules. It broke UK and Singapore retail-mortgage reporting requirements down and modelled them in ISDA's machine-executable **Common Domain Model**, which allowed automated cross-border analysis. Phase 2 moved to ML/NLP on unstructured and granular data. The project is listed as concluded, and its data model, demo and docs were the first release on BIS Open Tech. — [BIS Ellipse page](https://www.bis.org/about/bisih/topics/suptech_regtech/ellipse.htm); [BIS/MAS press release, 31 Mar 2022](https://www.bis.org/press/p220331.htm); [Ellipse docs](https://docs.bis.org/ellipse)
- The BIS has argued that machine-readable regulation can "narrow the gap between regulatory intent and interpretation" (as quoted in a secondary source). — [TechCrunch on SupTech](https://techcrunch.com/?p=2176605)
- **FCA/BoE Digital Regulatory Reporting (DRR):** a November 2017 TechSprint built a proof of concept that converted a small set of reporting instructions into machine-executable code, which pulled the required data directly from firm systems. The regulators judged it feasible but "far from proven". A Phase 1 pilot followed with two regulators and six firms, then Phase 2 with seven banks and a Phase 2 Viability Assessment in January 2020. — [FCA DRR page](https://www.fca.org.uk/firms/our-work-programme/model-driven-machine-executable-regulatory-reporting); [FCA DRR Phase 1 report](https://www.fca.org.uk/publication/discussion/digital-regulatory-reporting-pilot-phase-1-report.pdf)
- The independent PA Consulting review of DRR told regulators to keep monitoring tools before committing to a solution for generating Machine Executable Rules. It recommended that the next phase focus on a **Data Dictionary that precisely defines terms in the rulebook** as the foundation for automation. — [FCA: PA Consulting review](https://fca.org.uk/firms/pa-consulting-digital-regulatory-reporting-review-phase-1-and-2-digital-regulatory-reporting)
- **Catala** is a DSL designed for a direct, systematic translation of statutory law into executable code, with default-logic exceptions that mirror legal "notwithstanding" structure. When applied to US IRC §121 and French family benefits, it found a bug in the official implementation. — [Catala, arXiv 2103.03198](https://arxiv.org/abs/2103.03198v2); [Microsoft Research](https://www.microsoft.com/en-us/research/publication/catala-a-programming-language-for-the-law/)
- **LLM-to-Catala:** an NLLP 2025 benchmark and training set for translating tax law into Catala found automated legal code generation "feasible" with few-shot and fine-tuned models. A 2026 ICML paper, "Law to Code", used a multi-agent LLM pipeline to turn the German Corporate Income Tax Act (part 1) into Catala, validated with 86 synthetic scenarios with unit tests plus expert review. — [NLLP 2025.nllp-1.4](https://aclanthology.org/2025.nllp-1.4/); [ICML 2026 Law to Code](https://icml.cc/virtual/2026/80583)
- LLM-generated formal rules need review. In an LLM + SMT financial-compliance study (below), SMT code generation was only **86.2%** accurate. Errors included omitted entities, failing to zero out fines, and logically inconsistent constraint sets, and the code needed iterative prompting and manual review. — [arXiv 2601.06181](https://arxiv.org/html/2601.06181v1)
- **Other standards [PK]:** OASIS **LegalRuleML** represents deontic operators (obligation, permission, prohibition), defeasibility, temporal validity of norms (in force vs efficacy times) and source authority. — [OASIS LegalRuleML Core Spec](https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/legalruleml-core-spec-v1.0.html). OMG **DMN** with the FEEL expression language provides executable decision tables that business users can read. — [OMG DMN](https://www.omg.org/dmn/). **OpenFisca** is an open-source rules-as-code engine used for tax and benefit law in France, NZ and elsewhere, with parameters versioned by date. — [OpenFisca](https://openfisca.org/). No source found in this session evaluated OpenFisca or LegalRuleML for financial-conduct rules.

### Inferences
- **[SPECULATIVE]** Recommended representation: each obligation is a record with these fields:
  - `obligation_id`, `source` (circular number, paragraph), `deontic_type` (OBLIGATION/PROHIBITION/PERMISSION)
  - `subject` (bank, nodal officer), `trigger_event`, `condition` (an expression over the complaint data model), `deadline` (duration + calendar type + clock rules)
  - `exceptions`, `valid_from`/`valid_to`, `supersedes`/`superseded_by`, `version`, `test_cases`

  This mirrors LegalRuleML concepts, but the record should be stored as YAML/JSON or DMN tables in Git, with CI running the unit-test scenarios, as in the "Law to Code" approach.
- The DRR lesson suggests that the first-class artefact should be a **complaint data dictionary** (RBI category codes, channel, status, timestamps), with rules written against it.
- Use LLMs to *draft* rule encodings from circulars, with a human legal sign-off gate and mandatory unit tests. Do not let LLMs author live rules autonomously, given the 86% code-generation accuracy reported above.

### Gaps
- I found no reliable 2025–2026 source describing an RBI initiative on machine-readable regulation. Searches returned only vendor pages on RBI ADF/XBRL reporting ([Nelito](https://nelito.com/blog/what-are-regtech-and-suptech.html)). The report should not claim that RBI has such a programme unless another researcher found one.
- The MAS and Australian (NSW/Federal) Rules-as-Code programmes were not retrieved this session.
- I did not find a quantitative evaluation of DMN or LegalRuleML in conduct or complaint regulation.

---

## 2. Temporal reasoning for SLAs: event sourcing, pausable clocks, calendars, bitemporal audit

### Takeaway
No academic benchmark exists for this. Engineering practice is to event-source the complaint lifecycle (an immutable log of state-change events), derive SLA clocks as projections that apply start/pause/resume/stop rules and a holiday calendar, and store facts bitemporally. Bitemporal storage means the engine can answer two separate questions: what was true when, and what the system knew when. Published cloud reference architectures mention "SLA tracking" but do not specify the mechanism, which leaves room for a differentiated design.

### Cited Findings
- AWS's agentic complaint-classification reference says it "tracks SLA compliance" against regulatory windows: Reg AA 15-business-day acknowledgment, FDIC 14-day acknowledgment, and final response generally within 60 days. It does **not** describe timers or deadline fields. Its outputs only include next-step guidance such as "follow up within 24h, escalate if unresolved in 48h". — [AWS for Industries blog](https://aws.amazon.com/blogs/industries/automate-customer-complaint-classification-with-ai-agents-on-aws/)
- **Event sourcing [PK]:** every change to application state is captured as an event object in a sequence, so state can be rebuilt and replayed at any point in time. — [Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- **Bitemporal history [PK]:** separates *valid time* (when a fact was true in the world) from *record/transaction time* (when the system learned it). This lets the system correct retroactive facts without losing what it believed earlier. SQL:2011 standardises application-time and system-versioned tables. — [Fowler, Bitemporal History](https://martinfowler.com/articles/bitemporal-history.html)
- Temporal validity applies to regulations as well as complaints. SAT-Graph RAG argues that flat-chunk RAG has "temporal naivete" and cannot retrieve the version of a law in force on a given date. It proposes deterministic, temporally accurate reconstruction of provisions. — [arXiv 2505.00039 (alphaxiv overview)](https://alphaxiv.org/overview/2505.00039v5)

### Inferences
- **[SPECULATIVE] Target design:**
  1. An append-only `complaint_events` table holding event type, valid_time (business time of the occurrence, e.g. letter receipt date) and txn_time (DB insert time).
  2. An SLA engine that, for each applicable obligation version (chosen by the complaint's *received date* against rule `valid_from`/`valid_to`), computes a deadline from a clock definition. The clock definition covers start event, pause events (e.g. "awaiting customer information"), resume and stop events, plus calendar type (calendar vs working days, with a bank-holiday table per state/region, since Indian bank holidays vary by state).
  3. Recompute deadlines deterministically when late-arriving or corrected events come in, keeping prior computations for audit ("as known at T").
  4. Emit breach-risk alerts at thresholds.
- Effective-dating rule selection by complaint-received date matters when a circular changes mid-flight. The engine should record which rule version governed each complaint.

### Gaps
- I found no peer-reviewed evaluation of SLA-clock engines for complaints. Vendor engines (ServiceNow, Salesforce entitlements with pausable milestones) were not retrieved this session.
- RBI-specific pause/stop semantics (e.g. whether the 30-day clock under RB-IOS pauses for customer information) were not researched here and belong to the regulatory-rules researcher.

---

## 3. LLMs for compliance: obligation extraction, regulatory RAG/QA, neuro-symbolic, hallucination, grounding, GraphRAG, supersession

### Takeaway
The evidence strongly favours a **hybrid neuro-symbolic** design: LLMs retrieve, extract facts and draft, while deterministic rules or solvers decide. Even domain RAG products hallucinate 17–33% of the time in legal research. In one financial-enforcement study, a pure LLM's compliance-restoration F1 was 0.31, against 1.00 for LLM+SMT. Regulatory RAG needs a graph or temporal layer for cross-references and superseded circulars. Answer-quality metrics such as RePASs can be gamed.

### Cited Findings
**Benchmarks**
- **ObliQA / RIRAG:** 27,869 questions auto-generated from Abu Dhabi Global Market (ADGM) financial regulations, paired with passages. It introduced the **RePASs** metric, which scores whether an answer covers all relevant obligations and avoids contradictions. — [arXiv 2409.05677](https://arxiv.org/abs/2409.05677)
- The **RIRAG-2025 shared task** (RegNLP @ COLING 2025; Gokhan, Wang, Gurevych, Briscoe) had two subtasks: passage retrieval and answer generation. — [ACL Anthology 2025.regnlp-1.1](https://aclanthology.org/2025.regnlp-1.1); [Proceedings](https://aclanthology.org/2025.regnlp-1)
  - **Metric-gaming failure mode:** one team scored **0.947** RePASs by copying "obligation" sentences extracted from retrieved passages, without generating answers at all. A genuine iterative-refinement system scored a more plausible **0.639**.
  - Top approaches included LoRA-fine-tuned LLaMA-2-7B with expert refinement (Sun et al.) and fine-tuned embeddings plus lexical reranking (LeSeR, reported via recall@10/MAP@10). — [LeSeR arXiv 2412.06009](https://arxiv.org/html/2412.06009v1)
  - Exact leaderboard numbers could not be extracted (the PDF was unreadable to the fetch tool).
- **FinanceBench [PK]:** 10,231 questions over public-company filings. GPT-4-Turbo with a shared vector-store retrieval setup answered incorrectly or refused about **81%** of a 150-case sample. — [arXiv 2311.11944](https://arxiv.org/abs/2311.11944)
- **LegalBench [PK]:** 162 legal-reasoning tasks built collaboratively with legal professionals, covering rule-recall, rule-application, interpretation and so on. — [arXiv 2308.11462](https://arxiv.org/abs/2308.11462)
- **COLIEE** (statute and case retrieval/entailment) was not retrieved this session.

**Hallucination evidence**
- Magesh et al. (Stanford; J. Empirical Legal Studies 2025) found these hallucination rates:
  - Lexis+ AI: about 17%
  - Westlaw AI-Assisted Research: about 33%
  - GPT-4 general chatbot: about 43%

  RAG reduces hallucination but does not eliminate it, and vendor "hallucination-free" claims are overstated. Tools were tested on a May 2024 snapshot. — [arXiv 2405.20362](https://arxiv.org/abs/2405.20362v1); [Yale ISPS](https://isps.yale.edu/research/publications/isps25-33)
- In customer-facing complaints, the UK Financial Ombudsman Service estimated that AI likely contributed to up to **35%** of responses to initial assessments. It warned that incorrect generative-AI use creates disproportionate verification work. — [Regulation Tomorrow on FOS/Mills Review, Apr 2026](https://www.regulationtomorrow.com/2026/04/fos-responds-to-the-mills-review/)

**Neuro-symbolic results**
- **LLM + Z3 SMT on 87 Taiwan FSC enforcement cases:** the LLM generates constraints from statutes and facts, and Z3 checks legality (UNSAT = violation, with the unsat core identifying the clauses) and computes the minimal factual correction. — [arXiv 2601.06181](https://arxiv.org/html/2601.06181v1)
  - Compliance restoration: accuracy/precision/F1 = **1.00/1.00/1.00** for LLM+SMT vs **0.33/0.62/0.31** for LLM-only.
  - Reasoning time: 0.021 s vs 7.01 s per case.
  - LLM-only failure modes: bias toward "illegal" (50 false negatives out of 63 satisfiable cases), and over-reporting violations by treating advisory clauses as mandatory or citing vague, untraceable provisions.
  - Caveats: small problems (about 13 variables, 31 constraints) and limited reference labels.
- **GraphCompliance** aligns a Policy Graph and a Context Graph through a "Compliance Gate" before the LLM judgment. The authors note that graph-extraction quality drives final accuracy. — [arXiv 2510.26309](https://arxiv.org/pdf/2510.26309)
- **PolicyLLM** (ICML 2026) compiles natural-language policy into decision graphs validated by Z3 and enforces them on LLM outputs at runtime. — [ICML 2026](https://icml.cc/virtual/2026/78632)
- **Accountability paper:** an "LLM-Plus-Solver" pattern in which neural models extract candidate rules and solvers check satisfiability. — [arXiv 2512.12109](https://arxiv.org/pdf/2512.12109)
- **Older baseline:** BERT/GPT classification of legal provisions for compliance (food safety). — [arXiv 2404.17522](https://arxiv.com/abs/2404.17522)

**GraphRAG, cross-references, supersession**
- **ComplianceNLP** (arXiv 2604.23585) builds a regulatory KG with typed edges `AMENDS`, `SUPERSEDES`, `CROSSREFERENCES`, `IMPLEMENTS` (provision to obligation) and `APPLIESTO` (obligation to entity) over SEC, MiFID II and Basel III. It ingests feeds nightly and re-links new provisions within a 2-hop neighbourhood. *Most missed edges are implicit cross-references with no explicit citation marker.* — [arXiv 2604.23585](https://arxiv.org/pdf/2604.23585)
- **"RAGulating Compliance"** stores subject–predicate–object triples extracted from regulations alongside text sections and metadata for traceable QA. — [arXiv 2508.09893](https://arxiv.org/pdf/2508.09893)
- Graph-RAG for requirement traceability argues that graphs suit fine-grained cross-referencing. — [arXiv 2412.08593](https://arxiv.org/pdf/2412.08593)
- Practitioner framing (talk abstract, not peer-reviewed): a vector embedding cannot tell a 2022 circular from the 2024 version that superseded it. The fix is to model documents as temporal entities with SUPERSEDES edges, effective dates and sunset clauses. — [Neo4j NODES session](https://neo4j.com/nodes/agenda/graph-powered-temporal-validity-preventing-rag-systems-from-citing-dead-regulations/)

### Inferences
- **[SPECULATIVE] Target pipeline:**
  1. Ingest RBI circulars and master directions, then parse them into a provision tree.
  2. LLM-assisted extraction of obligations into the schema from Section 1, with human approval.
  3. A regulation KG with AMENDS/SUPERSEDES/CROSSREF edges and valid-time on each provision.
  4. Hybrid retrieval (BM25 + dense + rerank), filtered to provisions in force at the query date, expanded by graph neighbours.
  5. Answer generation with mandatory paragraph-level citations.
  6. A post-hoc citation verifier (NLI/entailment check that each claim is supported by the cited span) plus a "superseded source" check.
  7. Compliance decisions such as breach/no-breach and mandatory-content-present are taken by deterministic rules over LLM-extracted facts, never by free-form LLM judgment.
- Evaluate with retrieval metrics (recall@10, MAP@10), obligation coverage and contradiction checks (RePASs-style), and a human-graded gold set. Guard against metric gaming by also grading fluency and answerability.
- Expect regulatory RAG error rates in the tens of percent without verification. Budget for human review of any regulator-facing output.

### Gaps
- No RIRAG leaderboard numbers were extracted. The ComplianceNLP and SAT-Graph RAG evaluation figures were not opened.
- No published benchmark on RBI circulars exists that I could find. An RBI equivalent of ObliQA would be novel.
- No study quantified citation-faithfulness verifier accuracy (e.g. NLI-based) on regulatory text in this session.

---

## 4. Complaint NLP: classification on CFPB and Indian data, Hinglish/Indic, complaint-vs-query

### Takeaway
Rigorous public benchmarks are thin. Fine-tuned models report around 90%+ on CFPB product classification and about 97.5% on complaint-vs-non-complaint triage, but only on small or synthetic test sets. Code-mixed Hinglish complaint classification is much harder: about 74% accuracy across 14 classes for the best model. MuRIL generally beats IndicBERT on Hinglish tasks. Teams need their own labelled evaluation set.

### Cited Findings
- **CFPB, Qwen2.5-7B LoRA** generating structured product/sub-product/issue/sub-issue JSON, then TF-IDF mapping to official labels: product exact match about **0.908** (F1 about 0.907) on 250 held-out complaints, vs about 0.010 for the base model. This is self-reported on a model card with a small test set. — [Model card](https://friendli.ai/models/aryachakraborty/arya-cfpb-qwen_2.5-7b-lora-V2)
- Only about one in five CFPB complaints includes a public narrative (narratives published since June 2015). CFPB taxonomies change over time, so accuracy does not transfer across taxonomy versions. — [TDS write-up](https://towardsdatascience.com/classifying-complaints-with-natural-language-processing-e3b2765d525f/)
- **Complaint-vs-non-complaint (AWS reference):** **97.5%** identification accuracy and 2.5% false-negative rate, with 100% category accuracy on fee disputes when detailed rubrics were used. About 18 s end to end vs 5–9 min manual triage. Tested on a **synthetic set of 50 transcripts**. Accuracy improved with more specific knowledge-base criteria. — [AWS for Industries](https://aws.amazon.com/blogs/industries/automate-customer-complaint-classification-with-ai-agents-on-aws/)
- **Hinglish cybercrime complaints** (Indian government data, 14 classes): best model HingRoBERTa reached **74.41% accuracy / 71.49% F1**. MuRIL and IndicBERT were not tested. — [arXiv 2412.16614](https://arxiv.org/html/2412.16614v1)
- **MuRIL vs IndicBERT on Hinglish (cyberbullying):** MuRIL outperformed RoBERTa and IndicBERT by **1.36–13.07 pp**, with 86.97% (Bohra), 84.62% (BullyExplain) and 75.41% (Kumar). — [arXiv 2506.16066](https://arxiv.org/abs/2506.16066v1)
- **Hinglish toxicity with banking hard negatives** (self-published): nine configurations (MuRIL base/large, IndicBERT v2, ensemble) all reached 0.70–0.76 code-mixed AUROC. The author attributes the ceiling to label noise rather than model size. — [HF model card](https://huggingface.co/rotalabs/sakshi-guard-mix)
- IndicBERT accuracy on Hinglish hate detection ranged about 0.63–0.72 depending on code-mixing ratio and augmentation. — [arXiv 2405.20755](https://arxiv.org/pdf/2405.20755)

### Inferences
- **[SPECULATIVE]** Use a two-stage classifier:
  - Stage 1 (high recall): complaint vs query/request, tuned to minimise false negatives, because a missed complaint is a regulatory failure.
  - Stage 2: RBI category/sub-category. Use a fine-tuned MuRIL or a Hinglish-aware LLM with taxonomy rubrics held in a configurable knowledge base (the AWS pattern), plus transliteration normalisation.
- Route low-confidence predictions to humans. Track per-language and per-channel accuracy separately.
- Label noise is the binding constraint for Indic data. Invest in annotation guidelines and inter-annotator agreement.

### Gaps
- No public Indian *banking* complaint dataset or benchmark was found. No Sarvam or AI4Bharat (IndicTrans2, IndicBERT v2) evaluations on complaints were found.
- Negation handling, root-cause clustering and duplicate-detection accuracy were not covered by sources retrieved this session.

---

## 5. Response compliance checking: QA of customer replies, tone, mis-selling, Consumer Duty

### Takeaway
Regulators (FCA) expect granular complaint MI, real root-cause analysis and outcome monitoring, especially for vulnerable customers. I found no regulator publication specifying automated response QA. Industry practice is that AI extracts and drafts while humans own the determination. Automated QA of replies should therefore be a checklist of deterministic content rules applied over LLM-extracted facts, plus sampling.

### Cited Findings
- **FCA December 2024 complaints and RCA review (40 firms):** many firms need to strengthen governance, MI and root cause analysis. MI must be granular enough to show outcomes for customers with characteristics of vulnerability. Board discussion must be evidenced, not "tick-box". Changes need post-implementation effectiveness reviews. — [Linklaters](https://financialregulation.linklaters.com/post/102jrak/fca-feeds-back-to-firms-on-complaints-and-root-cause-analysis); [TLT on 2026 refresh](https://www.tlt.com/insights-and-events/insight/fca-updates-complaints-and-root-cause-analysis-good-practice-guidance---what-firms-need-to-know)
- The FCA supports AI use but expects firms to define the intended customer outcome per AI use case, evidence fair value, monitor bias and exclusion, and keep governance in place. — [FinTech Global, Apr 2026](https://fintech.global/2026/04/16/fca-targets-ai-governance-and-off-channel-messaging/)
- **Live example:** in Manx Financial Group's motor-finance redress, the technology reads correspondence, extracts data and drafts customer communications, but does not decide outcomes. "Machine handles intake, extraction and drafting; human owns the determination." — [ResultSense, Sep 2026](https://www.resultsense.com/news/2026-09-04-manx-financial-ai-complaints-redress/)
- FCA FG21/1 (vulnerable customers) implies automated tools must detect vulnerability signals (as cited by a vendor guide). — [Lorikeet guide](https://www.lorikeetcx.ai/articles/ai-support-uk-financial-services-guide)

### Inferences
- **[SPECULATIVE]** Response QA module:
  1. An obligation checklist per complaint type, compiled from rules. For RBI this could include acknowledgment, complaint reference number, final-reply reasons, escalation rights to the RBI Ombudsman with the timeline and CMS portal, and the nodal officer contact. The exact list should be confirmed by the RBI rules researcher.
  2. An LLM extracts "is element X present, and where (span)?", and a deterministic rule decides pass/fail.
  3. Classifiers for tone, empathy, vulnerability cues and mis-selling or prohibited statements (e.g. discouraging escalation).
  4. Block sending, or require supervisor review, on failure. Log span-level evidence.

### Gaps
- No quantitative study of automated complaint-response QA accuracy was found. CFPB supervisory highlights on complaint-response deficiencies were not retrieved.

---

## 6. Model risk management, explainability, HITL, drift, tamper-evident audit

### Takeaway
SR 11-7 (US) and RBI FREE-AI (August 2025) both push toward an inventory of models, independent validation, ongoing monitoring, audit, and board-level accountability. A compliance-AI engine should ship with a model registry, golden evaluation sets, confidence-thresholded human review, drift dashboards, and an append-only, hash-chained evidence log.

### Cited Findings
- **RBI FREE-AI report** (13 August 2025; committee chaired by Prof. Pushpak Bhattacharyya, IIT Bombay): 7 "Sutras", **26 recommendations** under 6 pillars (Infrastructure, Policy, Capacity, Governance, Protection, Assurance). Recommendations include:
  - board-approved AI policies
  - an AI inventory in each regulated entity
  - risk-based AI audits
  - AI disclosures in annual reports
  - AI-specific consumer protection
  - incident reporting
  - an industry AI compliance toolkit
  - application of outsourcing guidelines to third-party AI, with contractual safeguards on bias, accountability and data use

  Several of these details come from secondary commentary, so verify them against RBI's text. — [KPMG India](https://kpmg.com/in/en/insights/2025/08/rbi-free-ai-committee-report-on-framework-for-responsible-and-ethical-enablement-of-artificial-intelligence.html); [Law.asia](https://law.asia/rbi-ai-framework/); [Securiti](https://securiti.ai/free-ai-framework-in-indian-finance/)
- **SR 11-7 [PK]** (Fed/OCC 2011) defines model risk management as sound development and implementation, independent validation (conceptual soundness, ongoing monitoring, outcomes analysis) and governance (inventory, policies, effective challenge). — [Federal Reserve SR 11-7](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
- **AWS reference audit controls:** CloudTrail on gateway, agent and knowledge-base calls; CloudWatch logging of classification decisions, confidence scores and routing; optional logging of an input hash and rationale at each decision point. Agents work on PII-redacted text (Amazon Comprehend) while unredacted originals sit under restricted access. Each component has its own scoped IAM role, with customer-managed KMS keys and a human approval gate before actions execute. — [AWS for Industries](https://aws.amazon.com/blogs/industries/automate-customer-complaint-classification-with-ai-agents-on-aws/)
- **Tamper-evident logs [PK]:** Merkle-tree append-only logs (Certificate Transparency, RFC 6962) let anyone detect insertion or rewriting of past entries through consistency proofs. — [RFC 6962](https://datatracker.ietf.org/doc/html/rfc6962). AWS has ended support for its managed ledger database QLDB (end of support announced for 31 July 2025), so hash chains should be implemented in-application or on Postgres/S3 Object Lock rather than relying on QLDB. **[PK — verify]**

### Inferences
- **[SPECULATIVE]** Controls to build in:
  - A model card per component (classifier, extractor, RAG answerer), listing intended use, eval metrics by language and channel, and known failure modes.
  - A gold evaluation set refreshed quarterly with drift monitoring: label distribution, confidence distribution, human-override rate.
  - Confidence thresholds: auto-accept above τ_high, mandatory review below τ_low, plus 100% review for regulator-facing escalations and money decisions (AWS's suggestion for fee reversals).
  - An evidence record per decision covering input hash, model and version, prompt version, retrieved provision IDs and versions, rule version, output and reviewer. Each record is chained by SHA-256 of the previous record and periodically anchored, e.g. a daily Merkle root stored in WORM storage.
- This maps directly onto the FREE-AI asks for an "AI inventory", "audit" and "incident reporting".

### Gaps
- RBI's verbatim FREE-AI text (which items are binding vs advisory) was not fetched.
- No quantitative studies on HITL threshold tuning for compliance AI were found.

---

## 7. Cloud reference architectures (AWS/Azure/GCP) for complaint intelligence and regulatory GenAI

### Takeaway
The most concrete public reference is AWS's agentic complaint classifier (Bedrock AgentCore + Strands, a supervisor agent with specialist agents, a knowledge-base-driven taxonomy, PII redaction and a human approval gate). It is strong on classification and security but weak on SLA mechanics, rule versioning and regulatory change management. Those weaknesses are the gaps a best-in-class engine should fill.

### Cited Findings
- **AWS agentic complaint classification components:**
  - Amazon Transcribe Streaming (voice to text)
  - Supervisor Agent on Bedrock AgentCore Runtime, which filters intent so that only confirmed complaints proceed
  - AgentCore Identity (in/outbound auth) and AgentCore Gateway (MCP endpoint orchestrating specialist agents and CRM access)
  - Complaints Agent (category, severity from critical to low, routing group)
  - Bedrock Knowledge Base holding a configurable taxonomy that can change without code changes
  - Amazon Comprehend PII redaction
  - Strands Agents SDK
  - Streamlit UI with approval gate

  Severity factors are financial impact, regulatory deadline proximity, sentiment and recurrence. — [AWS for Industries](https://aws.amazon.com/blogs/industries/automate-customer-complaint-classification-with-ai-agents-on-aws/)
- **Amazon Finance regulatory-inquiry assistant:** Bedrock Knowledge Bases with OpenSearch Serverless for RAG, Claude Sonnet 4.5 for multi-turn chat, and OpenTelemetry + Langfuse for observability. — [Summary of AWS ML blog, May 2026](https://aihub.hkuspace.hku.hk/2026/05/13/how-amazon-finance-streamlines-regulatory-inquiries-by-using-generative-ai-on-aws/)
- **Teradata + Bedrock Customer Complaint Analyzer:** complaint-vs-not prediction, clustering, topic detection, summarisation and sentiment, on VantageCloud Lake. — [Teradata](https://kr.teradata.com/solutions/amazon-bedrock-complaint-analyzer)

### Inferences
- **[SPECULATIVE] Target architecture**, combining all sections:
  1. Omnichannel ingestion (email, branch, call transcripts, CMS/RBI portal feeds) → PII redaction.
  2. Complaint/query triage plus multilingual classification (Section 4).
  3. Event-sourced case store with bitemporal facts (Section 2).
  4. Versioned obligation registry as rules-as-code, with tests (Section 1), fed by a regulatory-change pipeline: circular ingestion → LLM obligation extraction → human approval → KG with SUPERSEDES edges (Section 3).
  5. Deterministic SLA/obligation evaluator emitting breach-risk alerts.
  6. Response drafting with RAG + citation verification, and a response-QA gate (Section 5).
  7. RCA/analytics and MI by segment and vulnerability.
  8. MRM layer: registry, eval sets, drift, HITL queue, and a hash-chained evidence log (Section 6).
- The key differentiators over published cloud references are explicit SLA clocks, effective-dated rule versions, supersession-aware retrieval, and a tamper-evident audit trail.

### Gaps
- Azure Architecture Center and Google Cloud reference architectures for complaint or regulatory GenAI were not retrieved this session.
- No published cloud reference covers rule versioning or regulatory change management for complaints.
