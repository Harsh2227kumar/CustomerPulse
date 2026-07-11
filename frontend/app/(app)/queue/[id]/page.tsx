"use client";

import { useCallback, useEffect, useState, use } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCopy,
  Clock,
  BookOpenCheck,
  FileSearch,
  Scale,
  Loader2,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Shield,
  ThumbsUp,
  User,
} from "lucide-react";
import {
  approveReview,
  assignComplaint,
  getComplaintDetail,
  getComplaintComplianceExplanation,
  rerunReview,
  resolveReview,
} from "@/lib/api/complaints";
import { getFeedback, submitFeedback } from "@/lib/api/feedback";
import type {
  AgentFeedbackUpsertRequest,
  ComplaintDetail,
  ComplaintComplianceExplanationResponse,
  FeedbackRead,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import {
  aiStatusVariant,
  churnRiskVariant,
  formatDate,
  formatDateTime,
  formatRelative,
  humanize,
  sentimentVariant,
  slaVariant,
  toPercent,
  truncate,
} from "@/lib/utils/format";

export default function ComplaintDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [complaint, setComplaint] = useState<ComplaintDetail | null>(null);
  const [compliance, setCompliance] = useState<ComplaintComplianceExplanationResponse | null>(null);
  const [complianceError, setComplianceError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<FeedbackRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [narrativeExpanded, setNarrativeExpanded] = useState(false);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [countdown, setCountdown] = useState("");

  useEffect(() => {
    if (!complaint?.sla_deadline || complaint.sla_status === "Resolved") {
      setCountdown("");
      return;
    }
    const deadline = new Date(complaint.sla_deadline).getTime();
    function tick() {
      const diff = deadline - Date.now();
      if (diff <= 0) {
        setCountdown("Breached (0s remaining)");
      } else {
        const h = Math.floor(diff / (1000 * 60 * 60));
        const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const s = Math.floor((diff % (1000 * 60)) / 1000);
        setCountdown(`${h}h ${m}m ${s}s remaining`);
      }
    }
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [complaint]);

  async function handleAssign(agentId: string) {
    if (!complaint || !agentId) return;
    setAssigning(true);
    try {
      const updated = await assignComplaint(complaint.complaint_id, agentId);
      setComplaint(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to assign complaint");
    } finally {
      setAssigning(false);
    }
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [detail, fb, complianceResult] = await Promise.allSettled([
        getComplaintDetail(id),
        getFeedback(id),
        getComplaintComplianceExplanation(id, 6),
      ]);
      if (detail.status === "fulfilled") setComplaint(detail.value);
      else throw new Error(detail.reason instanceof Error ? detail.reason.message : "Complaint not found");
      if (fb.status === "fulfilled") setFeedback(fb.value);
      if (complianceResult.status === "fulfilled") {
        setCompliance(complianceResult.value);
        setComplianceError(null);
      } else {
        setCompliance(null);
        setComplianceError(complianceResult.reason instanceof Error ? complianceResult.reason.message : "Compliance evidence unavailable");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load complaint");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  function copyId() {
    if (!complaint) return;
    navigator.clipboard.writeText(complaint.complaint_id).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (loading) return <LoadingSpinner fullPage label="Loading complaint workspace…" />;

  if (error || !complaint) {
    return (
      <div style={{ maxWidth: 480, margin: "64px auto" }}>
        <div className="alert-error">
          <AlertTriangle size={16} />
          <div>
            <strong>Failed to load complaint</strong>
            <p style={{ marginTop: 2 }}>{error}</p>
          </div>
        </div>
        <Link href="/queue" className="btn-secondary" style={{ marginTop: 12, display: "inline-flex" }}>
          <ArrowLeft size={14} /> Back to Queue
        </Link>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* ── Breadcrumb + header ────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <Link href="/queue" style={{ color: "var(--color-on-surface-variant)", fontSize: "var(--text-body-sm)", display: "flex", alignItems: "center", gap: 4 }}>
              <ArrowLeft size={13} /> Queue
            </Link>
            <span style={{ color: "var(--color-outline)" }}>/</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--color-on-surface-variant)" }}>
              {complaint.complaint_id}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: "var(--text-headline-lg)", fontWeight: 700, color: "var(--color-on-background)" }}>
              Complaint Workspace
            </h1>
            <Badge variant={aiStatusVariant(complaint.ai_status)}>
              {humanize(complaint.ai_status)}
            </Badge>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-icon" onClick={copyId} title="Copy complaint ID">
            <ClipboardCopy size={16} />
          </button>
          {copied && <span style={{ fontSize: 11, color: "var(--color-resolved)", alignSelf: "center" }}>Copied!</span>}
          <button className="btn-secondary" onClick={load}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* ── 3-column grid ─────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr 300px", gap: 16, alignItems: "start" }}>
        {/* ── Column 1: Complaint Info ─────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Core info card */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Complaint Info</span>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <div className="info-row"><span className="info-label">Product</span><span className="info-value">{complaint.product ?? "—"}</span></div>
              <div className="info-row"><span className="info-label">Sub-product</span><span className="info-value">{complaint.sub_product ?? "—"}</span></div>
              <div className="info-row"><span className="info-label">Issue</span><span className="info-value">{complaint.issue ?? "—"}</span></div>
              <div className="info-row"><span className="info-label">Company</span><span className="info-value">{complaint.company ?? "—"}</span></div>
              <div className="info-row"><span className="info-label">Channel</span><span className="info-value">{complaint.channel ?? "—"}</span></div>
              <div className="info-row"><span className="info-label">Date Received</span><span className="info-value">{formatDate(complaint.date_received)}</span></div>
              <div className="info-row"><span className="info-label">Processed At</span><span className="info-value">{formatDateTime(complaint.processed_at)}</span></div>
              <div className="info-row">
                <span className="info-label">Timely SLA</span>
                <span className="info-value">
                  {complaint.timely_response != null ? (
                    <Badge variant={slaVariant(complaint.timely_response)}>
                      {complaint.timely_response === "Yes" ? "Timely" : "Untimely"}
                    </Badge>
                  ) : "—"}
                </span>
              </div>
              {complaint.retry_count != null && complaint.retry_count > 0 && (
                <div className="info-row"><span className="info-label">Retries</span><span className="info-value">{complaint.retry_count}</span></div>
              )}
            </div>
          </div>

          {/* Signals card */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>AI Signals</span>
            </div>
            <div style={{ padding: "12px 16px" }}>
              {/* Urgency */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Urgency</span>
                  <span style={{ fontWeight: 700, color: complaint.urgency_score && complaint.urgency_score >= 70 ? "var(--color-breach)" : complaint.urgency_score && complaint.urgency_score >= 40 ? "var(--color-pending)" : "var(--color-resolved)" }}>
                    {complaint.urgency_score ?? "—"}/100
                  </span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${complaint.urgency_score ?? 0}%`, background: complaint.urgency_score && complaint.urgency_score >= 70 ? "var(--color-breach)" : complaint.urgency_score && complaint.urgency_score >= 40 ? "var(--color-pending)" : "var(--color-resolved)" }} />
                </div>
              </div>

              {/* AI Confidence */}
              {complaint.ai_confidence != null && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>AI Confidence</span>
                    <span style={{ fontWeight: 700 }}>{toPercent(complaint.ai_confidence)}</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${Math.round(complaint.ai_confidence <= 1 ? complaint.ai_confidence * 100 : complaint.ai_confidence)}%`, background: "var(--color-processing)" }} />
                  </div>
                </div>
              )}

              {/* Badges row */}
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", paddingTop: 4 }}>
                {complaint.sentiment && <Badge variant={sentimentVariant(complaint.sentiment)}>{complaint.sentiment}</Badge>}
                {complaint.churn_risk && <Badge variant={churnRiskVariant(complaint.churn_risk)}>{complaint.churn_risk} Risk</Badge>}
              </div>

              {/* Human review */}
              {complaint.human_review_reason && (
                <div className="alert-warning" style={{ marginTop: 12 }}>
                  <AlertTriangle size={13} />
                  <div>
                    <strong style={{ fontSize: 11 }}>Human review</strong>
                    <p style={{ fontSize: 11, marginTop: 1 }}>{humanize(complaint.human_review_reason)}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Narrative card */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Narrative</span>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
                {narrativeExpanded ? complaint.narrative : truncate(complaint.narrative, 300)}
              </p>
              {complaint.narrative.length > 300 && (
                <button
                  className="btn-ghost"
                  style={{ marginTop: 6, height: 24, padding: "0 4px", fontSize: 11 }}
                  onClick={() => setNarrativeExpanded(!narrativeExpanded)}
                >
                  {narrativeExpanded ? <><ChevronUp size={11} /> Show less</> : <><ChevronDown size={11} /> Show more</>}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ── Column 2: AI Analysis + Similar Cases + Audit Trail ─────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* AI Analysis */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>AI Analysis</span>
              {complaint.grounded_response && <Badge variant="success">Grounded</Badge>}
            </div>
            <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <p className="form-label">Category</p>
                <p style={{ fontSize: "var(--text-body-sm)" }}>{complaint.category ?? "—"}</p>
              </div>
              <div>
                <p className="form-label">Next Action</p>
                <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)" }}>{complaint.next_action ?? "—"}</p>
              </div>
              <div>
                <p className="form-label">Draft Response</p>
                <div style={{ background: "var(--color-surface-container-low)", borderRadius: "var(--radius-DEFAULT)", padding: "10px 12px", border: "1px solid var(--color-outline-variant)" }}>
                  <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", lineHeight: 1.65 }}>
                    {complaint.draft_response ?? "—"}
                  </p>
                </div>
              </div>
              {complaint.approved_response && (
                <div>
                  <p className="form-label">Approved Response</p>
                  <div style={{ background: "var(--color-resolved-bg)", borderRadius: "var(--radius-DEFAULT)", padding: "10px 12px", border: "1px solid color-mix(in oklch, var(--color-resolved) 25%, transparent)" }}>
                    <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-resolved-text)", lineHeight: 1.65 }}>
                      {complaint.approved_response}
                    </p>
                  </div>
                </div>
              )}
              {complaint.ai_reasoning && (
                <div>
                  <button
                    className="btn-ghost"
                    style={{ height: 24, padding: "0 4px", fontSize: 11, marginBottom: 4 }}
                    onClick={() => setReasoningExpanded(!reasoningExpanded)}
                  >
                    {reasoningExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                    AI Reasoning
                  </button>
                  {reasoningExpanded && (
                    <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", lineHeight: 1.6, padding: "6px 8px", background: "var(--color-surface-container-low)", borderRadius: "var(--radius-DEFAULT)" }}>
                      {complaint.ai_reasoning}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          <RegulatoryCompliancePanel compliance={compliance} error={complianceError} />

          {/* Similar Cases */}
          {complaint.similar_cases && complaint.similar_cases.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Similar Cases</span>
                <Badge variant="neutral">{complaint.similar_cases.length}</Badge>
              </div>
              <div style={{ padding: "8px 0" }}>
                {complaint.similar_cases.map((sc) => (
                  <Link
                    key={sc.complaint_id}
                    href={`/queue/${sc.complaint_id}`}
                    style={{ display: "block", padding: "10px 16px", borderBottom: "1px solid var(--color-outline-variant)", transition: "background 0.1s" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <span className="id-pill" style={{ marginBottom: 4, display: "inline-block" }}>{sc.complaint_id.slice(0, 14)}…</span>
                        <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", lineHeight: 1.4 }}>
                          {truncate(sc.approved_response ?? sc.next_action ?? "—", 100)}
                        </p>
                      </div>
                      {sc.similarity_score != null && (
                        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-processing)", flexShrink: 0 }}>
                          {Math.round(sc.similarity_score * 100)}%
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Audit Trail */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Processing History</span>
              <Badge variant="neutral">{complaint.processing_runs.length} runs</Badge>
            </div>
            <div style={{ padding: "8px 0" }}>
              {complaint.processing_runs.length === 0 ? (
                <p style={{ padding: 16, color: "var(--color-on-surface-variant)", fontSize: "var(--text-body-sm)", textAlign: "center" }}>No processing runs</p>
              ) : (
                complaint.processing_runs.map((run, i) => (
                  <div key={run.id} style={{ padding: "10px 16px", borderBottom: i < complaint.processing_runs.length - 1 ? "1px solid var(--color-outline-variant)" : "none" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 20, height: 20, borderRadius: "50%", background: "var(--color-surface-container)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "var(--color-on-surface-variant)" }}>
                          {run.attempt_number}
                        </div>
                        <div>
                          <p style={{ fontSize: "var(--text-body-sm)", fontWeight: 500 }}>{humanize(run.status_outcome)}</p>
                          <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>
                            {run.trigger_reason ? humanize(run.trigger_reason) : "—"}
                            {run.initiated_by && ` · ${run.initiated_by}`}
                          </p>
                        </div>
                      </div>
                      <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>
                        {formatRelative(run.created_at)}
                      </span>
                    </div>
                    {run.error_category && (
                      <p style={{ fontSize: 11, color: "var(--color-error)", marginTop: 4, marginLeft: 28 }}>{run.error_category}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ── Column 3: Actions + Feedback ────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* SLA Countdown Card */}
          {countdown && (
            <div className="card" style={{ borderLeft: complaint.sla_status === "Breached" ? "4px solid var(--color-error)" : complaint.sla_status === "At Risk" ? "4px solid var(--color-warning)" : "4px solid var(--color-primary)" }}>
              <div className="card-header" style={{ paddingBottom: 8 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                  <Clock size={16} style={{ color: complaint.sla_status === "Breached" ? "var(--color-error)" : "var(--color-primary)" }} />
                  SLA Deadline Countdown
                </span>
                <Badge variant={complaint.sla_status === "Breached" ? "danger" : complaint.sla_status === "At Risk" ? "warning" : "neutral"}>
                  {complaint.sla_status}
                </Badge>
              </div>
              <div style={{ padding: "8px 16px 12px" }}>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color: complaint.sla_status === "Breached" ? "var(--color-error)" : "inherit" }}>
                  {countdown}
                </div>
                {complaint.sla_deadline && (
                  <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 4 }}>
                    Target ETA: {formatDateTime(complaint.sla_deadline)}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Assign Agent Card */}
          <div className="card">
            <div className="card-header">
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                <User size={16} style={{ color: "var(--color-primary)" }} />
                Assigned Agent
              </span>
              <Badge variant={complaint.assigned_agent_id ? "info" : "neutral"}>
                {complaint.assigned_agent_id ? "Assigned" : "Unassigned"}
              </Badge>
            </div>
            <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
              {complaint.assigned_agent_id ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{complaint.assigned_agent_id}</span>
                  <button className="btn-ghost" style={{ fontSize: 11, padding: "2px 8px", height: 24 }} onClick={() => handleAssign("")} disabled={assigning}>
                    Reassign
                  </button>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 8 }}>
                  <select
                    className="form-select"
                    style={{ flex: 1, fontSize: 12, height: 32 }}
                    value={selectedAgent}
                    onChange={(e) => setSelectedAgent(e.target.value)}
                  >
                    <option value="">Select Agent...</option>
                    <option value="agent (Tier 1 Support)">agent (Tier 1 Support)</option>
                    <option value="manager (Tier 2 Escalation)">manager (Tier 2 Escalation)</option>
                    <option value="admin (System Lead)">admin (System Lead)</option>
                    <option value="Harsh Kumar">Harsh Kumar</option>
                  </select>
                  <button
                    className="btn-primary"
                    style={{ height: 32, padding: "0 12px", fontSize: 12 }}
                    disabled={!selectedAgent || assigning}
                    onClick={() => { handleAssign(selectedAgent); setSelectedAgent(""); }}
                  >
                    {assigning ? <Loader2 size={13} className="animate-spin" /> : "Assign"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Review actions */}
          {complaint.ai_status === "human_review" && (
            <ReviewActionsPanel
              complaintId={complaint.complaint_id}
              draftResponse={complaint.draft_response ?? ""}
              onSuccess={(updated) => setComplaint(updated)}
            />
          )}

          {/* Resolution info (if already reviewed) */}
          {complaint.reviewed_at && (
            <div className="card">
              <div className="card-header">
                <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Review Outcome</span>
                <Badge variant="success">Reviewed</Badge>
              </div>
              <div style={{ padding: "12px 16px" }}>
                <div className="info-row"><span className="info-label">Reviewed by</span><span className="info-value">{complaint.reviewer ?? "—"}</span></div>
                <div className="info-row"><span className="info-label">At</span><span className="info-value">{formatDateTime(complaint.reviewed_at)}</span></div>
                {complaint.review_resolution && (
                  <div className="info-row"><span className="info-label">Resolution</span><span className="info-value">{humanize(complaint.review_resolution)}</span></div>
                )}
                {complaint.review_notes && (
                  <div style={{ marginTop: 8 }}>
                    <p className="form-label">Notes</p>
                    <p style={{ fontSize: "var(--text-body-sm)" }}>{complaint.review_notes}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Feedback panel */}
          <FeedbackPanel
            complaintId={complaint.complaint_id}
            existing={feedback}
            onSaved={setFeedback}
          />
        </div>
      </div>
    </div>
  );
}

function RegulatoryCompliancePanel({
  compliance,
  error,
}: {
  compliance: ComplaintComplianceExplanationResponse | null;
  error: string | null;
}) {
  const explanation = compliance?.explanation_with_sources?.explanation;
  const sources = compliance?.explanation_with_sources?.regulatory_sources ?? [];
  const limitations = compliance?.explanation_with_sources?.limitations ?? [];
  const query = compliance?.explanation_with_sources?.retrieval_query ?? "";
  const risk = compliance?.risk_level ?? explanation?.risk_justification.overall_risk_level ?? "low";

  return (
    <div className="card" style={{ border: "1px solid color-mix(in oklch, var(--color-primary) 20%, var(--color-outline-variant))" }}>
      <div className="card-header" style={{ alignItems: "flex-start", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Scale size={16} style={{ color: "var(--color-primary)" }} />
          <div>
            <span style={{ fontWeight: 700, fontSize: "var(--text-headline-sm)" }}>Regulatory Compliance</span>
            <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 2 }}>
              Rule decision, complaint evidence, and RBI guideline citations for audit review.
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <Badge variant={riskVariant(risk)}>{humanize(risk)} Risk</Badge>
          {compliance?.regulatory_flag && <Badge variant="warning">Regulatory Flag</Badge>}
        </div>
      </div>

      <div style={{ padding: "12px 16px", display: "grid", gap: 14 }}>
        {error && (
          <div className="alert-warning">
            <AlertTriangle size={14} />
            <div>
              <strong style={{ fontSize: 12 }}>Compliance evidence could not be loaded</strong>
              <p style={{ fontSize: 12, marginTop: 2 }}>{error}</p>
            </div>
          </div>
        )}

        {!error && compliance && !compliance.available && (
          <div className="alert-warning">
            <FileSearch size={14} />
            <div>
              <strong style={{ fontSize: 12 }}>No compliance evaluation stored yet</strong>
              <p style={{ fontSize: 12, marginTop: 2 }}>{compliance.message}</p>
            </div>
          </div>
        )}

        {!error && compliance?.available && explanation && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
              <InfoTile label="Evidence Record" value={compliance.evidence_record_id ? compliance.evidence_record_id.slice(0, 8) + "..." : "-"} />
              <InfoTile label="Required Action" value={compliance.required_action ? humanize(compliance.required_action) : "None"} />
              <InfoTile label="Evaluated" value={formatDateTime(compliance.evaluated_at)} />
              <InfoTile label="Source Citations" value={`${sources.length}`} />
            </div>

            <div style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-outline-variant)", borderRadius: 8, padding: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <Shield size={14} style={{ color: "var(--color-primary)" }} />
                <strong style={{ fontSize: 13 }}>Risk Summary</strong>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.55 }}>{explanation.risk_justification.reason_summary}</p>
              {explanation.risk_justification.contributing_factors.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                  {explanation.risk_justification.contributing_factors.map((factor) => (
                    <span key={factor} className="id-pill">{factor}</span>
                  ))}
                </div>
              )}
            </div>

            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <strong style={{ fontSize: 13 }}>Triggered Rules</strong>
                <Badge variant="neutral">{explanation.rule_explanations.length}</Badge>
              </div>
              <div style={{ display: "grid", gap: 8 }}>
                {explanation.rule_explanations.length === 0 ? (
                  <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)" }}>No regulatory rule was triggered for this complaint.</p>
                ) : explanation.rule_explanations.map((rule) => (
                  <div key={`${rule.rule_id}-${rule.triggered_at}`} style={{ border: "1px solid var(--color-outline-variant)", borderRadius: 8, padding: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 6 }}>
                      <div>
                        <strong style={{ fontSize: 13 }}>{rule.rule_id}</strong>
                        <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", marginTop: 2 }}>{rule.rule_description}</p>
                      </div>
                      <Badge variant={confidenceBadge(rule.confidence)}>{humanize(rule.confidence)}</Badge>
                    </div>
                    <p style={{ fontSize: 12, lineHeight: 1.55 }}>{rule.why_triggered}</p>
                    {rule.evidence_snippets.length > 0 && (
                      <div style={{ marginTop: 8, display: "grid", gap: 5 }}>
                        {rule.evidence_snippets.slice(0, 3).map((snippet, index) => (
                          <p key={index} style={{ fontSize: 11, color: "var(--color-on-surface-variant)", background: "var(--color-surface-container-low)", padding: "6px 8px", borderRadius: 6 }}>
                            {snippet}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <BookOpenCheck size={14} style={{ color: "var(--color-primary)" }} />
                  <strong style={{ fontSize: 13 }}>Regulatory Sources</strong>
                </div>
                <Badge variant={sources.length ? "info" : "neutral"}>{sources.length} matched</Badge>
              </div>
              {sources.length === 0 ? (
                <div className="alert-warning">
                  <FileSearch size={14} />
                  <div>
                    <strong style={{ fontSize: 12 }}>No guideline citation found</strong>
                    <p style={{ fontSize: 12, marginTop: 2 }}>Backfill embeddings for regulatory documents, then refresh this complaint.</p>
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", gap: 8 }}>
                  {sources.map((source) => (
                    <div key={source.chunk_id} style={{ border: "1px solid var(--color-outline-variant)", borderRadius: 8, padding: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 6 }}>
                        <div style={{ minWidth: 0 }}>
                          <strong style={{ fontSize: 13 }}>{source.document_title ?? "Regulatory document"}</strong>
                          <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 2 }}>
                            {source.regulator} / {source.domain} / {source.section_reference ?? "Unsectioned"} / pages {formatPageRange(source.page_start, source.page_end)}
                          </p>
                        </div>
                        <Badge variant={source.similarity_score >= 0.75 ? "success" : source.similarity_score >= 0.5 ? "warning" : "neutral"}>
                          {(source.similarity_score * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <p style={{ fontSize: 12, lineHeight: 1.55 }}>{source.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ borderTop: "1px solid var(--color-outline-variant)", paddingTop: 10 }}>
              <p className="form-label">Retrieval Query</p>
              <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", lineHeight: 1.5 }}>{truncate(query || "-", 420)}</p>
              {limitations.map((item) => (
                <p key={item} style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 6 }}>{item}</p>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid var(--color-outline-variant)", borderRadius: 8, padding: 10, background: "var(--color-surface-container-low)" }}>
      <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontWeight: 700, textTransform: "uppercase" }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>{value}</p>
    </div>
  );
}

function riskVariant(value: string | null | undefined): "success" | "warning" | "danger" | "neutral" {
  if (value === "critical" || value === "high") return "danger";
  if (value === "medium") return "warning";
  return "success";
}

function confidenceBadge(value: string): "success" | "warning" | "neutral" {
  if (value === "high") return "success";
  if (value === "medium") return "warning";
  return "neutral";
}

function formatPageRange(start: number | null, end: number | null): string {
  if (start == null && end == null) return "-";
  if (start === end || end == null) return String(start ?? end);
  return `${start}-${end}`;
}
// ── Review Actions Panel ──────────────────────────────────────────────────────

function ReviewActionsPanel({
  complaintId,
  draftResponse,
  onSuccess,
}: {
  complaintId: string;
  draftResponse: string;
  onSuccess: (c: ComplaintDetail) => void;
}) {
  const [mode, setMode] = useState<"idle" | "approve" | "resolve" | "rerunning">("idle");
  const [editedResponse, setEditedResponse] = useState(draftResponse);
  const [notes, setNotes] = useState("");
  const [resolution, setResolution] = useState("resolved");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleApprove() {
    setLoading(true); setError(null);
    try {
      const updated = await approveReview(complaintId, { approved_response: editedResponse, notes: notes || null });
      onSuccess(updated);
      setMode("idle");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  }

  async function handleResolve() {
    setLoading(true); setError(null);
    try {
      const updated = await resolveReview(complaintId, { resolution, notes: notes || null });
      onSuccess(updated);
      setMode("idle");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  }

  async function handleRerun() {
    setLoading(true); setError(null); setMode("rerunning");
    try {
      const updated = await rerunReview(complaintId);
      // rerun returns ProcessedComplaintResponse, reload full detail
      window.location.reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); setMode("idle"); }
    finally { setLoading(false); }
  }

  return (
    <div className="card" style={{ border: "1px solid color-mix(in oklch, var(--color-pending) 40%, transparent)" }}>
      <div className="card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={16} style={{ color: "var(--color-pending)" }} />
          <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Review Actions</span>
        </div>
        <Badge variant="warning">Needs Review</Badge>
      </div>
      <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
        {error && <div className="alert-error"><AlertTriangle size={12} />{error}</div>}

        {mode === "idle" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <button className="btn-primary" onClick={() => setMode("approve")}>
              <ThumbsUp size={14} /> Approve Response
            </button>
            <button className="btn-secondary" onClick={() => setMode("resolve")}>
              <CheckCircle2 size={14} /> Resolve
            </button>
            <button className="btn-ghost" onClick={handleRerun} disabled={loading}>
              {loading ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
              Re-run AI
            </button>
          </div>
        )}

        {mode === "approve" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <label className="form-label">Approved Response</label>
            <textarea
              className="form-textarea"
              rows={4}
              value={editedResponse}
              onChange={(e) => setEditedResponse(e.target.value)}
            />
            <label className="form-label">Notes (optional)</label>
            <textarea className="form-textarea" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn-primary" onClick={handleApprove} disabled={loading} style={{ flex: 1 }}>
                {loading ? <Loader2 size={13} className="animate-spin" /> : <ThumbsUp size={13} />}
                Confirm Approval
              </button>
              <button className="btn-ghost" onClick={() => setMode("idle")}>Cancel</button>
            </div>
          </div>
        )}

        {mode === "resolve" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <label className="form-label">Resolution</label>
            <select className="form-select" value={resolution} onChange={(e) => setResolution(e.target.value)}>
              <option value="resolved">Resolved</option>
              <option value="pending">Pending</option>
              <option value="escalated_tier2">Escalated (Tier 2)</option>
              <option value="closed">Closed</option>
            </select>
            <label className="form-label">Notes (optional)</label>
            <textarea className="form-textarea" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn-primary" onClick={handleResolve} disabled={loading} style={{ flex: 1 }}>
                {loading ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                Confirm Resolution
              </button>
              <button className="btn-ghost" onClick={() => setMode("idle")}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Feedback Panel ────────────────────────────────────────────────────────────

function FeedbackPanel({
  complaintId,
  existing,
  onSaved,
}: {
  complaintId: string;
  existing: FeedbackRead | null;
  onSaved: (f: FeedbackRead) => void;
}) {
  const [form, setForm] = useState<Omit<AgentFeedbackUpsertRequest, "agent_id">>({
    feedback_action: existing?.feedback_action ?? "accepted",
    final_response: existing?.final_response ?? "",
    action_used: existing?.action_used ?? null,
    human_review_outcome: existing?.human_review_outcome ?? "resolved",
    similar_cases_useful: existing?.similar_cases_useful ?? null,
    notes: existing?.notes ?? "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(!!existing);
  const [editing, setEditing] = useState(!existing);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const result = await submitFeedback(complaintId, { agent_id: "ops-user", ...form });
      onSaved(result);
      setSaved(true);
      setEditing(false);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to save feedback"); }
    finally { setLoading(false); }
  }

  return (
    <div className="card">
      <div className="card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <MessageSquare size={16} style={{ color: "var(--color-primary)" }} />
          <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Agent Feedback</span>
        </div>
        {saved && !editing && (
          <button className="btn-ghost" style={{ height: 24, fontSize: 11 }} onClick={() => setEditing(true)}>Edit</button>
        )}
      </div>
      <div style={{ padding: "12px 16px" }}>
        {!editing && saved && existing ? (
          <div>
            <div className="info-row"><span className="info-label">Action</span><span className="info-value"><Badge variant={existing.feedback_action === "accepted" ? "success" : existing.feedback_action === "rejected" ? "danger" : "warning"}>{existing.feedback_action}</Badge></span></div>
            <div className="info-row"><span className="info-label">Outcome</span><span className="info-value">{humanize(existing.human_review_outcome)}</span></div>
            {existing.action_used != null && <div className="info-row"><span className="info-label">Action Used</span><span className="info-value">{existing.action_used ? "Yes" : "No"}</span></div>}
            {existing.similar_cases_useful != null && <div className="info-row"><span className="info-label">Cases Useful</span><span className="info-value">{existing.similar_cases_useful ? "Yes" : "No"}</span></div>}
            {existing.notes && <div style={{ marginTop: 8 }}><p className="form-label">Notes</p><p style={{ fontSize: "var(--text-body-sm)" }}>{existing.notes}</p></div>}
            <p style={{ fontSize: 10, color: "var(--color-on-surface-variant)", marginTop: 8 }}>
              Submitted {formatRelative(existing.submitted_at)} · {existing.revision_count} revision(s)
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {error && <div className="alert-error"><AlertTriangle size={12} />{error}</div>}
            <div>
              <label className="form-label">Feedback Action</label>
              <select className="form-select" value={form.feedback_action} onChange={(e) => setForm(f => ({ ...f, feedback_action: e.target.value as AgentFeedbackUpsertRequest["feedback_action"] }))}>
                <option value="accepted">Accepted</option>
                <option value="edited">Edited</option>
                <option value="rejected">Rejected</option>
                <option value="escalated">Escalated</option>
              </select>
            </div>
            <div>
              <label className="form-label">Human Review Outcome</label>
              <select className="form-select" value={form.human_review_outcome} onChange={(e) => setForm(f => ({ ...f, human_review_outcome: e.target.value as AgentFeedbackUpsertRequest["human_review_outcome"] }))}>
                <option value="resolved">Resolved</option>
                <option value="pending">Pending</option>
                <option value="escalated_tier2">Escalated (Tier 2)</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <label className="form-label">Final Response (if edited)</label>
              <textarea className="form-textarea" rows={3} value={form.final_response ?? ""} onChange={(e) => setForm(f => ({ ...f, final_response: e.target.value }))} placeholder="Leave blank if response was accepted as-is" />
            </div>
            <div style={{ display: "flex", gap: 16 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "var(--text-body-sm)", cursor: "pointer" }}>
                <input type="checkbox" checked={form.action_used ?? false} onChange={(e) => setForm(f => ({ ...f, action_used: e.target.checked }))} />
                Next action used
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "var(--text-body-sm)", cursor: "pointer" }}>
                <input type="checkbox" checked={form.similar_cases_useful ?? false} onChange={(e) => setForm(f => ({ ...f, similar_cases_useful: e.target.checked }))} />
                Similar cases helpful
              </label>
            </div>
            <div>
              <label className="form-label">Notes</label>
              <textarea className="form-textarea" rows={2} value={form.notes ?? ""} onChange={(e) => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Optional notes for QA…" />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn-primary" disabled={loading} style={{ flex: 1 }}>
                {loading ? <Loader2 size={13} className="animate-spin" /> : null}
                {saved ? "Update Feedback" : "Submit Feedback"}
              </button>
              {saved && <button type="button" className="btn-ghost" onClick={() => setEditing(false)}>Cancel</button>}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
