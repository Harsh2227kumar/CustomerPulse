# Open-Source Code Review for an RBI Complaint Compliance Engine (CustomerPulse)

Method: GitHub repo search with the authenticated `gh` CLI (2026-10-12). I shallow-cloned 21 repos and read the source files directly. Where clones failed because of Windows long-path limits (Presidio, Manas-singh14, compliance-trestle) or the repo was too large (OPA, CDM), I fetched the specific files from raw.githubusercontent.com. Star counts and last-push dates come from the GitHub API on 2026-10-12.

**Files actually read (main ones):**
- ComplianceIQ: `backend/app/services/{generator,hybrid_search,chunker}.py`, `backend/app/eval/{run_eval.py,golden_set.json}`
- ComplyNext: `backend/src/rules_engine/npa_engine.py`, `backend/src/scraper/rbi_scraper.py`
- rbi-ombudsman-analytics: `classifier/{classify_complaints.py,generate_synthetic_complaints.py,metrics.json}`
- banking-compliance-rag-chatbot: `rag.py`, `test_rag_questions.py`
- ReguMind_AI: `backend/src/services/risk.service.js`
- Regulatory-Change-Autopilot: `src/watcher/extractor.py`, `src/rag/gap_analyser.py`
- cfpb-complaint-nlp: `CFPB_NLP_OneClick.ipynb`, `results_table.md`
- openfisca-core: `variables/variable.py`, `parameters/parameter.py`, `tracers/full_tracer.py`, `reforms/reform.py`
- json-rules-engine: `src/{rule,condition,almanac}.js`, the `test/` listing
- Microsoft RulesEngine: `Models/{Rule,RuleResultTree}.cs`
- GoRules Zen: `core/engine/src/{engine.rs,nodes/decision_table/mod.rs,policy/mod.rs}`, `core/expression/src/functions/date_method.rs`
- durable_rules: `libpy/durable/lang.py`
- Blawx: `blawx/{dates.py,reasoner.py,models.py}`
- Catala: `compiler/shared_ast/{definitions.ml,operator.ml,coverage.mli}`, the `stdlib/` listing
- holidays: `holidays/countries/india.py`, `holidays/holiday_base.py`
- workalendar: `workalendar/core.py`
- Presidio: `country_specific/india/in_aadhaar_recognizer.py`, `in_pan_recognizer.py`
- compliance-trestle: `trestle/oscal/catalog.py`
- NeMo Guardrails: `rails/llm/options.py`, the `actions/` listing
- OPA: `v1/topdown/time.go`

Two repos turned out to be empty or README-only: `Sanjay-jat/regulatory-intelligence-engine` (the clone has only `.git`) and `anuragthakur73/rbi-master-directions-assistant` (only a README).

CustomerPulse baseline, read locally: `backend/app/compliance/rules.json` holds 17 rules shaped `{rule_id, description, condition_type, severity, mandatory_action, action{action_type, owner, description, deadline_days}}`. None of them has an effective date, version, or source-circular field. `engine.py` dispatches each `condition_type` to a hard-coded method, for example `_legal_or_regulatory_keyword`, which does a `keyword in text` substring check over lower-cased combined text.

---

## Key Question 1: How do the best projects represent rules, versions and effective dates in code?

### Takeaway
Only the legal "rules-as-code" family (OpenFisca, Catala, Blawx) treats effective dates and legislative references as first-class concepts. OpenFisca's model is the most directly copyable into Python/JSON: parameter values keyed by start date, plus formulas selected by date. The generic business-rule engines (json-rules-engine, Microsoft RulesEngine, Zen, durable_rules, OPA) have no notion of rule validity periods. What they do well is structured, per-condition evaluation traces, and CustomerPulse should copy those for explainability.

### Cited Findings

**OpenFisca-core**: 242 stars, AGPL-3.0, last push 2026-10-12.
- Date-versioned formulas. A variable can define several methods named `formula_YYYY`, `formula_YYYY_MM` or `formula_YYYY_MM_DD`. `Variable.parse_formula_name` parses these with the regex `formula_(\d{4})(?:_(\d{2}))?(?:_(\d{2}))?$` into start dates kept in a sorted dict, and `Variable.get_formula(period)` picks the formula in force at the requested instant. — [variable.py](https://github.com/openfisca/openfisca-core/blob/master/openfisca_core/variables/variable.py)
- Variables carry an `end` attribute (YYYY-MM-DD; the variable "disappears from the legislation"), a `reference` (a string or list of legislative URLs), and a `unit`. `set_end` refuses a formula that starts after `end`. — [variable.py](https://github.com/openfisca/openfisca-core/blob/master/openfisca_core/variables/variable.py)
- Parameters are value histories keyed by start date, and each value can carry its own metadata. The docstring example is `"2015-01-01": {'value': 550, 'metadata': {'reference': 'http://taxes.gov/income_tax/2015'}}`. `Parameter._get_at_instant` walks `values_list` (newest first) and returns the first value whose `instant_str <= instant`. `Parameter.update(start, stop, value)` splices in a new interval. — [parameter.py](https://github.com/openfisca/openfisca-core/blob/master/openfisca_core/parameters/parameter.py)
- Explainability comes from `FullTracer`, with `record_calculation_start`, `record_parameter_access` and `record_calculation_result`. It builds a computation tree that `ComputationLog.print_log` renders, so every computed value can be traced back to the parameters and dated values it used. — [full_tracer.py](https://github.com/openfisca/openfisca-core/blob/master/openfisca_core/tracers/full_tracer.py)
- "What-if" versioning uses reforms: `Reform.modify_parameters(modifier_function)`, plus `TaxBenefitSystem.update_variable` and `neutralize_variable`. — [reform.py](https://github.com/openfisca/openfisca-core/blob/master/openfisca_core/reforms/reform.py)

**Catala**: 2,418 stars, Apache-2.0, last push 2026-10-01.
- The AST models legal defeasibility directly. A rule definition can be an `Exception of { label; ... }` and the operator set includes `HandleExceptions`, so a later circular can override a base rule without editing it. — [definitions.ml](https://github.com/CatalaLang/catala/blob/master/compiler/shared_ast/definitions.ml)
- Date arithmetic is explicit about ambiguity. `Add_dat_dur` and `Sub_dat_dur` take a `date_rounding` argument (`RoundUp` or `RoundDown`), which forces an author to decide how "Jan 31 + 1 month" resolves. — [definitions.ml](https://github.com/CatalaLang/catala/blob/master/compiler/shared_ast/definitions.ml), [operator.ml](https://github.com/CatalaLang/catala/blob/master/compiler/shared_ast/operator.ml)
- There is a stdlib date module (`stdlib/date_en.catala_en` with a C backend `date_internal.c`) and a new `coverage.ml` module (2025) for test coverage of legal scopes. — [stdlib](https://github.com/CatalaLang/catala/tree/master/stdlib), [coverage.mli](https://github.com/CatalaLang/catala/blob/master/compiler/shared_ast/coverage.mli)
- The tutorial examples are no longer in the main repo, which suggests they moved to a separate examples repository. I did not read a full Catala program.

**Blawx**: 157 stars, MIT, last push 2024-11-01, so not very active.
- Rules compile to s(CASP), a constraint answer-set Prolog. `reasoner.py` calls `scasp(Query,[tree(Tree),model(Model),...])` followed by `human_justification_tree(Tree,[])`, and `generate_answers` packages the result into `Tree`, `Terms`, `Residuals` and `Variables`. That gives a natural-language justification tree for every answer. — [reasoner.py](https://github.com/Lexpedite/blawx/blob/main/blawx/reasoner.py)
- Date predicates have natural-language templates, for example `#pred date_compare(X,lt,Y) :: '@(X) is before @(Y)'` and `date_add`. Dates are Unix timestamps. `dates.py` injects `blawx_today` from `datetime.now()` at import time, which bakes server-local "now" into the reasoner. — [dates.py](https://github.com/Lexpedite/blawx/blob/main/blawx/dates.py)
- Rule text is stored as Akoma Ntoso-style `RuleDoc` models, so encodings are anchored to legal sections (`ruleDocLegalTextView`). I found no effective-date fields in `models.py`. — [models.py](https://github.com/Lexpedite/blawx/blob/main/blawx/models.py)

**json-rules-engine**: 3,143 stars, ISC, last push 2026-02-16.
- A rule is JSON with `conditions` (all/any/not trees), an `event {type, params}`, a `priority` (integer of at least 1, higher runs first) and a `name`. There are no date or version fields. — [rule.js](https://github.com/CacheControl/json-rules-engine/blob/master/src/rule.js)
- Explainability: after evaluation each condition serialises `factResult`, `valueResult` and `result` (`Condition.toJSON`), so the rule result shows exactly which fact value failed which comparison. — [condition.js](https://github.com/CacheControl/json-rules-engine/blob/master/src/condition.js)
- Facts are resolved lazily through an `Almanac` with a cache (`factValue`, `addRuntimeFact`, JSONPath `pathResolver`). There are about 30 test files covering all/any/not, fact priority, recursion, caching, error handling and performance. — [almanac.js](https://github.com/CacheControl/json-rules-engine/blob/master/src/almanac.js), [test/](https://github.com/CacheControl/json-rules-engine/tree/master/test)

**Microsoft RulesEngine**: 4,358 stars, MIT, last push 2026-09-11.
- `Rule` has `RuleName`, `Expression` (a C# lambda string), `Operator`, nested `Rules`, `LocalParams`, `Enabled`, `SuccessEvent`, `ErrorMessage`, `Actions` and `WorkflowsToInject`. There are no effective-date fields. — [Rule.cs](https://github.com/microsoft/RulesEngine/blob/main/src/RulesEngine/Models/Rule.cs)
- `RuleResultTree` returns `Rule`, `IsSuccess`, `ChildResults` (recursive), `Inputs`, `ActionResult` and `ExceptionMessage`, which is a nested explanation tree. — [RuleResultTree.cs](https://github.com/microsoft/RulesEngine/blob/main/src/RulesEngine/Models/RuleResultTree.cs)

**GoRules Zen**: 2,057 stars, MIT, last push 2026-10-09.
- JDM decision graphs contain decision-table nodes with `DecisionTableHitPolicy::First` or `::Collect`. Tracing is opt-in (`EvaluationOptions.trace`), and the decision table records `DecisionTableNodeTrace::FirstHit(DecisionTableRowTrace)` or `::Collect(traces)`, meaning which row matched. — [decision_table/mod.rs](https://github.com/gorules/zen/blob/master/core/engine/src/nodes/decision_table/mod.rs), [engine.rs](https://github.com/gorules/zen/blob/master/core/engine/src/engine.rs)
- The expression language has calendar date methods (`Add`, `Sub`, `StartOf`, `EndOf`, `Diff`, `IsSame`, `IsBefore`, `Weekday`, `Tz`) but no business-day or holiday functions. A grep for "business" and "holiday" in `core/expression/src` returned nothing. — [date_method.rs](https://github.com/gorules/zen/blob/master/core/expression/src/functions/date_method.rs)
- A new `policy` module adds a linter, validator, typed blocks (`assertion`, `decision_table`, `match_block`), `BlockTrace`/`ConditionTrace`, and `Diagnostic` types. It is evolving towards authored "policy documents" with static analysis. — [policy/mod.rs](https://github.com/gorules/zen/blob/master/core/engine/src/policy/mod.rs)

**durable_rules**: 1,301 stars, MIT, last push 2025-07-15.
- A Rete-style engine with `ruleset`, `when_all`/`when_any`, statecharts and a `timeout(name)` timer primitive. It handles time-based escalation as events ("timer fired") rather than as computed deadlines. — [lang.py](https://github.com/jruizgit/rules/blob/master/libpy/durable/lang.py)

**OPA / Rego**: 12,350 stars, Apache-2.0, last push 2026-10-12.
- The time built-ins are `time.now_ns`, `parse_rfc3339_ns`, `parse_duration_ns`, `date`, `clock`, `weekday`, `add_date` and `diff`. There is no working-day or holiday support, and rule bundles have no validity periods (versioning sits at the bundle and revision level). — [time.go](https://github.com/open-policy-agent/opa/blob/main/v1/topdown/time.go)

**OSCAL compliance-trestle**: 284 stars, Apache-2.0, last push 2026-10-05.
- OSCAL `Control` (a Pydantic model) has `params`, `props`, `links` and `parts`. Obligations are therefore catalog entries with parameters (for example "N days") and links to source documents, which is a good schema for "requirement then parameter then evidence". — [catalog.py](https://github.com/oscal-compass/compliance-trestle/blob/develop/trestle/oscal/catalog.py)

### Inferences
- The best pattern for CustomerPulse is OpenFisca's split between versioned parameters and formulas. Keep deadlines such as "acknowledge within N days" or "escalate to the Internal Ombudsman after N days" as parameters with dated histories and `reference` metadata (circular number, paragraph, URL). Keep the logic as a small set of formulas. CustomerPulse's `deadline_days: 3` in `rules.json` would become `{"2024-01-01": {"value": 3, "metadata": {"reference": "<circular>"}}}`, and evaluation would look up the value in force at `complaint.received_at`, not at "now".
- Catala's explicit `RoundUp`/`RoundDown` and Blawx's use of server-local `now()` are two sides of the same lesson. Deadline arithmetic must be deterministic, timezone-explicit (IST) and anchored to an event timestamp.
- For explainability, any of the json-rules-engine per-condition `factResult`, the MS RulesEngine `RuleResultTree`, or the Zen row traces fits CustomerPulse's current "evaluated once" model better than adopting a full logic engine.

### Gaps
- I did not read a full OpenFisca country package (for example the YAML parameter files in openfisca-france) or a full Catala example program. The descriptions above come from the core library code.
- I did not inspect Drools/KIE, LogicalEnglish2 or FINOS Legend source. I found FINOS CDM's reporting codelists (for example `rosetta-source/.../codelist/json/reporting-regime-1-7.json` in [CDM](https://github.com/finos/common-domain-model)), but I did not read its Rosetta DRR rule files. Its applicability to complaint handling is likely low because it targets trade reporting.

---

## Key Question 2: Which RBI-specific repos exist and how good are they actually?

### Takeaway
Every RBI-specific repo I found has 0 to 10 stars and is a student, portfolio or hackathon project. None implements RBI complaint-handling timelines: the Integrated Ombudsman Scheme escalation, the 30-day bank resolution window, or the failed-transaction TAT and compensation rules. Most are thin RAG wrappers with naive chunking, and evaluation is either absent or broken. The one deterministic rule engine (ComplyNext's NPA classifier) is clean but covers loan asset classification, not complaints. Code quality and data provenance are weak across the category.

### Cited Findings

**pavith-raj/ComplianceIQ**: 1 star, no license, last push 2026-07-22. A FastAPI + Chroma + Groq RAG over RBI, SEBI and IRDAI PDFs.
- `chunker.py`: fixed-size character sliding window (`chunk_text`). The regulator is inferred from the filename prefix (`infer_regulator`: "rbi..." becomes RBI). Metadata is page number and regulator only, with no circular number or date. — [chunker.py](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/services/chunker.py)
- `hybrid_search.py`: BM25 (`rank_bm25`) union vector search. The docstring admits reciprocal-rank fusion is "a future upgrade". The `where` filter is only applied to the BM25 hits. — [hybrid_search.py](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/services/hybrid_search.py)
- `generator.py`: a grounding prompt forces citations like `[RBI, p.4]` and a fixed refusal string. `diff_excerpts` asks the LLM whether excerpt B "supersede[s], contradict[s], or simply add[s] to A". This is the only supersession logic, and it is LLM judgment, not data. — [generator.py](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/services/generator.py)
- Evaluation is effectively broken. `run_eval.py` uses RAGAS faithfulness, answer_relevancy and context_precision, but passes citation labels (`"[RBI, p.4]"`) as `contexts` instead of the retrieved text, so faithfulness cannot be measured meaningfully. `golden_set.json` has only 2 items whose ground truths are placeholders ("Replace with the actual answer..."). — [run_eval.py](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/eval/run_eval.py), [golden_set.json](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/eval/golden_set.json)

**Nevin100/ComplyNext-Minor_Project**: 1 star, no license, last push 2026-09-18. A multi-tenant compliance platform for Indian NBFCs and co-operative banks.
- `npa_engine.py` is a deliberately deterministic engine. Its docstring says RBI's DPD thresholds "are fixed legal rules". `classify_term_loan` maps DPD to Standard, SMA-0, SMA-1, SMA-2 or NPA at 0, 30, 60 and 90 days. `classify_revolving` skips SMA-0. `ClassificationResult` carries `rule_reference` (a constant, "RBI Master Circular - IRACP Norms (Oct 1, 2021)"), a plain-English `reasoning` string, and `is_misclassified`, which compares against the bank's existing tag. The thresholds are hard-coded `if/elif` with no effective dating, and the tests are only a `__main__` demo. — [npa_engine.py](https://github.com/Nevin100/ComplyNext-Minor_Project/blob/main/backend/src/rules_engine/npa_engine.py)
- `rbi_scraper.py` uses requests and BeautifulSoup on two hard-coded RBI NotificationUser.aspx URLs. It trims navigation clutter with the regex `RBI/\d{4}-\d{2,4}/\d+`, which is a reusable trick for finding where an RBI circular body starts, and uses 300-word chunks. — [rbi_scraper.py](https://github.com/Nevin100/ComplyNext-Minor_Project/blob/main/backend/src/scraper/rbi_scraper.py)

**Prasanthdj8/rbi-ombudsman-analytics**: 0 stars, no license, last push 2026-06-22. The only repo I found aligned with RBI Ombudsman complaint categories.
- `classify_complaints.py`: TF-IDF (1-2-grams) with a LinearSVC (`class_weight="balanced"`) over 6 RBI Ombudsman categories: Loans and Advances, Credit Cards, ATM/Debit Cards, Mobile/Electronic Banking, Deposit Accounts, Pension Related. — [classify_complaints.py](https://github.com/Prasanthdj8/rbi-ombudsman-analytics/blob/main/classifier/classify_complaints.py)
- The training data is entirely synthetic. The author's own script says RBI "does not publish individual complaint narratives". The reported `metrics.json` shows precision, recall and F1 of 1.0 on every class, with a support of 10 per class. That indicates a trivially separable synthetic set and gives no evidence of real-world performance. — [generate_synthetic_complaints.py](https://github.com/Prasanthdj8/rbi-ombudsman-analytics/blob/main/classifier/generate_synthetic_complaints.py), [metrics.json](https://github.com/Prasanthdj8/rbi-ombudsman-analytics/blob/main/classifier/metrics.json)
- The repo also includes `data/ombudsman_trends.json` and `data/SOURCES.md`, which describe trend data from published RBI Ombudsman annual reports. I did not verify the contents. — [repo](https://github.com/Prasanthdj8/rbi-ombudsman-analytics)

**nithinraj49/banking-compliance-rag-chatbot**: 2 stars, MIT, last push 2026-01-18.
- `rag.py` is a script-style pipeline. It loads `chunks.pkl` and `bm25_index.pkl` with pickle, uses Chroma with `HybridRetriever(alpha=0.5)`, and calls Groq `llama-3.3-70b-versatile`. It contains a hard-coded Groq API key committed to the repo, which is a security defect. The corpus is Basel LCR, FATF and risk-based-approach documents, not RBI circulars, despite the description. — [rag.py](https://github.com/nithinraj49/banking-compliance-rag-chatbot/blob/main/rag.py)
- `test_rag_questions.py` only prints answers to a list of questions. It has no assertions or metrics. — [test_rag_questions.py](https://github.com/nithinraj49/banking-compliance-rag-chatbot/blob/main/test_rag_questions.py)

**shivampatra2027/ReguMind_AI**: 4 stars, last push 2026-07-07. Node, Ollama and Gemini, "Offline Agentic AI Compliance Platform for RBI, SEBI & IRDAI".
- `backend/src/services/risk.service.js`, the advertised risk logic, is an empty file. The README overstates what the code does. — [risk.service.js](https://github.com/shivampatra2027/ReguMind_AI/blob/main/backend/src/services/risk.service.js)

**Manas-singh14/Regulatory-Change-Autopilot**: 1 star, no license, last push 2026-07-29. Watches RBI, SEBI and IRDAI feeds, uses Qdrant RAG, exposes an MCP server, and has 8 test files.
- `gap_analyser.py`: Pydantic `ComplianceGap {gap_id, title, severity, new_requirement, existing_policy, suggested_action, deadline: str | None}` and `GapAnalysisResult`. The LLM (Groq) compares a new circular against retrieved policy chunks and must "respond with valid JSON only". The `deadline` is a free-text string extracted by the LLM, not a parsed date. — [gap_analyser.py](https://github.com/Manas-singh14/Regulatory-Change-Autopilot-AI-Powered-Compliance-Intelligence-System/blob/main/src/rag/gap_analyser.py)
- `extractor.py`: PyMuPDF text extraction with `[Page N]` markers and whitespace cleanup. This is reasonable boilerplate. — [extractor.py](https://github.com/Manas-singh14/Regulatory-Change-Autopilot-AI-Powered-Compliance-Intelligence-System/blob/main/src/watcher/extractor.py)

**Other RBI repos (metadata only, not read):** FinStack Loan-Origination-System-RBI-Master-Directions (10 stars), astuto-ai/cloud-custodian-rbi-security-pack (6 stars, Apache-2.0, AWS security policies for the RBI cyber framework; last push 2024-09), and pulkitdagur-auditar/IndiaAI-7Sutra-Traceability-Standard (5 stars, MIT, JSON Schema for RBI FREE-AI logging). — [GitHub search via gh CLI](https://github.com/search?q=RBI+compliance&type=repositories)

**CFPB complaint classification (comparison point): carmenwu0520/cfpb-complaint-nlp**, 1 star, last push 2026-09-26.
- On CFPB product classification it reports TF-IDF + LogReg at macro-F1 0.748, DistilBERT (44K rows) at 0.752, and Claude Haiku 4.5 at 0.676 to 0.685 across zero-shot, definitions and few-shot prompts on 500 rows, costing $0.33 to $0.98 per 1K. — [results_table.md](https://github.com/carmenwu0520/cfpb-complaint-nlp/blob/main/results_table.md)
- The notebook notes that richer prompts made the model verbose and "the parser picked wrong labels" (a "naive first-in-list label parser"). Output parsing, not model capability, drove part of the LLM's error. — [CFPB_NLP_OneClick.ipynb](https://github.com/carmenwu0520/cfpb-complaint-nlp/blob/main/CFPB_NLP_OneClick.ipynb)

### Inferences
- No open-source RBI complaint compliance engine exists to build on. CustomerPulse's 17-rule engine is already more complaint-specific than anything I found. The RBI repos are useful only for small pieces: the `RBI/YYYY-YY/NNN` circular-number regex, the `rule_reference` plus `reasoning` result fields from ComplyNext, and the Pydantic gap schema from Manas-singh14.
- Most RBI repos have no license, so their code cannot legally be copied. Only patterns can be borrowed.
- The CFPB result suggests a cheap TF-IDF/linear baseline is competitive with zero-shot LLMs for category triage. CustomerPulse should benchmark Bedrock against a linear baseline and use constrained output (enum or tool schema) to avoid the parsing failures seen there.

### Gaps
- I found no public dataset of real Indian bank complaint narratives. The rbi-ombudsman-analytics author states RBI does not publish narratives.
- No repo implements RBI's Integrated Ombudsman Scheme 2021 timelines or the failed-transaction TAT and compensation framework in code. I could not find one under any search term I tried ("banking ombudsman", "grievance redressal bank", "RBI master direction", "RBI guidelines").
- I did not read the other CFPB repos (all had 0 stars), and the `saketh97` LLM complaint repo failed to clone.

---

## Key Question 3: What components could CustomerPulse reuse directly (license-compatible) and which patterns should it copy?

### Takeaway
The directly reusable, permissively licensed pieces are `holidays` (MIT) for India working-day SLA clocks, Presidio (MIT) for Aadhaar and PAN masking before text goes to Bedrock, json-rules-engine (ISC) or Zen (MIT, with Python bindings) if a declarative rule format is wanted, and RAGAS or NeMo Guardrails for evaluation and guardrails. OpenFisca is AGPL-3.0, so copy its pattern rather than its code. The workalendar library has no India calendar and has been stale since 2024.

### Cited Findings

**holidays (vacanza)**: 1,948 stars, MIT, last push 2026-10-12.
- The `India` class has `start_year = 1948`. It defines 36 `subdivisions` for states and UTs, with aliases and deprecated codes, and categories `(GOVERNMENT, OPTIONAL, OPTIONAL_WOMEN, PUBLIC)`. It mixes in `HinduCalendarHolidays`, `IslamicHolidays` and `ChristianHolidays` for lunar festivals, with per-state methods such as `_populate_subdiv_gj_public_holidays`. The sources are archived state gazette PDFs. — [india.py](https://github.com/vacanza/holidays/blob/dev/holidays/countries/india.py)
- `HolidayBase` provides `is_working_day`, `get_nth_working_day(key, n)` and `get_working_days_count(start, end)`, and supports a configurable `weekend` (default `{SAT, SUN}`) and `weekend_workdays`. — [holiday_base.py](https://github.com/vacanza/holidays/blob/dev/holidays/holiday_base.py)
- There are financial calendars `national_stock_exchange_of_india.py` and `bombay_stock_exchange.py`, but no RBI/bank (Negotiable Instruments Act) holiday category. Indian banks' 2nd and 4th Saturday closures are not modelled by the default `{SAT, SUN}` weekend. — [holidays/financial](https://github.com/vacanza/holidays/tree/dev/holidays/financial), [india.py](https://github.com/vacanza/holidays/blob/dev/holidays/countries/india.py)

**workalendar**: 947 stars, MIT, last push 2024-04-12.
- `core.py` has a good API (`add_working_days`, `sub_working_days`, `get_working_days_delta`, `is_working_day`), but grepping the package for "india" only finds Singapore and US-Indiana files. It has no India calendar. — [core.py](https://github.com/workalendar/workalendar/blob/master/workalendar/core.py)

**Presidio**: 11,295 stars, MIT, repo now `data-privacy-stack/presidio`, last push 2026-10-09.
- The India recognisers are `in_aadhaar`, `in_pan`, `in_gstin`, `in_passport`, `in_vehicle_registration` and `in_voter`. `InAadhaarRecognizer` uses regexes `\b[0-9]{12}\b` and a 4-4-4 separated form, both at a base score of 0.01, and raises confidence through `validate_result`. That check requires 12 digits, a first digit of at least 2, a Verhoeff checksum (`_is_verhoeff_number`), and a non-palindromic number. Context words are "aadhaar" and "uidai". — [in_aadhaar_recognizer.py](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/india/in_aadhaar_recognizer.py)
- `InPanRecognizer` uses three regex `Pattern`s of differing strength plus a context word list. — [in_pan_recognizer.py](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/india/in_pan_recognizer.py)
- There is no Indian bank-account or IFSC or UPI-ID recogniser in the India folder (file listing via the GitHub tree API). Those would have to be added as custom `PatternRecognizer`s. — [india/](https://github.com/data-privacy-stack/presidio/tree/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/india)

**NeMo Guardrails**: 7,281 stars, GitHub license field NOASSERTION, last push 2026-10-10.
- `GenerationLogOptions.activated_rails` and `GenerationLog.activated_rails: List[ActivatedRail]` record which rails fired per response, which serves as an audit log for LLM outputs. `actions/` includes `llm_judge.py`, `rail_outcome.py` and `retrieve_relevant_chunks.py`. — [options.py](https://github.com/NVIDIA-NeMo/Guardrails/blob/develop/nemoguardrails/rails/llm/options.py)

**Guardrails AI**: 7,511 stars, Apache-2.0, last push 2026-10-09. Metadata only; I did not read its code. — [repo](https://github.com/guardrails-ai/guardrails)

**Rule engines (license check):** json-rules-engine is ISC, Zen MIT, Microsoft RulesEngine MIT (.NET, so a poor fit for FastAPI), durable_rules MIT, OPA Apache-2.0, Catala Apache-2.0, Blawx MIT, compliance-trestle Apache-2.0. OpenFisca is AGPL-3.0, so do not vendor it into a closed SaaS. — GitHub API metadata, [openfisca-core](https://github.com/openfisca/openfisca-core), [zen](https://github.com/gorules/zen), [json-rules-engine](https://github.com/CacheControl/json-rules-engine)

### Inferences
- **Reuse directly:**
  - `holidays.India(subdiv=<state>, categories=PUBLIC)` subclassed with a bank-specific weekend rule (2nd and 4th Saturdays) and an RBI/NI-Act holiday overlay, then `get_nth_working_day` to compute due dates.
  - Presidio's Aadhaar and PAN recognisers plus custom account-number, IFSC and UPI recognisers before Bedrock calls.
  - RAGAS for circular-RAG evaluation, using real retrieved contexts and avoiding ComplianceIQ's bug.
- **Copy these patterns:**
  1. OpenFisca-style dated parameter histories with reference metadata.
  2. A json-rules-engine or Zen-style per-condition trace (`fact`, `operator`, `expected`, `actual`, `result`) stored with each evaluation.
  3. A ComplyNext-style `rule_reference` and `reasoning` on every result.
  4. Catala-style explicit date rounding and a fixed evaluation instant.
  5. OSCAL-style obligation catalog: control, then params, then links to the circular.
  6. Zen's linter idea: statically validate `rules.json` (unknown condition types, overlapping effective periods) in CI.

### Gaps
- I did not verify whether `holidays` handles the RBI "bank holiday" list published per state under the NI Act. Its categories suggest it does not.
- I did not read Presidio's PAN regex values in full or test recall on real text.

---

## Key Question 4 (synthesis): What is missing across all of them?

### Takeaway
No project combines all four things an RBI complaint engine needs: dated, source-cited obligations; working-day deadline clocks on an Indian bank calendar; event-driven re-evaluation over a complaint's lifecycle; and auditable per-condition explanations. The rules-as-code tools cover dating and explanation but not calendars or complaint lifecycles. The RBI repos cover retrieval but not deterministic obligations.

### Cited Findings
- Effective dating exists only in OpenFisca (formula start dates, parameter histories, `end`) and conceptually in Catala exceptions. It is absent from json-rules-engine `Rule`, MS RulesEngine `Rule`, Zen and OPA. — [variable.py](https://github.com/openfisca/openfisca-core/blob/master/openfisca_core/variables/variable.py), [rule.js](https://github.com/CacheControl/json-rules-engine/blob/master/src/rule.js), [Rule.cs](https://github.com/microsoft/RulesEngine/blob/main/src/RulesEngine/Models/Rule.cs)
- No rule engine I read has business-day or holiday arithmetic. Zen has calendar date methods only, OPA has `add_date`, `diff` and `weekday`, and Blawx has `date_add` on timestamps. — [date_method.rs](https://github.com/gorules/zen/blob/master/core/expression/src/functions/date_method.rs), [time.go](https://github.com/open-policy-agent/opa/blob/main/v1/topdown/time.go), [dates.py](https://github.com/Lexpedite/blawx/blob/main/blawx/dates.py)
- Time-triggered re-evaluation exists only in durable_rules (`timeout`). Every other engine evaluates once per call. — [lang.py](https://github.com/jruizgit/rules/blob/master/libpy/durable/lang.py)
- The RBI repos handle supersession and deadlines with LLM free text: ComplianceIQ's `diff_excerpts` and Manas-singh14's `deadline: str | None`. — [generator.py](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/services/generator.py), [gap_analyser.py](https://github.com/Manas-singh14/Regulatory-Change-Autopilot-AI-Powered-Compliance-Intelligence-System/blob/main/src/rag/gap_analyser.py)
- Evaluation in the RBI repos is missing or invalid: placeholder golden sets, label-only RAGAS contexts, F1 = 1.0 on synthetic data, and print-only tests. — [run_eval.py](https://github.com/pavith-raj/ComplianceIQ/blob/main/backend/app/eval/run_eval.py), [metrics.json](https://github.com/Prasanthdj8/rbi-ombudsman-analytics/blob/main/classifier/metrics.json), [test_rag_questions.py](https://github.com/nithinraj49/banking-compliance-rag-chatbot/blob/main/test_rag_questions.py)

### Inferences
- CustomerPulse's differentiator is an engine that does all of the following:
  - Stores each obligation with `effective_from`, `effective_to`, `source_circular_no` (validated by the `RBI/YYYY-YY/NNN` regex), paragraph and URL.
  - Resolves parameters as of the complaint's received date.
  - Computes due dates with an India-state bank calendar built on `holidays`.
  - Re-evaluates on lifecycle events and on a scheduler tick, rather than once.
  - Persists a per-condition trace.
  - Has a gold test suite of complaint timelines with expected breach and no-breach outcomes, the kind of test discipline json-rules-engine and OpenFisca's YAML tests show.
- Replacing substring keyword matching with semantic or LLM signals should remain advisory. Deterministic date and threshold rules should stay in code, a design choice ComplyNext's `npa_engine.py` docstring argues explicitly.

### Gaps
- I could not assess FINOS DRR, Legend or LexNLP/Blackstone/LegalBench obligation-extraction code within the tool budget. Obligation extraction from RBI circulars therefore remains unreviewed.
- Promptfoo was not reviewed.
