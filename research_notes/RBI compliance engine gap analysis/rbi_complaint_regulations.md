# RBI Complaint / Grievance-Redress / Customer-Service Rules for Banks — Machine-Checkable Catalogue (state as of 12 Oct 2026)

Primary texts actually read in full for these notes (clause numbers below are taken directly from them):
- **RB-IOS 2026** full scheme text (bank-hosted copy of the RBI scheme): https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf (RBI's own PDF https://rbidocs.rbi.org.in/rdocs/content/pdfs/SCHEME16012026_A.pdf was behind a bot-check). The RBI FAQ is at https://www.rbi.org.in/commonperson/english/scripts/FAQs.aspx?Id=3407
- **RBI (Commercial Banks – Internal Ombudsman) Directions, 2026**, RBI/CEPD/2025-26/381, 14 Jan 2026 (copy hosted by SBI): https://sbi.bank.in/documents/53471/53742/11082026_Annexure+I-RBI+Commercial+Banks-Internal+Ombudsman+Directions+2026.pdf/7a497eab-60d3-155f-e5cd-357b80ebda24
- **RBI (Commercial Banks – Responsible Business Conduct) Directions, 2025**, RBI/DOR/2025-26/170, DOR.MCS.REC.No.89/01-01-032/2025-26, 28 Nov 2025, "Updated as on October 1, 2026": https://www.caalley.com/rbi_mc_md_25/md/170MD.pdf . Below this is cited as "RBC-CB".
- **Failed-transaction TAT circular**, RBI/2019-20/67, DPSS.CO.PD No.629/02.01.014/2019-20, 20 Sep 2019: https://www.rbi.org.in/commonman/English/scripts/Notification.aspx?Id=3074

---

## Q1. RB-IOS 2026 vs RB-IOS 2021: maintainability, wait period, filing window, compensation caps, RE duties, transition

### Takeaway
RB-IOS 2026 came into force on **1 July 2026** and repealed RB-IOS 2021 from that date. A complaint is routed to a scheme by **the date the Ombudsman/CRPC received it**: before 1 Jul 2026 means the 2021 scheme, including its appeals and award execution; on or after 1 Jul 2026 means the 2026 scheme. Under 2026, the RE gets **30 days** to reply, or the RBI/NPCI/card-network TAT if that is longer. The customer then has **90 days** to file, counted from that deadline or from the RE's last communication, whichever is later. The old 1-year window is gone. Caps are **₹30 lakh** for consequential loss plus **₹3 lakh** for time, expense and harassment. The RE has **15 days** to file its written response, and award acceptance, compliance and appeals each run **30 days**.

### Cited Findings
**Identity and transition**
- RB-IOS 2026 cl. 1(2): "shall come into force with effect from July 1, 2026." It is issued under BR Act s.35A, RBI Act s.45L, PSS Act s.18 and CICRA s.11. — [RB-IOS 2026 text](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)
- Cl. 20(1): RB-IOS 2021 "shall stand repealed as on July 01, 2026". Cl. 20(2): adjudication of complaints received under 2021 **before 1 Jul 2026**, appeals from those decisions, and execution of 2021 awards stay governed by RB-IOS 2021 and the instructions issued under it. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf); confirmed by [RBI FAQ Q1](https://www.rbi.org.in/commonperson/english/scripts/FAQs.aspx?Id=3407)
- The scheme was announced in January 2026; a draft (then called the "Reserve Bank Ombudsman Scheme 2025") came out earlier. The notification/circular number of the final scheme was **not found**: the FAQ gives none, and Vinod Kothari cites only press release prid=62052. — [Vinod Kothari](https://vinodkothari.com/2026/01/rbi-integrated-ombudsman-scheme-2026-key-changes/); [RBI draft](https://website.rbi.org.in/documents/87730/14317374/DraftReserveBankOmbudsmanScheme2025.pdf/695fcbaf-e9f7-0489-a97c-91d9b080a3fd)

**Coverage (cl. 1(3))**
- Covered: all Commercial Banks, RRBs, State Co-op Banks, Central Co-op Banks and Scheduled UCBs, plus non-scheduled UCBs with deposits of **₹50 crore or more** as on the previous FY's audited balance sheet. NBFCs are covered if they accept deposits, or have a customer interface and assets of **₹100 crore or more**. Excluded NBFCs: HFCs, CICs, IDF-NBFCs, NBFC-IFCs, NOFHCs, PDs and MGCs. Also covered: all non-bank PPI issuers and all Credit Information Companies. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)
- State and central co-operative banks were brought under the ombudsman scheme in October 2025, before RB-IOS 2026. — [Business Standard](https://www.business-standard.com/finance/news/central-state-co-op-banks-brought-under-ambit-of-rbi-s-ombudsman-scheme-125100701358_1.html)

**Definitions relevant to rules**
- Cl. 3(1)(c): "Authorised Representative" means a person *other than an advocate*. Cl. 3(1)(o): "Rejected Complaints" means complaints closed under cl. 16. Clause 3(1)(h)/(i) (customer; deficiency in service covering *all* services) is reported by Vinod Kothari. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf); [Vinod Kothari](https://vinodkothari.com/2026/01/rbi-integrated-ombudsman-scheme-2026-key-changes/)

**Maintainability, cl. 10(1). These are cumulative conditions an engine can check before advising escalation:**
- (a) Addressed to the RBI Ombudsman directly; a communication that merely copies RBI does not count.
- (b) Filed personally or through an authorised representative who is not an advocate (unless the advocate is the aggrieved person).
- (c) Complete information as per cl. 11 and the Annex form.
- (d) Not abusive, frivolous or vexatious.
- (e) **Complaint first made to the RE** in writing or another mode, *with proof*.
- (f) **No reply within 30 days, or within the RBI/NPCI/card-network specified time if any, whichever is higher**, after the RE received the complaint; OR the complainant is not satisfied with the reply.
- (g) **Filed within 90 days** from the date the (f) timeline expires, or from the date of the RE's last communication, whichever is later.
- (h)–(k) The same grievance is not pending or settled before the Ombudsman, or before a court, tribunal, arbitrator or quasi-judicial forum. Explanation 1: criminal proceedings and police investigations do not count.
- (l) The complaint to the RE was made within the Limitation Act, 1963 period.
- Source: [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)

**Exclusions, cl. 10(2)**
- Excluded: commercial judgment of the RE; vendor vs RE disputes; grievances against management or executives; RE action complying with judicial, statutory or law-enforcement orders; services outside RBI purview; disputes between REs; employee-employer disputes; matters with a remedy under CICRA s.18; customers of REs not covered by the scheme.
- Cl. 10(3): complaints that fail these tests are rejected at the outset.
- Cl. 12(1): portal complaints go through system-based validation and can be rejected at the outset. Cl. 12(2)–(3): CRPC screens email and physical complaints, and treats suggestions and queries as "not valid complaint". — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)

**Compensation, cl. 8(3)**
- There is no limit on the amount in dispute. Consequential loss is capped at **₹30 lakh**. Loss of time, expenses and harassment/mental anguish is capped at **₹3 lakh**, payable in addition. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)
- Under 2021 the caps were ₹20 lakh and ₹1 lakh. — [Vinod Kothari comparison table](https://vinodkothari.com/2026/01/rbi-integrated-ombudsman-scheme-2026-key-changes/)

**Filing window, 2021 vs 2026**
- 2021: within **1 year** of receiving the RE's reply, or **1 year + 30 days** from the complaint date if no reply was received.
- 2026 (para 10(1)(g)): **90 days**, as above. — [Vinod Kothari](https://vinodkothari.com/2026/01/rbi-integrated-ombudsman-scheme-2026-key-changes/); [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)

**Procedure and timelines binding the RE (rule-encodable)**
- Cl. 13(1): the Ombudsman forwards the complaint copy to the RE with a direction to respond. Cl. 13(2): if the RE fails to furnish requested information "without sufficient cause", it is deemed to have none.
- Cl. 14(2): **the RE must file its written response, with copies of the documents it relies on, within 15 days.** The Ombudsman may grant more time on a written request.
- Cl. 14(3): if the RE does not file, the Ombudsman may proceed **ex-parte and issue an Award**.
- Cl. 14(6): the Ombudsman may issue an advisory at any stage. If the RE complies within the stipulated time and the complainant accepts, the complaint is closed under 14(8)(b).
- Cl. 14(7): conciliation meeting, in person or online, held in the Ombudsman's presence.
- Cl. 14(8)(a)–(e): closure grounds are settled; complainant satisfied; withdrawn; objection without merit; or partly addressed with the remainder outside scope or not a deficiency. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)
- Cl. 15: an Award is passed (a) where the RE did not furnish documents, or (b) where the complaint is not resolved under 14(8), after a hearing.
  - 15(4): the Award **lapses** unless the complainant sends an acceptance letter to the RE **within 30 days** of receiving it.
  - 15(5): **the RE must comply and intimate compliance to the Ombudsman, or appeal, within 30 days of receiving the acceptance letter.** — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)
- Cl. 16: rejection grounds.
  - 16(1): non-maintainable; not a valid complaint; same cause filed in court during examination.
  - 16(2): no deficiency; compensation sought beyond the 8(3) caps; not pursued with diligence; without sufficient cause; requires elaborate evidence; no loss or inconvenience. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)
- Cl. 17: appeals.
  - The RE has **no appeal** against a 15(1)(a) award (one passed for non-furnishing of documents).
  - RE appeal against a 15(1)(b) award: within **30 days** of the acceptance letter, with prior sanction of an ED or equal-rank official. The Appellate Authority may allow **up to 30 more days**.
  - Complainant appeal: within **30 days** of receiving the award, plus up to 30 days more.
  - The Appellate Authority is the ED-in-charge of CEPD. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf)

**RE display and PNO obligations, cl. 18 (all checkable)**
- 18(2): the RE must appoint a **Principal Nodal Officer** at head office, of rank **not less than General Manager** or equivalent. Changes in the appointment or contact details must be reported to CEPD, Central Office, RBI **before the change**, or immediately after it in an exigency. (The 2021 scheme had no reporting obligation, per Vinod Kothari.)
- 18(3): display at branches the PNO's name, phone/mobile and email, and the CRPC address. The website must link to https://cms.rbi.org.in.
- 18(4): display the scheme's salient features in **English, Hindi and the regional language** at all offices and branches.
- 18(5): keep a copy of the scheme at every branch, to be given on request.
- 18(6): keep the salient features, the scheme copy and the PNO details on the website, updated. — [RB-IOS 2026](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf); [Vinod Kothari](https://vinodkothari.com/2026/01/rbi-integrated-ombudsman-scheme-2026-key-changes/)

**Filing channels and fees**
- Filing is via the CMS portal, crpc@rbi.org.in, or post to the CRPC, 4th Floor, RBI, Sector 17, Central Vista, Chandigarh 160017. There is no fee. Contact Centre: 14448. — [RB-IOS 2026 cl. 6, 11](https://av.sc.com/in/content/docs/in-integrated-ombudsman-scheme.pdf); [RBI FAQ Q7–Q11, Q21](https://www.rbi.org.in/commonperson/english/scripts/FAQs.aspx?Id=3407)

### Inferences
- Engine rule `IOS_ELIGIBLE_DATE(complaint)`: deadline = max(RE_receipt + 30 calendar days, RE_receipt + external TAT) or last_RE_communication, whichever is later; filing deadline = that date + 90 days. The scheme says "days" without qualifying it. Treat this as calendar days; the TAT and IO texts use "days" the same way.
- Engine rule `SCHEME_VERSION`: use the date RBI received the complaint (≥ 2026-07-01 means 2026). If the complaint reached the RE in 2025 but was filed with RBI after 30 Jun 2026, the 2026 90-day window applies. Such complaints may already be time-barred under 2026 even though the 2021 1-year window would have allowed them. This is an inference from cl. 20(2), which keys on "received before July 01, 2026".
- Bank-side internal SLA for Ombudsman complaints: 15 days for the written response; 30 days for award compliance from the acceptance letter; 30 (+30) days for an appeal, which needs ED sanction.
- RB-IOS 2026 itself does **not** contain the 2021-era requirement that the RE's final reply tell the customer about the Ombudsman. That requirement now sits in IO Directions 14(12) and in sectoral rules such as the notice-board format (see Q2/Q3).

### Gaps
- The notification/circular number and date of the final RB-IOS 2026 were not found.
- The Annex complaint form fields are summarised in RBI FAQ Q18 but were not read verbatim.
- The 2021 scheme text was not re-read here. The 2021 comparators (₹20 lakh/₹1 lakh caps, 1-year window, 15-day written version) come from the Vinod Kothari comparison and my background knowledge of the 2021 scheme.

---

## Q2. Internal Ombudsman (IO) Directions 2026 (repealing MD-IO 2023): auto-escalation, final decision timeline, exclusions, classification, compensation

### Takeaway
For commercial banks with **10 or more banking outlets** (as on 31 Mar 2025), the bank must auto-escalate every partially resolved or wholly rejected complaint to the IO **within 20 days of receipt**. Where an RBI, NPCI or card-network TAT applies, escalation must come early enough to give the IO **at least 10 days** before that TAT. The final decision must reach the complainant **within 30 days of the bank receiving the complaint**. The CMS may record only three outcomes: Fully Resolved, Partially Resolved, Wholly Rejected. The reply must state that the IO reviewed the complaint and give the RB-IOS escalation details, including the CMS URL and the CRPC address. The IO can now recommend compensation, including RB-IOS-type compensation.

### Cited Findings
- **Instrument:** RBI/CEPD/2025-26/381, CEPD.PRD.No.S1027/13.01.019/2025-26, dated **14 Jan 2026**, issued under BR Act s.35A. **Cl. 1(2):** in force immediately, except cl. **7(2), 14(2) and 14(4)**, which had to be complied with by **30 Jun 2026**. **Cl. 17:** repeals the *Master Direction – RBI (Internal Ombudsman for Regulated Entities) Directions, 2023* dated **29 Dec 2023**. — [IO Directions (SBI copy)](https://sbi.bank.in/documents/53471/53742/11082026_Annexure+I-RBI+Commercial+Banks-Internal+Ombudsman+Directions+2026.pdf/7a497eab-60d3-155f-e5cd-357b80ebda24)
- RBI issued separate, harmonised directions for commercial banks, SFBs, payments banks, NBFCs, non-bank PPI issuers and CICs on 14 Jan 2026, following a draft dated 7 Oct 2025. IOs are no longer required in RRBs and co-operative banks. — [Taxmann](https://www.taxmann.com/post/blog/rbi-strengthens-grievance-redressal-via-internal-ombudsman); [Outlook Money](https://www.outlookmoney.com/banking/rbi-issues-new-internal-ombudsman-directions-for-banks-and-nbfcs); [RBI draft](https://website.rbi.org.in/documents/d/rbi/draftmd_rbiinternalombudsmanforregulatedentitiesdirections2025_c2r)
- **Applicability (cl. 3):**
  - Commercial banks with **10 or more banking outlets in India as on 31 Mar 2025**. This excludes SFBs, PBs, LABs, and banks in resolution, winding-up or under directions.
  - A bank crossing the threshold later becomes subject **6 months after** meeting the criteria.
  - Cl. 4(1)(c): a "Complaint" is a representation alleging deficiency in service **with or without seeking relief**. — [IO Directions](https://sbi.bank.in/documents/53471/53742/11082026_Annexure+I-RBI+Commercial+Banks-Internal+Ombudsman+Directions+2026.pdf/7a497eab-60d3-155f-e5cd-357b80ebda24)
- **Auto-escalation (cl. 14(1)):** a "fully automated Complaints Management System" is mandatory. All partially resolved or wholly rejected complaints are auto-escalated to the IO:
  - (a) Where an RBI, NPCI or card-network timeline exists: "sufficiently in advance such that IO / Dy. IO gets **at least 10 days** for review", so the final decision can be communicated within that TAT.
  - (b) In all other cases: "**within 20 days of receipt**". — [IO Directions](https://sbi.bank.in/documents/53471/53742/11082026_Annexure+I-RBI+Commercial+Banks-Internal+Ombudsman+Directions+2026.pdf/7a497eab-60d3-155f-e5cd-357b80ebda24)
- **Classification (cl. 14(2), by 30 Jun 2026):** the CMS must provide **only three categories**: "Fully Resolved", "Partially Resolved", "Wholly Rejected". Complaints outside IO purview under 14(5)(c)–(e) are exempt from this classification. — same
- **Cl. 14(3):** a Standard Operating Procedure is required for the time-bound flow of complaints. **Cl. 14(4) (by 30 Jun 2026):** a complaint must **not be closed by the same branch, unit or touch point** where it was handled. Partially resolved or rejected complaints must be reviewed "at a fairly senior level" before going to the IO. — same
- **Exclusions (cl. 14(5)):**
  - (a) Corporate frauds or misappropriation that do not affect the customer.
  - (b) Suggestions and commercial decisions. Service deficiencies within commercial decisions *are* valid.
  - (c) Internal administration, HR, staff pay.
  - (d) Matters decided or pending in courts, consumer commissions, arbitration and similar fora.
  - (e) Disputes with a remedy under CICRA s.18.
  - Rejected or partially resolved complaints in categories (a) and (b) must still be forwarded to the IO, who decides whether the exemption applies. Out-of-purview complaints are returned to the bank immediately. — same
- **Final decision and communication content:**
  - **14(9):** "the final decision is communicated to the complainant within a period of **30 days from the date of receipt of complaint by the bank**."
  - **14(10):** the IO records a "reasoned decision".
  - **14(11):** where the IO upholds a rejection or partial resolution, the reply must "explicitly state that the said complaint has been reviewed by the IO / Dy. IO".
  - **14(12):** for complaints partially resolved or rejected after IO review, the bank must advise the option to approach the **RBI Ombudsman** (except complaints not covered by RB-IOS), "along with complete details of the complaint". It must also give the **CMS URL https://cms.rbi.org.in** and the **CRPC physical/email address** (CRPC, RBI, Central Vista, Sector 17, Chandigarh 160017; crpc@rbi.org.in). — same
- **14(13):** when a complaint is escalated to the RBI Ombudsman, the IO decision must be included in the bank's submission. If the IO had not reviewed it, the bank must obtain the IO's comments and submit them. **14(17):** IO contact details must **not** be published, because the IO does not take direct complaints (cl. 12(1)). — same
- **Compensation:**
  - **12(4):** the IO recommends compensation per RBI's prescribed compensation (for example the TAT and limited-liability rules), or per the bank's compensation policy where RBI prescribes none.
  - **12(5):** the IO may *additionally* recommend compensation per RB-IOS for consequential loss and for time, expenses and harassment. That makes the RB-IOS 2026 caps (₹30 lakh / ₹3 lakh) the implied ceiling. — same
- **Governance:**
  - **13(3)–(4):** an IO decision can be overruled only with approval of the Competent Authority (WTD/ED in charge of customer service). Every overruled case goes to the Customer Service Committee of the Board (CSCB).
  - **13(2):** IO reports to the CSCB at least half-yearly, preferably quarterly.
  - **13(5):** RBI-Ombudsman decisions in the complainant's favour are placed before the CSCB **quarterly**, with analysis of at least the **top 5 complaint categories**.
  - **12(6):** the IO analyses complaint patterns quarterly. **12(8):** the IO gets read-only access to RBI CMS.
  - **11:** annual internal audit, including timeliness of auto-escalation. — same
- **Staffing and tenure:**
  - IO: GM-equivalent with at least 7 years' experience. Dy. IO: DGM-equivalent with at least 5 years. Not over 70 at end of tenure. Not ex-employees of the bank or its group.
  - Tenure at least 3 years, at most 5 years in total (cl. 8(4)).
  - The bank must start a replacement **3 months before** tenure expiry (8(5)).
  - An unforeseen vacancy is reported to RBI within **10 working days**, and filled within **3 months** (8(6)).
  - If both IO and Dy. IO are absent, a temporary GM-rank designate may act for up to **1 month** (8(3)).
  - CSCB reviews the number of IOs **annually** (7(2), by 30 Jun 2026). — same
- **Reporting (cl. 16):**
  - IO or Dy. IO appointment details go to CEPD (iocepd@rbi.org.in) within **5 working days**.
  - Quarterly report in the Annex format is due by the **15th of the month after the quarter**. Annex rows include complaints referred to the IO within 20 days vs after 20 days, and those referred after 20 days because of an RBI/NPCI/card TAT, among others. — same

### Inferences
- Engine rules: `IO_ESCALATION_DUE = receipt + 20d` (calendar days; the text says "days"); for TAT-governed complaints, `IO_ESCALATION_DUE = external_TAT_deadline − 10d`; `FINAL_REPLY_DUE = receipt + 30d`; `REPLY_MUST_CONTAIN = {IO-reviewed statement (if upheld), RB-IOS option, cms.rbi.org.in, CRPC address}` whenever outcome ∈ {Partially Resolved, Wholly Rejected}.
- The 20/30-day scheme leaves at most about 10 days for IO review in ordinary cases.
- The 25-day CIC escalation figure mentioned in the brief appears in the separate CIC IO direction (and the earlier 2023 MD). I did not read the CIC/NBFC versions, so it is unverified here.

### Gaps
- The NBFC, SFB, PB, PPI and CIC versions of the IO Directions 2026 were not read. Their thresholds (for example NBFC branch/asset criteria) and any CIC-specific day counts (the brief's "25 days") are unverified.
- The 2023 MD's clause numbering was not compared line by line. The 20/30-day and 10-day structure is understood to carry over from 2023, but this is not verified here.

---

## Q3. Customer-service consolidation (Nov 2025 Master Directions), withdrawal of the 2021 grievance circular (RBI/2025-26/207), and complaint disclosures

### Takeaway
On 28 Nov 2025 RBI consolidated about 9,000 circulars into 244 entity-wise Master Directions on an "as-is" basis. For commercial banks, customer-service, grievance, limited-liability, deceased-claim, locker, property-document and recovery-agent rules now sit in the **RBI (Commercial Banks – Responsible Business Conduct) Directions, 2025** (RBC-CB). The copy read here is "updated as on 1 Oct 2026". On **11 Feb 2026**, RBI/2025-26/207 withdrew the **27 Jan 2021** "Strengthening of grievance redress mechanism in banks" circular with immediate effect. RBI cited duplication with the Financial Statements MD complaint disclosures (28 Nov 2025), RB-IOS 2026 and the IO Directions 2026.

### Cited Findings
- **RBC-CB identity:**
  - RBI/DOR/2025-26/170, DOR.MCS.REC.No.89/01-01-032/2025-26, 28 Nov 2025, "Updated as on October 1, 2026".
  - Para 464: repeals the earlier Responsible Business Conduct instructions for commercial banks "as communicated vide circular DOR.RRC.REC.302/33-01-010/2025-26 dated November 28, 2025".
  - Para 465: savings clause; actions taken under repealed instructions stay governed by them.
  - Several paras carry footnotes "Substituted with effect from October 1, 2026, consequent to RBI (Commercial Banks – Governance) Amendment Directions, 2026 dated July 14, 2026". These replace "Board" with "Board or a Committee to which powers have been delegated". — [RBC-CB](https://www.caalley.com/rbi_mc_md_25/md/170MD.pdf)
- About 244 MDs were issued and roughly 9,445 circulars repealed on 28 Nov 2025, on an "as-is" basis. — [SNG & Partners](https://sngpartners.in/2025/12/04/rbi-rolls-out-consolidated-master-directions/); [Finakon](https://finakon.in/regulatory-update-november26-dec5/)
- **Board-approved policies required (RBC-CB para 5(1)):** customer relations policy (covering customer liability for reporting delays beyond 7 days in unauthorised e-banking); locker policy and SOP; cheque collection policy; doorstep banking policy for senior citizens and differently-abled persons; **customer compensation policy**; policy on settlement of claims; and others. **Para 6:** review of customer service **once in 6 months**; review of customer-liability cases; review of FPC compliance and grievance-mechanism functioning. — [RBC-CB](https://www.caalley.com/rbi_mc_md_25/md/170MD.pdf)
- **Customer Compensation Policy (para 11):** must at minimum cover erroneous debits from fraudulent or other transactions; interest for delayed collection; interest for delay in issuing duplicate drafts; and other unauthorised bank actions causing financial loss. **Para 12:** policies go on the website and the branch notice board, and customers are told of changes. — same
- **Committees:**
  - **Para 13–14:** a Customer Service Committee of the Board, with experts and customer representatives as invitees. Its remit includes an annual depositor-satisfaction survey and a triennial audit of services.
  - **Para 15:** a memorandum on customer service goes to the Board **every 6 months**.
  - **Para 16–17:** a Standing Committee on Customer Service, chaired by the CMD/CEO/ED.
  - **Para 18–20:** branch-level Customer Service Committees that include senior citizens. They **meet at least monthly** to study complaints and report **quarterly** to the Standing Committee. — same
- **Display and website:**
  - **Para 48–49:** a comprehensive notice board, bilingual in Hindi states and trilingual elsewhere, with recent changes flagged. Branch name, working days and hours are displayed outside.
  - **Para 54(2):** the website must carry the grievance redressal mechanism, **information on RB-IOS 2026**, and customer service centres (PSBs).
  - **Annex I §C:** the notice-board format must give a branch contact for grievances, then the Regional/Zonal/HO address if unresolved, then the "Ombudsman" name, address, phone and email.
  - **Annex I §E:** booklets must include the grievance redressal policy and the compensation policy. — same
- **Unauthorised-transaction complaint intake (para 66):**
  - SMS alerts are mandatory.
  - 24x7 reporting through multiple channels, including a dedicated toll-free helpline.
  - Customers can "Reply" to alert SMS and email.
  - A direct link to report unauthorised e-transactions on the website **home page**.
  - An **immediate acknowledgement (auto-response) with a registered complaint number**.
  - Date and time stamps of alert delivery and customer response must be recorded.
  - No e-transactions other than ATM withdrawals for customers without a mobile number. — same
- **Lending grievance (para 346):** the board lays down a grievance mechanism ensuring disputes over decisions by bank functionaries are "heard and disposed of at least at the next higher level", with periodic review. **KFS Annex XIII Part 2 item 3:** the KFS must give the phone and email of the nodal grievance redressal officer. A generic email is allowed "provided a response is made within **1 working day**". — same
- **RBI/2025-26/207:**
  - CO.CEPD.PRS.No.S1121/13-01-008/2025-2026, dated **11 Feb 2026**. It withdraws the 27 Jan 2021 circular "Strengthening of grievance redress mechanism in banks".
  - Reasons: subsequent developments; complaint disclosures now under the MD on Financial Statements: Presentation and Disclosures (28 Nov 2025); higher compensation under RB-IOS 2026; IO power to recommend compensation under the IO Directions 2026.
  - Banks' obligation to keep an effective grievance mechanism continues. — [Taxmann](https://www.taxmann.com/post/blog/rbi-withdraws-circular-on-bank-grievance-redress-mechanism); [JHS & Associates](https://jhsassociates.in/resources/rbi-withdraws-2021-grievance-redress-circular-for-banks/); [TeamLease RegTech](https://www.teamleaseregtech.com/updates/article/52617/rbi-strengthening-of-grievance-redress-mechanism-in-banks-review/)
  - JHS cites the withdrawn circular as RBI/2020-21/87. Other sources give only the date. — [JHS](https://jhsassociates.in/resources/rbi-withdraws-2021-grievance-redress-circular-for-banks/)

### Inferences
- The 2021 circular's cost-recovery mechanism (banks charged for maintainable complaints above peer-group median levels) and its "intensive review" framework appear to have ceased with the withdrawal. Disclosures move to the annual financial statements. An engine should drop any "2021 circular" disclosure rules and map disclosure rules to the Financial Statements MD instead.
- RBC-CB contains **no generic complaint acknowledgement or resolution TAT** for all complaints. The only explicit acknowledgement requirement is for unauthorised-transaction reports (para 66). The generic 30-day clock comes from RB-IOS cl. 10(1)(f) and IO cl. 14(9).
- RBC-CB does not mention a "Grievance Redressal Policy". The grievance mechanism is required through the RB-IOS PNO, the IO, the notice board and para 346. Banks still publish board-approved Grievance Redressal Policies, for example [Union Bank 2025-26](https://www.unionbankofindia.bank.in/pdf/grievance-redressal-and-customer-relations-policy-2025-26.pdf) and [IOB](https://www.iob.bank.in/documents/20117/74499/grievance-redressal-policy-2nd-annual-review.pdf/bef3b4d3-019a-96a0-f70b-02000e94a3c7?t=1773839178426).

### Gaps
- **The exact complaint-disclosure table in the MD on Financial Statements: Presentation and Disclosures (28 Nov 2025) was not retrieved.** Items such as complaints pending at start and end, received, disposed, maintainable complaints from the Ombudsman, top-5 grounds, and awards unimplemented are known from the 2021 circular format. Whether they carry over unchanged is unverified.
- The text of RBI/2025-26/207 itself was not read; details are from summaries.
- I did not confirm whether a separate consolidated direction (for example a "Customer Service" MD, or the PPI/Cards MDs) holds a generic complaint register or acknowledgement rule.

---

## Q4. Harmonised TAT and compensation for failed transactions (20 Sep 2019)

### Takeaway
RBI/2019-20/67 (effective **15 Oct 2019**) remains the reference. T is the transaction date, reversal must be completed by T+1 or T+5 depending on the channel, and **₹100 per day** of delay is payable **suo motu** with no complaint needed. I found no source confirming a later RBI change to the table. Whether it was carried into a Nov 2025 consolidated payment-systems direction is unverified; RB-IOS cl. 10(1)(f) and IO cl. 14(1)(a) both still refer to "timelines specified by RBI/NPCI/card networks".

### Cited Findings
- **Instrument:** RBI/2019-20/67, DPSS.CO.PD No.629/02.01.014/2019-20, 20 Sep 2019, under PSS Act s.10(2) read with s.18. Effective **15 Oct 2019**. — [RBI](https://www.rbi.org.in/commonman/English/scripts/Notification.aspx?Id=3074)
- **Principles:**
  - **T** = day of transaction, a calendar date. **R** = day the reversal is concluded and funds received by the issuer; the reversal must be posted the same day.
  - The TAT is the *outer* limit.
  - Compensation is credited "without waiting for a complaint or claim".
  - Credit-push failures carry a penalty payable to the beneficiary if credit is delayed. If the originator's bank delays initiation, the penalty goes to the originator.
  - Only domestic transactions are covered. "Bank" includes authorised non-banks.
  - A customer not redressed within the TAT may complain under RB-IOS. — [RBI](https://www.rbi.org.in/commonman/English/scripts/Notification.aspx?Id=3074)
- **Annex table (from the RBI page):**
  - ATM/Micro-ATM, account debited but cash not dispensed: **T+5**, ₹100/day.
  - Card-to-card transfer, not credited: **T+1**, ₹100/day.
  - PoS (card present), no charge slip: **T+5**, ₹100/day.
  - IMPS, beneficiary not credited: **T+1**, ₹100/day.
  - UPI P2P, not credited: **T+1**, ₹100/day.
  - UPI merchant, no confirmation: **T+5**, ₹100/day.
  - AePS merchant, no confirmation: **T+5**, ₹100/day.
  - APBS delayed credit: **T+1**, ₹100/day.
  - NACH delayed credit or reversal: **T+1**, ₹100/day.
  - NACH debit despite mandate revocation: the customer's bank is liable; resolve by **T+1**.
  - PPI off-us: follows the underlying system. PPI on-us: **T+1**, ₹100/day. — [RBI](https://www.rbi.org.in/commonman/English/scripts/Notification.aspx?Id=3074)
  - Rows **2c (Card-Not-Present/e-commerce)**, **5b (AePS, beneficiary not credited)** and the compensation for **7b** were illegible in my fetch. From background knowledge they are: CNP T+5 and ₹100/day; AePS-beneficiary T+1 and ₹100/day; NACH-revoked ₹100/day beyond T+1. **These three values are unverified in this session.**
- Business Standard (2019) reported ATM T+5 and ₹100/day and the automatic credit. — [Business Standard](https://www.business-standard.com/amp/article/finance/rbi-tightens-norms-for-banks-up-penalties-for-failed-atm-transactions-119092001334_1.html)
- NPCI implemented this for IMPS/UPI via circular IMPS/UPI OC-93 FY19-20. — [NPCI](https://www.npci.org.in/PDF/npci/imps/circular/2019/IMPS-UPI-I-OC-93-I-FY-19-20-I-Harmonisation-of-Turn-Around-Time(TAT)-and-customer-compensation-for-failed-transaction.pdf)
- A Scribd document claims a 2020 circular changed the time unit to *working* days from 1 Jan 2021. **Treat as unverified/suspect:** the RBI page itself defines T as a calendar date. — [Scribd](https://www.scribd.com/document/728951908/LRB210722-2)

### Inferences
- Engine rule: `FAILED_TXN_COMP = 100 × max(0, R_date − (T + n))` in calendar days, auto-credited. For credit-push failures the payee is the beneficiary; for delayed initiation it is the originator.
- Combined with IO cl. 14(1)(a), the bank must route rejected failed-transaction disputes to the IO at least 10 days before the external deadline.

### Gaps
- Whether the 2019 circular now sits in a Nov 2025 consolidated direction, or was repealed and restated, was not confirmed.
- Values in rows 2c, 5b and 7b are unverified. A possible 2020 working-day amendment is unverified.

---

## Q5. Limiting customer liability in unauthorised electronic banking transactions (6 Jul 2017; now RBC-CB paras 64–76)

### Takeaway
The 2017 framework (DBR circular, 6 Jul 2017) is carried essentially verbatim into RBC-CB Section D, paras 64–76.
- **Zero liability** if bank fault, or if a third-party breach is reported within **3 working days**.
- Liability **capped at ₹5,000, ₹10,000 or ₹25,000** (or the transaction value, if lower) if reported within **4–7 working days**.
- **Board policy** governs reporting beyond 7 working days.
- **Shadow credit within 10 working days** of notification, value-dated.
- **Resolution and liability determination within 90 days**; if not done, compensation is paid.
- The burden of proof is on the bank.

### Cited Findings
- **Para 67:** zero liability for (1) contributory fraud, negligence or deficiency by the bank, whether reported or not; (2) third-party breach reported **within 3 working days** of receiving the bank's communication. — [RBC-CB](https://www.caalley.com/rbi_mc_md_25/md/170MD.pdf)
- **Para 68(1):** where the customer was negligent (shared credentials), the customer bears the full loss until reporting. The bank bears losses after reporting. **68(2):** third-party breach reported in **4–7 working days**: liability is the lower of the transaction value and the Table 1 cap. — same
- **Table 1 (para 68(2)):**
  - **₹5,000:** BSBD accounts.
  - **₹10,000:** all other SB accounts; PPIs and gift cards; MSME current/CC/OD accounts; individuals' current/CC/OD with annual average balance or limit up to ₹25 lakh; credit cards with limit up to ₹5 lakh.
  - **₹25,000:** all other current/CC/OD accounts; credit cards with limit above ₹5 lakh. — same
- **Para 69:** reporting delayed beyond 7 working days falls under the Board (or delegated committee) approved policy. The policy is given at account opening, displayed publicly, and existing customers are informed individually. **Para 70, Table 2:** the summary table. **Para 71:** working days are counted per the **home branch's working schedule, excluding the day the communication was received**. — same
- **Para 72:** the bank must credit (shadow reversal) the amount **within 10 working days** of notification, without waiting for any insurance claim, **value-dated to the date of the unauthorised transaction**. — same
- **Para 73:**
  - (1) Resolve and establish liability within the time in the board policy, but **not exceeding 90 days** from receipt of complaint.
  - (2) If the bank cannot resolve within 90 days, it pays the compensation under paras 67–72.
  - (3) No loss of interest (debit card or account); no extra interest burden (credit card). — same
- **Para 74:** the customer relations policy must state compensation mechanisms and timelines, and be on the website with the grievance escalation procedure. **Para 75:** **burden of proof lies on the bank**. **Para 76:** customer-liability cases are reported to the Board or a committee by volume, value and category (CP/CNP/IB/MB/ATM), and reviewed by internal auditors. — same
- **Para 63:** for erroneous debits from fraud, the bank pays at once where staff fraud is evident. It compensates "without demur" where at fault, and compensates up to a policy limit where the fault lies elsewhere in the system. — same

### Inferences
- Engine rules: `REPORT_DELAY_WD = working_days(home_branch_calendar, comm_received_date+1 … report_date)`; `LIABILITY = 0 if bank_fault or delay ≤ 3; min(txn, cap[account_type]) if 4 ≤ delay ≤ 7; policy if delay > 7`; `SHADOW_CREDIT_DUE = notify + 10 WD`; `LIABILITY_DETERMINATION_DUE = receipt + 90 calendar days`, with breach meaning automatic compensation.
- Equivalents for others, from background knowledge and not re-verified this session: co-operative banks under the 14 Dec 2017 circular (same structure); RRBs; non-bank PPIs under the PPI Master Direction (2021) Annex. A similar 3/4–7 working-day framework applies to PPIs, with a 10-day credit and 90-day resolution. NBFC equivalents are mostly not prescribed.

### Gaps
- I found no 2024–2026 *substantive* revision of the caps or timelines. The only change seen is the Governance Amendment Directions (14 Jul 2026, effective 1 Oct 2026), which let a Board committee approve the policy.
- The NBFC, co-op, RRB and PPI consolidated equivalents were not read.

---

## Q6. Other numeric complaint-related obligations (CIC compensation, digital lending, recovery, deceased claims, locker, property documents, cards, nomination, DD, etc.)

### Takeaway
Many fixed TATs and compensation formulas exist outside the Ombudsman framework. Those verified in primary text (RBC-CB) are:
- Deceased-claim settlement **15 calendar days**; delay attracts Bank Rate + 4% interest (deposits) or **₹5,000/day** (lockers).
- Original property documents released **within 30 days** of closure, else **₹5,000/day** (60 days if documents are lost).
- Gold/silver collateral returned within **7 working days**.
- Nomination acknowledgement or rejection within **3 working days**.
- Duplicate DD within a **fortnight**.
- Inoperative-account activation within **3 working days**.
- Takeover consent within **21 days**.
- No referral to recovery agents while a complaint is pending.

From secondary sources: credit-information complaints get **₹100 per calendar day after 30 days**; credit-card closure within **7 working days**, else **₹500/day**.

### Cited Findings (RBC-CB, primary)
- **Deceased depositors:**
  - Para 317: acknowledge claims and list missing documents.
  - **Para 319:** settle deposit claims within **15 calendar days** of receiving all documents.
  - **Para 320:** for lockers and safe custody, process within **15 calendar days** and fix the inventory date.
  - **Para 321:** on delay, give reasons. If the delay is the bank's fault, pay interest at **at least Bank Rate + 4% p.a.** on the amount for the delay period, reckoned from the date all documents were received.
  - **Para 322:** for locker/safe-custody delays, **₹5,000 per day**. — [RBC-CB](https://www.caalley.com/rbi_mc_md_25/md/170MD.pdf)
- **Property documents:**
  - **Para 354:** release all original documents and remove registered charges **within 30 days** of full repayment.
  - **Para 356:** the timeline and place must be in sanction letters issued on or after 1 Dec 2023.
  - **Para 358:** on delay, communicate reasons. If the delay is the bank's fault, **₹5,000 per day**.
  - **Para 359:** for loss or damage, the bank bears the cost of duplicates and gets an extra 30 days, so the penalty runs after **60 days**.
  - **Para 360:** applies where release falls due on or after **1 Dec 2023**. — same
- **Gold/silver loans:**
  - **Para 377:** release collateral the same day, at most **7 working days** after repayment.
  - **Para 379:** auction only after notice; if the borrower is untraceable, **one month** after a public notice.
  - **Para 382:** reserve price at least **90%** of current value (**85%** after two failed auctions).
  - **Para 385:** refund any surplus within **7 working days** of receiving the auction proceeds.
  - **Paras 386–389:** compensation for damage or loss. — same
- **Nomination:** **para 275:** acknowledge registration, cancellation or variation of a nomination within **3 working days**, even if not requested. **Para 276:** reject in writing with reasons within **3 working days**. — same
- **Inoperative and unclaimed accounts:** **para 207:** process activation within **3 working days** of a complete application, and send SMS/email intimation of the status change including how to report unauthorised access. — same
- **Duplicate DD:** **para 129:** issue within **a fortnight**; for delay, interest at the term-deposit rate for the corresponding maturity. **Para 128:** a duplicate up to ₹5,000 may be issued on indemnity alone. — same
- **Cheque collection:** **paras 132–133:** the policy must specify interest for delayed collection, **paid without any claim from the customer**. — same
- **Loan takeover:** **para 344:** convey consent or objection to transfer of a loan account **within 21 days**. **Para 343:** no harassment at odd hours. — same
- **Recovery agents:**
  - **Para 448(6)** (numbering approximate; it is in Section K): the bank must not refer a case to a recovery agency while the borrower's grievance is pending, unless the bank has proof of frivolous or vexatious complaints. Caution is needed if the matter is sub judice.
  - **(7):** a mechanism for recovery-related grievances, with details given to the borrower.
  - **Paras 452–453:** the bank is liable as principal. RBI may ban recovery-agent use in an area. — same
- **Lockers:** **para 256:** a board policy on liability for loss from the bank's negligence. (The 100× annual-rent liability cap from the 2021 locker circular is at para C.8; the exact para was not extracted.) — same
- **KFS:** loan-offer validity of at least **3 working days** for loans with tenor of 7 days or more, and **1 working day** for shorter loans (around para 330). — same

### Cited Findings (secondary or older primary)
- **CIC/CI complaints:**
  - From the RBI circular of 26 Oct 2023 (effective 6 months later, i.e. from about 26 Apr 2024): complainants get **₹100 per calendar day** if the complaint is not resolved within **30 calendar days**.
  - Compensation is credited within **5 working days** of resolution and apportioned between CIs and CICs. Indicatively, CIs get 21 days and CICs 9 days.
  - Carried into the MD – Credit Information Reporting Directions, 2025 (6 Jan 2025), which adds alerts to consumers when their report is accessed, and reasons for rejecting correction requests. — [Taxmann](https://www.taxmann.com/post/blog/rbi-mandates-cis-cics-to-compensate-complainants-with-rs-100-per-day-if-complaints-remain-unresolved-beyond-30-days/); [RBI notification](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12554); [Moneylife](https://moneylife.in/article/rbi-revises-master-directions-on-reporting-of-customers-credit-information/76056.html)
  - One report says "30 working days". RBI text says calendar days. — [Outlook Money](https://www.outlookmoney.com/news/rbi-sets-a-daily-compensation-of-rs-100-for-delayed-credit-complaint-resolution)
- **Credit cards:**
  - From MD Credit Card & Debit Card – Issuance and Conduct, 21 Apr 2022, effective 1 Jul 2022: closure requests are honoured within **7 working days**, subject to dues being paid. After that, **₹500 per calendar day** is payable until closure.
  - Closure must be accepted through multiple channels, without insisting on post, and confirmed immediately by email or SMS.
  - A card not activated within **30 days** of issue needs OTP consent; without it, the card is closed at no cost within 7 working days.
  - Consolidated into "RBI (Commercial Banks – Credit Cards and Debit Cards: Issuance and Conduct) Directions, 2025" (28 Nov 2025). Whether the wording is unchanged is unverified. — [Moneylife](https://mas360.moneylife.in/article/new-credit-card-closure-rules-effective-from-1st-july/4018.html); [Outlook Money](https://www.outlookmoney.com/banking/concerned-if-you-should-pay-dues-for-unused-credit-card-know-rbi-rules-remedies); [Probe42 listing](https://resources.probe42.in/regulatory-updates/rbi-circulars/rbi-commercial-banks-credit-debit-cards/)
- **Digital lending:**
  - RBI (Digital Lending) Directions, 2025 (8 May 2025): every RE and LSP with a borrower interface must have a **nodal grievance redressal officer**, with details shown on the RE/LSP websites and apps. The officer also handles complaints about DLAs.
  - If a complaint is not resolved **within 30 days**, the borrower may go to the RB-IOS (CMS).
  - Para 6 took effect 1 Nov 2025 and para 17 on 15 Jun 2025.
  - Cooling-off period set by the board and disclosed in the KFS. One summary says the minimum is "1 day" after a 2024 change. **This conflicts** with the 2022 rule of 3 days for tenor of 7 days or more, and is easily confused with the KFS validity period. Treat as unverified. — [Mondaq](https://www.mondaq.com/india/financial-services/1632398/digital-lending-in-india-a-regulatory-reset-under-the-reserve-bank-of-india-digital-lending-directions-2025); [RBI Digital Lending Directions](https://website.rbi.org.in/documents/d/rbi/directionsondigitallending); [ELP](https://elplaw.in/wp-content/uploads/2025/05/Regulatory-Update-on-RBIs-Consolidated-Digital-Lending-Framework-%E2%80%93-May-2025.pdf)

### Inferences
- Engine compensation formulas:
  - `DECEASED_DEPOSIT_COMP = amount × (BankRate@docs_date + 4%) × delay_days/365`
  - `LOCKER_CLAIM_COMP = 5000 × delay_days`
  - `PROPERTY_DOC_COMP = 5000 × days beyond 30 (or 60 if lost)`
  - `CARD_CLOSURE_COMP = 500 × days beyond 7 WD`
  - `CIC_COMP = 100 × days beyond 30`
  - `FAILED_TXN_COMP = 100 × days beyond T+n`
  - All are payable without a claim where the text says so: failed transactions, cheque-collection interest and CIC compensation.
- Pension (delayed pension credit at 8% p.a.), senior-citizen doorstep banking specifics, and the ATM cash-out penalty (₹10,000 per ATM for cash-outs over 10 hours/month, an RBI 2021 scheme from the Currency Management Department) are probably in other consolidated MDs. They were not verified this session.

### Gaps
- Not verified this session: pension-delay compensation; the ATM cash-out penalty scheme; the doorstep-banking timeline; third-party product mis-selling rules; locker para numbers and the 100× rent cap; NBFC FPC grievance (30-day) rules.
- The consolidated 2025 card directions were not read.

---

## Q7. Cross-regulator overlaps: NPCI UPI/IMPS dispute TATs and ODR; card-network chargebacks

### Takeaway
RBI rules incorporate NPCI and card-network TATs by reference: RB-IOS cl. 10(1)(f) takes the longer of 30 days and the external TAT, and IO cl. 14(1)(a) requires 10 days of IO review within the external TAT. Current NPCI dispute-stage TAT tables were not retrieved. Confirmed: RBI's Aug 2020 ODR mandate, NPCI's UDIR ODR deadline of 30 Sep 2022, UPI auto-acceptance/rejection of chargebacks from 15 Feb 2025 (OC 213), and IMPS from 27 Aug 2025.

### Cited Findings
- RBI (Aug 2020) required authorised PSOs and participants to implement Online Dispute Resolution by Jan 2021. NPCI required all UPI participants to implement UDIR-based ODR by **30 Sep 2022**; non-compliance meant a ban on onboarding new customers from 1 Oct 2022. — [Lexplosion](https://lexplosion.in/npci-issues-reminder-to-upi-participants-on-implementation-timeline-of-unified-dispute-and-issue-resolution-udir-approach-as-online-dispute-resolution-for-all-upi-users-by-30th-september-2022/); [Moneylife](https://mas360.moneylife.in/article/npci-to-roll-out-real-time-dispute-resolution-system-for-upi/3522.html)
- NPCI UPI OC No. 213/2024-25 (10 Feb 2025): automatic acceptance or rejection of chargebacks based on TCC/RET, effective **15 Feb 2025**, for bulk upload/UDIR only. — [NPCI circular](https://npci.org.in/PDF/npci/upi/circular/2025/UPI-OC-No-213-FY-2024-25-Auto-Acceptance-Rejection-of-Chargeback.pdf); [Angel One](https://www.angelone.in/news/npci-introduces-new-chargeback-rule-for-upi-transactions)
- IMPS (NPCI circular 127/2025-26, 10 Jul 2025): auto-acceptance for deemed-approved P2P chargebacks, effective 27 Aug 2025. Existing TATs unchanged. — [TaxGuru](https://taxguru.in/finance/npci-revises-imps-chargeback-handling-process.html)
- A co-operative bank's notice gives UPI stage timelines: credit adjustment T+1, chargeback within 45 days, re-presentment within 35 days. **This is not NPCI primary; treat as unverified.** — [GS Mahanagar Bank](https://gsmahanagar.bank.in/assets/pdf/other/UPI.pdf)

### Inferences
- An engine should hold an "external TAT" table keyed by channel and dispute type (NPCI UPI/IMPS/NACH/AePS; Visa/Mastercard/RuPay chargeback cycles). It feeds both the RB-IOS maintainability clock and the IO escalation deadline (external TAT − 10 days).

### Gaps
- No current NPCI UPI dispute-TAT annexure or card-network (Visa/Mastercard/RuPay) chargeback-window document was retrieved. Card-network rules are proprietary and largely not public.
- No 2026 NPCI circular changing TATs was found.
