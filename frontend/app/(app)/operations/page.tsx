"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  BarChart3,
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
import { createEmbeddingBackfillJob, createProcessingJob, listJobs } from "@/lib/api/jobs";
import { getSlaBreachRisk, getSlaByChannel, getSlaByProduct, getSlaSummary, getSlaTrend, type SLAGroupSortBy, type SLATrendGranularity } from "@/lib/api/sla";
import type {
  ChurnRisk,
  DuplicateGroupSummary,
  FeedbackRead,
  ProcessingJobResponse,
  SLABreachRiskResponse,
  SLAGroupedResponse,
  SLASummaryResponse,
  SLATrendResponse,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { TrendChart } from "@/components/ui/TrendChart";
import { Modal } from "@/components/ui/Modal";
import { Pagination } from "@/components/ui/Pagination";
import { churnRiskVariant, formatDate, formatDateTime, formatRelative, humanize, toPercent, triggerBlobDownload, type BadgeVariant } from "@/lib/utils/format";

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

// -- SLA Tab ------------------------------------------------------------------

type SlaHealth = { label: "Healthy" | "At Risk" | "Critical"; variant: BadgeVariant; color: string };

function getSlaHealth(summary: SLASummaryResponse): SlaHealth {
  if (summary.high_urgency_untimely_count > 0 || summary.timely_rate_pct < 70) return { label: "Critical", variant: "danger", color: "var(--color-breach)" };
  if (summary.timely_rate_pct < 90 || summary.untimely_count > 0) return { label: "At Risk", variant: "warning", color: "var(--color-pending)" };
  return { label: "Healthy", variant: "success", color: "var(--color-resolved)" };
}

function SlaTab() {
  const [summary, setSummary] = useState<SLASummaryResponse | null>(null);
  const [byProduct, setByProduct] = useState<SLAGroupedResponse | null>(null);
  const [byChannel, setByChannel] = useState<SLAGroupedResponse | null>(null);
  const [breach, setBreach] = useState<SLABreachRiskResponse | null>(null);
  const [trend, setTrend] = useState<SLATrendResponse | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [summaryProduct, setSummaryProduct] = useState("");
  const [summaryChannel, setSummaryChannel] = useState("");
  const [groupMode, setGroupMode] = useState<"product" | "channel">("product");
  const [groupSort, setGroupSort] = useState<SLAGroupSortBy>("timely_rate");
  const [groupLimit, setGroupLimit] = useState(20);
  const [riskUrgency, setRiskUrgency] = useState(70);
  const [riskChurn, setRiskChurn] = useState<ChurnRisk | "">("");
  const [riskLimit, setRiskLimit] = useState(25);
  const [riskOffset, setRiskOffset] = useState(0);
  const [trendGranularity, setTrendGranularity] = useState<SLATrendGranularity>("weekly");
  const [trendProduct, setTrendProduct] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback((refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    setError(null);
    const dates = { date_from: dateFrom || undefined, date_to: dateTo || undefined };
    Promise.all([
      getSlaSummary({ ...dates, product: summaryProduct || undefined, channel: summaryChannel || undefined }),
      getSlaByProduct({ ...dates, limit: groupLimit, sort_by: groupSort }),
      getSlaByChannel({ ...dates, limit: groupLimit, sort_by: groupSort }),
      getSlaBreachRisk({ urgency_threshold: riskUrgency, churn_risk: riskChurn || undefined, limit: riskLimit, offset: riskOffset }),
      getSlaTrend({ ...dates, granularity: trendGranularity, product: trendProduct || undefined }),
    ])
      .then(([s, bp, bc, br, tr]) => { setSummary(s); setByProduct(bp); setByChannel(bc); setBreach(br); setTrend(tr); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load SLA data"))
      .finally(() => { setLoading(false); setRefreshing(false); });
  }, [dateFrom, dateTo, groupLimit, groupSort, riskChurn, riskLimit, riskOffset, riskUrgency, summaryChannel, summaryProduct, trendGranularity, trendProduct]);

  useEffect(() => { reload(); }, [reload]);

  const productOptions = useMemo(() => Array.from(new Set((byProduct?.items ?? []).map((i) => i.product).filter(Boolean) as string[])).sort(), [byProduct]);
  const channelOptions = useMemo(() => Array.from(new Set((byChannel?.items ?? []).map((i) => i.channel).filter(Boolean) as string[])).sort(), [byChannel]);
  const grouped = groupMode === "product" ? byProduct : byChannel;

  if (loading) return <LoadingSpinner fullPage label="Loading SLA data..." />;
  if (error) return <div className="alert-error"><AlertTriangle size={14} />{error}</div>;
  if (!summary) return null;

  const health = getSlaHealth(summary);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card">
        <div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}>
          <div><span style={{ fontWeight: 700 }}>SLA Health</span><p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", marginTop: 2 }}>{summary.period_from ? `${formatDate(summary.period_from)} to ${formatDate(summary.period_to)}` : "All available complaints"}</p></div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input className="form-input" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setRiskOffset(0); }} style={{ width: 150 }} />
            <input className="form-input" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setRiskOffset(0); }} style={{ width: 150 }} />
            <select className="form-select" value={summaryProduct} onChange={(e) => setSummaryProduct(e.target.value)} style={{ width: 190 }}><option value="">All products</option>{productOptions.map((p) => <option key={p} value={p}>{p}</option>)}</select>
            <select className="form-select" value={summaryChannel} onChange={(e) => setSummaryChannel(e.target.value)} style={{ width: 150 }}><option value="">All channels</option>{channelOptions.map((c) => <option key={c} value={c}>{c}</option>)}</select>
            <button className="btn-secondary" onClick={() => reload(true)} disabled={refreshing}><RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />Refresh</button>
          </div>
        </div>
        <div className="card-body" style={{ display: "grid", gridTemplateColumns: "minmax(220px, 0.8fr) minmax(280px, 1.4fr)", gap: 18 }}>
          <div style={{ borderRight: "1px solid var(--color-outline-variant)", paddingRight: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}><Badge variant={health.variant}>{health.label}</Badge><span style={{ fontSize: 12, color: "var(--color-on-surface-variant)", fontWeight: 600 }}>At Risk</span></div>
            <div style={{ fontSize: 54, fontWeight: 800, lineHeight: 1, color: health.color }}>{Math.round(summary.timely_rate_pct)}%</div>
            <p style={{ fontSize: 13, color: "var(--color-on-surface-variant)", marginTop: 6 }}>Timely response rate</p>
            <RateBar timely={summary.timely_count} untimely={summary.untimely_count} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
            <SlaMetric label="Total" value={summary.total_complaints.toLocaleString()} />
            <SlaMetric label="Timely" value={summary.timely_count.toLocaleString()} color="var(--color-resolved)" />
            <SlaMetric label="Untimely" value={summary.untimely_count.toLocaleString()} color={summary.untimely_count > 0 ? "var(--color-breach)" : undefined} />
            <SlaMetric label="High-risk late" value={summary.high_urgency_untimely_count.toLocaleString()} color={summary.high_urgency_untimely_count > 0 ? "var(--color-error)" : "var(--color-resolved)"} />
            <SlaMetric label="Avg urgency" value={summary.avg_urgency_score != null ? `${Math.round(summary.avg_urgency_score)}/100` : "-"} />
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.15fr) minmax(320px, 0.85fr)", gap: 16 }}>
        <div className="card">
          <div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}><CheckCircle2 size={16} style={{ color: "var(--color-primary)" }} /><span style={{ fontWeight: 700 }}>Product / Channel Breakdown</span></div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {(["product", "channel"] as const).map((m) => <button key={m} className={groupMode === m ? "btn-primary" : "btn-secondary"} style={{ height: 30, padding: "0 12px", fontSize: 11 }} onClick={() => setGroupMode(m)}>{m === "product" ? "Product" : "Channel"}</button>)}
              <select className="form-select" value={groupSort} onChange={(e) => setGroupSort(e.target.value as SLAGroupSortBy)} style={{ width: 165 }}><option value="timely_rate">Timely rate</option><option value="total">Total</option><option value="untimely_count">Untimely count</option></select>
              <select className="form-select" value={groupLimit} onChange={(e) => setGroupLimit(Number(e.target.value))} style={{ width: 110 }}>{[10, 20, 50, 100].map((v) => <option key={v} value={v}>{v} rows</option>)}</select>
            </div>
          </div>
          <GroupedSlaTable mode={groupMode} response={grouped} />
        </div>
        <SlaTrendPanel trend={trend} granularity={trendGranularity} product={trendProduct} products={productOptions} onGranularityChange={setTrendGranularity} onProductChange={setTrendProduct} />
      </div>

      <div className="card">
        <div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}><Zap size={16} style={{ color: "var(--color-breach)" }} /><span style={{ fontWeight: 700 }}>At-risk Queue</span><Badge variant={breach && breach.total > 0 ? "danger" : "neutral"}>{breach?.total ?? 0} at risk</Badge></div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--color-on-surface-variant)", fontWeight: 600 }}>Urgency {riskUrgency}<input type="range" min={0} max={100} step={5} value={riskUrgency} onChange={(e) => { setRiskUrgency(Number(e.target.value)); setRiskOffset(0); }} style={{ width: 120 }} /></label>
            <select className="form-select" value={riskChurn} onChange={(e) => { setRiskChurn(e.target.value as ChurnRisk | ""); setRiskOffset(0); }} style={{ width: 150 }}><option value="">All churn risk</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select>
          </div>
        </div>
        <RiskQueue breach={breach} limit={riskLimit} offset={riskOffset} setLimit={setRiskLimit} setOffset={setRiskOffset} />
      </div>
    </div>
  );
}

function SlaMetric({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="stat-card" style={{ minHeight: 86 }}><span style={{ fontSize: 10, color: "var(--color-on-surface-variant)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>{label}</span><span style={{ fontSize: 25, fontWeight: 800, color: color ?? "var(--color-on-background)", lineHeight: 1.1 }}>{value}</span></div>;
}

function RateBar({ timely, untimely }: { timely: number; untimely: number }) {
  const total = Math.max(timely + untimely, 1);
  return <div style={{ marginTop: 18 }}><div style={{ display: "flex", height: 9, borderRadius: 999, overflow: "hidden", background: "var(--color-surface-container)", gap: 2 }}><div style={{ width: `${(timely / total) * 100}%`, background: "var(--color-resolved)", borderRadius: 999 }} /><div style={{ width: `${(untimely / total) * 100}%`, background: "var(--color-breach)", borderRadius: 999 }} /></div><div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginTop: 6, fontSize: 11 }}><span style={{ color: "var(--color-resolved)", fontWeight: 600 }}>{timely.toLocaleString()} timely</span><span style={{ color: untimely > 0 ? "var(--color-breach)" : "var(--color-on-surface-variant)", fontWeight: 600 }}>{untimely.toLocaleString()} untimely</span></div></div>;
}

function GroupedSlaTable({ mode, response }: { mode: "product" | "channel"; response: SLAGroupedResponse | null }) {
  return <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>{mode === "product" ? "Product" : "Channel"}</th><th>Total</th><th>Timely</th><th>Untimely</th><th>Rate</th><th>Avg Urgency</th></tr></thead><tbody>{response?.items.length === 0 ? <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 22 }}>No grouped SLA data</td></tr> : response?.items.map((row, i) => { const label = mode === "product" ? row.product : row.channel; return <tr key={`${mode}-${label ?? "unknown"}-${i}`}><td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600 }}>{label ?? "Unknown"}</td><td>{row.total.toLocaleString()}</td><td style={{ color: "var(--color-resolved)", fontWeight: 600 }}>{row.timely.toLocaleString()}</td><td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit", fontWeight: row.untimely > 0 ? 600 : 400 }}>{row.untimely.toLocaleString()}</td><td><InlineRate value={row.timely_rate_pct} /></td><td>{row.avg_urgency_score != null ? Math.round(row.avg_urgency_score) : "-"}</td></tr>; })}</tbody></table></div>;
}

function InlineRate({ value }: { value: number }) {
  const color = value >= 90 ? "var(--color-resolved)" : value >= 70 ? "var(--color-pending)" : "var(--color-breach)";
  return <div style={{ display: "flex", alignItems: "center", gap: 7, minWidth: 104 }}><div className="progress-bar" style={{ width: 58 }}><div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }} /></div><span style={{ fontSize: 12, fontWeight: 700, color }}>{Math.round(value)}%</span></div>;
}

function SlaTrendPanel({ trend, granularity, product, products, onGranularityChange, onProductChange }: { trend: SLATrendResponse | null; granularity: SLATrendGranularity; product: string; products: string[]; onGranularityChange: (value: SLATrendGranularity) => void; onProductChange: (value: string) => void }) {
  const chartData = (trend?.items ?? []).map((item) => ({ period: item.period, count: item.timely }));
  return <div className="card"><div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}><div style={{ display: "flex", alignItems: "center", gap: 8 }}><BarChart3 size={16} style={{ color: "var(--color-primary)" }} /><span style={{ fontWeight: 700 }}>SLA Trend</span></div><div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{(["weekly", "monthly"] as const).map((v) => <button key={v} className={granularity === v ? "btn-primary" : "btn-secondary"} style={{ height: 30, padding: "0 12px", fontSize: 11 }} onClick={() => onGranularityChange(v)}>{v === "weekly" ? "Weekly" : "Monthly"}</button>)}<select className="form-select" value={product} onChange={(e) => onProductChange(e.target.value)} style={{ width: 190 }}><option value="">All products</option>{products.map((p) => <option key={p} value={p}>{p}</option>)}</select></div></div><div className="card-body"><TrendChart data={chartData} height={150} color="var(--color-resolved)" label="SLA Timely Trend" /></div><div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Period</th><th>Total</th><th>Timely</th><th>Untimely</th><th>Rate</th></tr></thead><tbody>{trend?.items.length === 0 ? <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 18 }}>No SLA trend data</td></tr> : trend?.items.slice(-6).map((row) => <tr key={row.period}><td style={{ fontWeight: 600 }}>{row.period}</td><td>{row.total.toLocaleString()}</td><td style={{ color: "var(--color-resolved)", fontWeight: 600 }}>{row.timely.toLocaleString()}</td><td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit" }}>{row.untimely.toLocaleString()}</td><td><InlineRate value={row.timely_rate_pct} /></td></tr>)}</tbody></table></div></div>;
}

function RiskQueue({ breach, limit, offset, setLimit, setOffset }: { breach: SLABreachRiskResponse | null; limit: number; offset: number; setLimit: (value: number) => void; setOffset: (value: number) => void }) {
  return <><div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Complaint ID</th><th>Product</th><th>Channel</th><th>Urgency</th><th>Churn Risk</th><th>Received</th><th>Timely Response</th><th></th></tr></thead><tbody>{breach?.items.length === 0 ? <tr><td colSpan={8} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 24 }}>No at-risk complaints match the selected risk filters.</td></tr> : breach?.items.map((item) => { const displayId = item.source_complaint_id || item.complaint_id; return <tr key={item.complaint_id}><td><span className="id-pill">{displayId.slice(0, 16)}{displayId.length > 16 ? "..." : ""}</span></td><td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.product ?? "-"}</td><td>{item.channel ?? "-"}</td><td style={{ fontWeight: 700, color: item.urgency_score != null && item.urgency_score >= 70 ? "var(--color-breach)" : "var(--color-on-surface)" }}>{item.urgency_score ?? "-"}</td><td>{item.churn_risk ? <Badge variant={churnRiskVariant(item.churn_risk)}>{item.churn_risk}</Badge> : "-"}</td><td style={{ whiteSpace: "nowrap", color: "var(--color-on-surface-variant)", fontSize: 12 }}>{formatDate(item.date_received)}</td><td>{item.timely_response == null ? <Badge variant="neutral">Unknown</Badge> : <Badge variant={item.timely_response ? "success" : "danger"}>{item.timely_response ? "Timely" : "Untimely"}</Badge>}</td><td style={{ textAlign: "right" }}><Link className="btn-secondary" style={{ height: 28, padding: "0 10px", fontSize: 11 }} href={`/queue/${item.complaint_id}`}>Open</Link></td></tr>; })}</tbody></table></div><Pagination total={breach?.total ?? 0} limit={limit} offset={offset} onOffsetChange={setOffset} onLimitChange={setLimit} pageSizes={[10, 25, 50, 100, 200]} isLoading={false} /></>;
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
  const [jobsHistory, setJobsHistory] = useState<ProcessingJobResponse[]>([]);

  const reloadJobs = useCallback(() => {
    listJobs({ limit: 10 }).then((r) => setJobsHistory(r.items)).catch(() => null);
  }, []);

  useEffect(() => { reloadJobs(); }, [reloadJobs]);

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
      reloadJobs();
    } catch (e) { setJobError(e instanceof Error ? e.message : "Failed"); }
    finally { setJobLoading(false); }
  }

  async function handleBackfill() {
    setBackfillLoading(true);
    try {
      const result = await createEmbeddingBackfillJob();
      setJobResult(result);
      reloadJobs();
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

        <div className="card">
          <div className="card-header" style={{ justifyContent: "space-between" }}>
            <span style={{ fontWeight: 600 }}>System Jobs History Log</span>
            <button className="btn-secondary" style={{ height: 26, fontSize: 11, padding: "0 8px" }} onClick={reloadJobs}>
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Items</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {jobsHistory.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: 20, color: "var(--color-on-surface-variant)" }}>
                      No historical jobs found
                    </td>
                  </tr>
                ) : (
                  jobsHistory.map((j) => (
                    <tr key={j.job_id}>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>{j.job_id.slice(0, 12)}…</td>
                      <td>{humanize(j.job_type)}</td>
                      <td>
                        <Badge variant={j.status === "completed" ? "success" : j.status === "failed" ? "danger" : "warning"}>
                          {j.status}
                        </Badge>
                      </td>
                      <td>{j.total_items}</td>
                      <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>
                        {formatRelative(j.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
