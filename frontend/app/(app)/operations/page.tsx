"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Layers,
  Loader2,
  MessageSquare,
  RefreshCw,
  Settings,
  Zap,
} from "lucide-react";
import { downloadExport } from "@/lib/api/complaints";
import { detectDuplicates, getDuplicateChannelComparison, listDuplicates, mergeDuplicate, rejectDuplicate } from "@/lib/api/duplicates";
import { listFeedback } from "@/lib/api/feedback";
import { createEmbeddingBackfillJob, createProcessingJob } from "@/lib/api/jobs";
import { getSlaBreachRisk, getSlaByChannel, getSlaByProduct, getSlaSummary } from "@/lib/api/sla";
import type {
  DuplicateGroupSummary,
  FeedbackRead,
  ProcessingJobResponse,
  SLABreachRiskResponse,
  SLAGroupedResponse,
  SLASummaryResponse,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";
import { Pagination } from "@/components/ui/Pagination";
import { formatDate, formatDateTime, formatRelative, humanize, toPercent, triggerBlobDownload } from "@/lib/utils/format";

type Tab = "sla" | "duplicates" | "feedback" | "exports";

export default function OperationsPage() {
  const [tab, setTab] = useState<Tab>("sla");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Operations Command</h1>
          <p className="page-subtitle">SLA management, duplicate detection, agent feedback, and exports.</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="tab-bar">
        {([
          { id: "sla", label: "SLA Overview", icon: <CheckCircle2 size={14} /> },
          { id: "duplicates", label: "Duplicates", icon: <Layers size={14} /> },
          { id: "feedback", label: "Feedback", icon: <MessageSquare size={14} /> },
          { id: "exports", label: "Exports & Jobs", icon: <Settings size={14} /> },
        ] as const).map(({ id, label, icon }) => (
          <button
            key={id}
            className={`tab-item ${tab === id ? "active" : ""}`}
            onClick={() => setTab(id)}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>{icon}{label}</span>
          </button>
        ))}
      </div>

      {tab === "sla" && <SlaTab />}
      {tab === "duplicates" && <DuplicatesTab />}
      {tab === "feedback" && <FeedbackTab />}
      {tab === "exports" && <ExportsTab />}
    </div>
  );
}

// ── SLA Tab ───────────────────────────────────────────────────────────────────

function SlaTab() {
  const [summary, setSummary] = useState<SLASummaryResponse | null>(null);
  const [byProduct, setByProduct] = useState<SLAGroupedResponse | null>(null);
  const [byChannel, setByChannel] = useState<SLAGroupedResponse | null>(null);
  const [breach, setBreach] = useState<SLABreachRiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getSlaSummary(), getSlaByProduct(), getSlaByChannel(), getSlaBreachRisk(20)])
      .then(([s, bp, bc, br]) => { setSummary(s); setByProduct(bp); setByChannel(bc); setBreach(br); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load SLA data"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner fullPage label="Loading SLA data…" />;
  if (error) return <div className="alert-error"><AlertTriangle size={14} />{error}</div>;
  if (!summary) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
        {[
          { label: "Total", value: summary.total_complaints.toLocaleString() },
          { label: "Timely", value: summary.timely_count.toLocaleString(), color: "var(--color-resolved)" },
          { label: "Untimely", value: summary.untimely_count.toLocaleString(), color: summary.untimely_count > 0 ? "var(--color-pending)" : undefined },
          { label: "Timely Rate", value: `${Math.round(summary.timely_rate_pct)}%`, color: summary.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-breach)" },
          { label: "Avg Urgency", value: summary.avg_urgency_score != null ? `${Math.round(summary.avg_urgency_score)}/100` : "—" },
          { label: "High Risk + Late", value: summary.high_urgency_untimely_count.toString(), color: summary.high_urgency_untimely_count > 0 ? "var(--color-error)" : undefined },
        ].map(({ label, value, color }) => (
          <div key={label} className="stat-card">
            <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>{label}</span>
            <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", color: color ?? "var(--color-on-background)" }}>{value}</span>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* By product */}
        <div className="card">
          <div className="card-header"><span style={{ fontWeight: 600 }}>SLA by Product</span></div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead><tr><th>Product</th><th>Total</th><th>Timely</th><th>Untimely</th><th>Rate</th><th>Avg Urgency</th></tr></thead>
              <tbody>
                {byProduct?.items.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 16 }}>No data</td></tr>}
                {byProduct?.items.map((row, i) => (
                  <tr key={i}>
                    <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>{row.product ?? "Unknown"}</td>
                    <td>{row.total.toLocaleString()}</td>
                    <td style={{ color: "var(--color-resolved)" }}>{row.timely.toLocaleString()}</td>
                    <td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit" }}>{row.untimely.toLocaleString()}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <div className="progress-bar" style={{ width: 60 }}>
                          <div className="progress-fill" style={{ width: `${row.timely_rate_pct}%`, background: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-pending)" }} />
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 600 }}>{Math.round(row.timely_rate_pct)}%</span>
                      </div>
                    </td>
                    <td>{row.avg_urgency_score != null ? Math.round(row.avg_urgency_score) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* By channel */}
        <div className="card">
          <div className="card-header"><span style={{ fontWeight: 600 }}>SLA by Channel</span></div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead><tr><th>Channel</th><th>Total</th><th>Timely</th><th>Untimely</th><th>Rate</th></tr></thead>
              <tbody>
                {byChannel?.items.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 16 }}>No data</td></tr>}
                {byChannel?.items.map((row, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{row.channel ?? "Unknown"}</td>
                    <td>{row.total.toLocaleString()}</td>
                    <td style={{ color: "var(--color-resolved)" }}>{row.timely.toLocaleString()}</td>
                    <td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit" }}>{row.untimely.toLocaleString()}</td>
                    <td style={{ fontWeight: 600, color: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-breach)" }}>{Math.round(row.timely_rate_pct)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Breach risk */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Zap size={16} style={{ color: "var(--color-breach)" }} />
            <span style={{ fontWeight: 600 }}>SLA Breach Risk</span>
          </div>
          <Badge variant={breach && breach.total > 0 ? "danger" : "neutral"}>{breach?.total ?? 0} at risk</Badge>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead><tr><th>Complaint ID</th><th>Product</th><th>Channel</th><th>Urgency</th><th>Risk</th><th>Date</th></tr></thead>
            <tbody>
              {breach?.items.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 20 }}>No breach risk items</td></tr>
              ) : (
                breach?.items.map((item) => (
                  <tr key={item.complaint_id} onClick={() => window.location.assign(`/queue/${item.complaint_id}`)}>
                    <td><span className="id-pill">{item.complaint_id.slice(0, 14)}…</span></td>
                    <td style={{ maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.product ?? "—"}</td>
                    <td>{item.channel ?? "—"}</td>
                    <td style={{ fontWeight: 600, color: item.urgency_score && item.urgency_score >= 70 ? "var(--color-breach)" : "inherit" }}>{item.urgency_score ?? "—"}</td>
                    <td>{item.churn_risk ? <Badge variant={item.churn_risk === "High" ? "danger" : item.churn_risk === "Medium" ? "warning" : "success"}>{item.churn_risk}</Badge> : "—"}</td>
                    <td style={{ whiteSpace: "nowrap", color: "var(--color-on-surface-variant)", fontSize: 11 }}>{formatDate(item.date_received)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Duplicates Tab ────────────────────────────────────────────────────────────

function DuplicatesTab() {
  const [groups, setGroups] = useState<DuplicateGroupSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [showDetectModal, setShowDetectModal] = useState(false);
  const [detectOpts, setDetectOpts] = useState({ exact_enabled: true, near_enabled: true, near_threshold: 0.85 });
  const [detectResult, setDetectResult] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    listDuplicates()
      .then((r) => { setGroups(r.items); setTotal(r.count); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { reload(); }, [reload]);

  async function handleDetect() {
    setDetecting(true); setDetectResult(null);
    try {
      const r = await detectDuplicates(detectOpts);
      setDetectResult(`Created ${r.total_groups_created} groups (${r.exact_groups_created} exact, ${r.near_groups_created} near-duplicate).`);
      reload();
    } catch (e) { setDetectResult(`Error: ${e instanceof Error ? e.message : "Unknown"}`); }
    finally { setDetecting(false); }
  }

  async function handleMerge(groupId: string, canonicalId: string) {
    setActionLoading(groupId);
    try { await mergeDuplicate(groupId, canonicalId); reload(); }
    catch { /* ignore */ }
    finally { setActionLoading(null); }
  }

  async function handleReject(groupId: string) {
    setActionLoading(groupId);
    try { await rejectDuplicate(groupId); reload(); }
    catch { /* ignore */ }
    finally { setActionLoading(null); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
        <button className="btn-secondary" onClick={reload}><RefreshCw size={14} /></button>
        <button className="btn-primary" onClick={() => setShowDetectModal(true)}>
          <Zap size={14} /> Detect Duplicates
        </button>
      </div>

      <div className="card">
        <div className="card-header">
          <span style={{ fontWeight: 600 }}>Duplicate Groups</span>
          <Badge variant="neutral">{total} groups</Badge>
        </div>
        <div style={{ overflowX: "auto" }}>
          {loading ? <LoadingSpinner fullPage label="Loading…" /> : (
            <table className="data-table">
              <thead>
                <tr><th>Group ID</th><th>Type</th><th>Status</th><th>Members</th><th>Created</th><th style={{ textAlign: "right" }}>Actions</th></tr>
              </thead>
              <tbody>
                {groups.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 24 }}>No duplicate groups found. Run detection first.</td></tr>
                ) : groups.map((g) => (
                  <tr key={g.group_id}>
                    <td><span className="id-pill">{g.group_id.slice(0, 14)}…</span></td>
                    <td><Badge variant={g.detection_type === "exact" ? "info" : "warning"}>{g.detection_type}</Badge></td>
                    <td><Badge variant={g.status === "merged" ? "success" : g.status === "rejected" ? "neutral" : "warning"}>{g.status}</Badge></td>
                    <td>{g.member_count}</td>
                    <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>{formatRelative(g.created_at)}</td>
                    <td style={{ textAlign: "right" }}>
                      {g.status === "detected" && (
                        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                          <button
                            className="btn-secondary"
                            style={{ height: 26, padding: "0 10px", fontSize: 11 }}
                            disabled={actionLoading === g.group_id}
                            onClick={() => g.canonical_complaint_id && handleMerge(g.group_id, g.canonical_complaint_id)}
                          >
                            {actionLoading === g.group_id ? <Loader2 size={11} className="animate-spin" /> : "Merge"}
                          </button>
                          <button
                            className="btn-ghost"
                            style={{ height: 26, padding: "0 10px", fontSize: 11 }}
                            disabled={actionLoading === g.group_id}
                            onClick={() => handleReject(g.group_id)}
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showDetectModal && (
        <Modal title="Detect Duplicates" onClose={() => setShowDetectModal(false)} size="sm"
          footer={
            <>
              <button className="btn-secondary" onClick={() => setShowDetectModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleDetect} disabled={detecting}>
                {detecting ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                Run Detection
              </button>
            </>
          }
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {detectResult && (
              <div className={detectResult.startsWith("Error") ? "alert-error" : "alert-warning"}>
                {detectResult}
              </div>
            )}
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={detectOpts.exact_enabled} onChange={(e) => setDetectOpts(o => ({ ...o, exact_enabled: e.target.checked }))} />
              <span style={{ fontSize: "var(--text-body-sm)" }}>Exact duplicates (hash-based)</span>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={detectOpts.near_enabled} onChange={(e) => setDetectOpts(o => ({ ...o, near_enabled: e.target.checked }))} />
              <span style={{ fontSize: "var(--text-body-sm)" }}>Near-duplicates (semantic similarity)</span>
            </label>
            {detectOpts.near_enabled && (
              <div>
                <label className="form-label">Similarity Threshold: {detectOpts.near_threshold}</label>
                <input type="range" min={0.5} max={1} step={0.01} value={detectOpts.near_threshold}
                  onChange={(e) => setDetectOpts(o => ({ ...o, near_threshold: parseFloat(e.target.value) }))}
                  style={{ width: "100%" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--color-on-surface-variant)" }}>
                  <span>0.5 (looser)</span><span>1.0 (exact)</span>
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Feedback Tab ──────────────────────────────────────────────────────────────

function FeedbackTab() {
  const [items, setItems] = useState<FeedbackRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    listFeedback(50)
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"))
      .finally(() => setLoading(false));
  }, []);

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await downloadExport("feedback/csv");
      triggerBlobDownload(blob, `feedback-${Date.now()}.csv`);
    } catch { /* ignore */ }
    finally { setExporting(false); }
  }

  if (loading) return <LoadingSpinner fullPage label="Loading feedback…" />;

  return (
    <div className="card">
      <div className="card-header">
        <span style={{ fontWeight: 600 }}>Agent Feedback Records</span>
        <button className="btn-secondary" onClick={handleExport} disabled={exporting}>
          {exporting ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
          Export CSV
        </button>
      </div>
      {error && <div className="alert-error" style={{ margin: 12 }}><AlertTriangle size={14} />{error}</div>}
      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr><th>Complaint ID</th><th>Agent</th><th>Action</th><th>Outcome</th><th>Action Used</th><th>Cases Useful</th><th>Submitted</th></tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={7} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 24 }}>No feedback records yet</td></tr>
            ) : items.map((fb) => (
              <tr key={fb.complaint_id} onClick={() => window.location.assign(`/queue/${fb.complaint_id}`)}>
                <td><span className="id-pill">{fb.complaint_id.slice(0, 14)}…</span></td>
                <td style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>{fb.agent_id}</td>
                <td><Badge variant={fb.feedback_action === "accepted" ? "success" : fb.feedback_action === "rejected" ? "danger" : "warning"}>{fb.feedback_action}</Badge></td>
                <td>{humanize(fb.human_review_outcome)}</td>
                <td>{fb.action_used == null ? "—" : fb.action_used ? "Yes" : "No"}</td>
                <td>{fb.similar_cases_useful == null ? "—" : fb.similar_cases_useful ? "Yes" : "No"}</td>
                <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>{formatRelative(fb.submitted_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Exports & Jobs Tab ────────────────────────────────────────────────────────

function ExportsTab() {
  const [jobIds, setJobIds] = useState("");
  const [jobResult, setJobResult] = useState<ProcessingJobResponse | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [backfillLoading, setBackfillLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);

  const exports: { label: string; path: Parameters<typeof downloadExport>[0]; description: string }[] = [
    { label: "Complaints CSV", path: "complaints/csv", description: "Full complaint data with AI analysis" },
    { label: "Complaints PDF", path: "complaints/pdf", description: "Formatted report for distribution" },
    { label: "Analytics CSV", path: "analytics/csv", description: "Aggregated analytics data" },
    { label: "Feedback CSV", path: "feedback/csv", description: "Agent feedback and review outcomes" },
  ];

  async function handleExport(path: Parameters<typeof downloadExport>[0], filename: string) {
    setExportLoading(path);
    try {
      const blob = await downloadExport(path);
      triggerBlobDownload(blob, filename);
    } catch (e) { alert(e instanceof Error ? e.message : "Export failed"); }
    finally { setExportLoading(null); }
  }

  async function handleBatchJob() {
    const ids = jobIds.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean);
    if (ids.length === 0) return;
    setJobLoading(true); setJobError(null);
    try {
      const result = await createProcessingJob(ids);
      setJobResult(result);
    } catch (e) { setJobError(e instanceof Error ? e.message : "Failed"); }
    finally { setJobLoading(false); }
  }

  async function handleBackfill() {
    setBackfillLoading(true);
    try {
      const result = await createEmbeddingBackfillJob();
      setJobResult(result);
    } catch (e) { alert(e instanceof Error ? e.message : "Failed"); }
    finally { setBackfillLoading(false); }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      {/* Exports */}
      <div className="card">
        <div className="card-header"><span style={{ fontWeight: 600 }}>Data Exports</span></div>
        <div style={{ padding: "12px 0" }}>
          {exports.map(({ label, path, description }) => (
            <div key={path} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 24px", borderBottom: "1px solid var(--color-outline-variant)" }}>
              <div>
                <p style={{ fontWeight: 500, fontSize: "var(--text-body-sm)" }}>{label}</p>
                <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>{description}</p>
              </div>
              <button
                className="btn-secondary"
                style={{ height: 30, padding: "0 12px", fontSize: 11 }}
                disabled={exportLoading === path}
                onClick={() => handleExport(path, `${path.replace("/", "-")}-${Date.now()}.${path.endsWith("pdf") ? "pdf" : "csv"}`)}
              >
                {exportLoading === path ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                Download
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Jobs */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card">
          <div className="card-header"><span style={{ fontWeight: 600 }}>Batch Processing Job</span></div>
          <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
            {jobError && <div className="alert-error"><AlertTriangle size={13} />{jobError}</div>}
            <label className="form-label">Complaint IDs (one per line or comma-separated)</label>
            <textarea
              className="form-textarea"
              rows={5}
              value={jobIds}
              onChange={(e) => setJobIds(e.target.value)}
              placeholder={"complaint-id-1\ncomplaint-id-2\n..."}
            />
            <button className="btn-primary" onClick={handleBatchJob} disabled={jobLoading || !jobIds.trim()}>
              {jobLoading ? <Loader2 size={13} className="animate-spin" /> : <Settings size={13} />}
              Create Processing Job
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span style={{ fontWeight: 600 }}>Embedding Backfill</span></div>
          <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface-variant)" }}>
              Generate embeddings for complaints that haven't been embedded yet. Used for similarity search and duplicate detection.
            </p>
            <button className="btn-secondary" onClick={handleBackfill} disabled={backfillLoading}>
              {backfillLoading ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
              Run Embedding Backfill
            </button>
          </div>
        </div>

        {/* Job result */}
        {jobResult && (
          <div className="card">
            <div className="card-header"><span style={{ fontWeight: 600 }}>Job Created</span><Badge variant="info">{jobResult.status}</Badge></div>
            <div style={{ padding: "12px 16px" }}>
              <div className="info-row"><span className="info-label">Job ID</span><span className="info-value" style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>{jobResult.job_id}</span></div>
              <div className="info-row"><span className="info-label">Type</span><span className="info-value">{humanize(jobResult.job_type)}</span></div>
              <div className="info-row"><span className="info-label">Total Items</span><span className="info-value">{jobResult.total_items}</span></div>
              <div className="info-row"><span className="info-label">Status</span><span className="info-value"><Badge variant={jobResult.status === "completed" ? "success" : "warning"}>{jobResult.status}</Badge></span></div>
              <div className="info-row"><span className="info-label">Created</span><span className="info-value">{formatDateTime(jobResult.created_at)}</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
