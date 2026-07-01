"use client";

import React, { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Filter,
  Layers,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Settings,
  ShieldAlert,
  Sparkles,
  XCircle,
  Zap,
} from "lucide-react";
import { downloadExport, getComplaints } from "@/lib/api/complaints";
import { detectDuplicates, getDuplicateChannelComparison, listDuplicates, mergeDuplicate, rejectDuplicate } from "@/lib/api/duplicates";
import { listFeedback } from "@/lib/api/feedback";
import { createEmbeddingBackfillJob, createProcessingJob, getContinuousProcessingStatus, listJobs, retryJob, startContinuousProcessing, stopContinuousProcessing } from "@/lib/api/jobs";
import { getSlaBreachRisk, getSlaByChannel, getSlaByProduct, getSlaSummary, getSlaTrend, type SLAGroupSortBy, type SLATrendGranularity } from "@/lib/api/sla";
import type {
  ChurnRisk,
  ComplaintFilters,
  ComplaintListItem,
  DuplicateGroupSummary,
  FeedbackRead,
  ProcessingJobResponse,
  ContinuousProcessingStatus,
  Sentiment,
  SLABreachRiskResponse,
  SLAGroupedItem,
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

type Tab = "sla" | "at_risk" | "duplicates" | "feedback" | "jobs" | "exports";

export default function OperationsPage() {
  const [tab, setTab] = useState<Tab>("sla");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Operations Command</h1>
          <p className="page-subtitle">SLA management, high-urgency at-risk queue, duplicate detection, agent feedback, AI batch jobs, and data exports.</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="tab-bar">
        {([
          { id: "sla", label: "SLA Overview", icon: <CheckCircle2 size={14} /> },
          { id: "at_risk", label: "At-risk Queue", icon: <Zap size={14} style={{ color: "var(--color-breach)" }} /> },
          { id: "duplicates", label: "Duplicates", icon: <Layers size={14} /> },
          { id: "feedback", label: "Feedback", icon: <MessageSquare size={14} /> },
          { id: "jobs", label: "AI Jobs & Backfill", icon: <RotateCcw size={14} /> },
          { id: "exports", label: "Data Exports", icon: <Download size={14} /> },
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

      {tab === "sla" && <SlaTab onSwitchToAtRisk={() => setTab("at_risk")} />}
      {tab === "at_risk" && <AtRiskTab />}
      {tab === "duplicates" && <DuplicatesTab />}
      {tab === "feedback" && <FeedbackTab />}
      {tab === "jobs" && <JobsTab />}
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

function SlaTab({ onSwitchToAtRisk }: { onSwitchToAtRisk?: () => void }) {
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

  const [popup, setPopup] = useState<{ title: string; type: "card" | "breakdown"; label: string; mode?: "product" | "channel" } | null>(null);

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
            <SlaMetric label="Total" value={summary.total_complaints.toLocaleString()} onClick={() => setPopup({ title: "SLA Health: Total Complaints", type: "card", label: "Total" })} />
            <SlaMetric label="Timely" value={summary.timely_count.toLocaleString()} color="var(--color-resolved)" onClick={() => setPopup({ title: "SLA Health: Timely Responses", type: "card", label: "Timely" })} />
            <SlaMetric label="Untimely" value={summary.untimely_count.toLocaleString()} color={summary.untimely_count > 0 ? "var(--color-breach)" : undefined} onClick={() => setPopup({ title: "SLA Health: Untimely Responses", type: "card", label: "Untimely" })} />
            <SlaMetric label="High-risk late" value={summary.high_urgency_untimely_count.toLocaleString()} color={summary.high_urgency_untimely_count > 0 ? "var(--color-error)" : "var(--color-resolved)"} onClick={() => setPopup({ title: "SLA Health: High-risk Late", type: "card", label: "High-risk late" })} />
            <SlaMetric label="Avg urgency" value={summary.avg_urgency_score != null ? `${Math.round(summary.avg_urgency_score)}/100` : "-"} onClick={() => setPopup({ title: "SLA Health: Sorted by Urgency", type: "card", label: "Avg urgency" })} />
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
          <GroupedSlaTable mode={groupMode} response={grouped} onRowClick={(label, mode) => setPopup({ title: `${mode === "product" ? "Product Breakdown" : "Channel Breakdown"}: ${label}`, type: "breakdown", label, mode })} />
        </div>
        <SlaTrendPanel trend={trend} granularity={trendGranularity} product={trendProduct} products={productOptions} onGranularityChange={setTrendGranularity} onProductChange={setTrendProduct} />
      </div>

      <div className="card">
        <div className="card-header" style={{ gap: 12, flexWrap: "wrap", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}><Zap size={16} style={{ color: "var(--color-breach)" }} /><span style={{ fontWeight: 700 }}>At-risk Queue Preview</span><Badge variant={breach && breach.total > 0 ? "danger" : "neutral"}>{breach?.total ?? 0} at risk</Badge></div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--color-on-surface-variant)", fontWeight: 600 }}>Urgency {riskUrgency}<input type="range" min={0} max={100} step={5} value={riskUrgency} onChange={(e) => { setRiskUrgency(Number(e.target.value)); setRiskOffset(0); }} style={{ width: 100 }} /></label>
            <select className="form-select" value={riskChurn} onChange={(e) => { setRiskChurn(e.target.value as ChurnRisk | ""); setRiskOffset(0); }} style={{ width: 140 }}><option value="">All churn risk</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select>
            {onSwitchToAtRisk && (
              <button className="btn-primary" style={{ height: 28, fontSize: 11, padding: "0 12px", background: "var(--color-breach)", borderColor: "var(--color-breach)" }} onClick={onSwitchToAtRisk}>
                Open Full Command Center →
              </button>
            )}
          </div>
        </div>
        <RiskQueue breach={breach} limit={riskLimit} offset={riskOffset} setLimit={setRiskLimit} setOffset={setRiskOffset} />
      </div>

      {popup && (
        <ComplaintsPopupModal
          popup={popup}
          onClose={() => setPopup(null)}
          dateFrom={dateFrom}
          dateTo={dateTo}
          summaryProduct={summaryProduct}
          summaryChannel={summaryChannel}
        />
      )}
    </div>
  );
}

function SlaMetric({ label, value, color, onClick }: { label: string; value: string; color?: string; onClick?: () => void }) {
  return (
    <div 
      className="stat-card" 
      onClick={onClick}
      style={{ 
        minHeight: 86, 
        cursor: onClick ? "pointer" : "default",
        transition: "all 0.15s ease",
      }}
      title="Click to open popup window with filters and complaints"
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>{label}</span>
        {onClick && <span style={{ fontSize: 10, color: "var(--color-primary)", fontWeight: 600 }}>↗ View</span>}
      </div>
      <span style={{ fontSize: 25, fontWeight: 800, color: color ?? "var(--color-on-background)", lineHeight: 1.1, marginTop: 4 }}>{value}</span>
    </div>
  );
}

function RateBar({ timely, untimely }: { timely: number; untimely: number }) {
  const total = Math.max(timely + untimely, 1);
  return <div style={{ marginTop: 18 }}><div style={{ display: "flex", height: 9, borderRadius: 999, overflow: "hidden", background: "var(--color-surface-container)", gap: 2 }}><div style={{ width: `${(timely / total) * 100}%`, background: "var(--color-resolved)", borderRadius: 999 }} /><div style={{ width: `${(untimely / total) * 100}%`, background: "var(--color-breach)", borderRadius: 999 }} /></div><div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginTop: 6, fontSize: 11 }}><span style={{ color: "var(--color-resolved)", fontWeight: 600 }}>{timely.toLocaleString()} timely</span><span style={{ color: untimely > 0 ? "var(--color-breach)" : "var(--color-on-surface-variant)", fontWeight: 600 }}>{untimely.toLocaleString()} untimely</span></div></div>;
}

function GroupedSlaTable({ 
  mode, 
  response,
  onRowClick,
}: { 
  mode: "product" | "channel"; 
  response: SLAGroupedResponse | null;
  onRowClick?: (label: string, mode: "product" | "channel") => void;
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>{mode === "product" ? "Product" : "Channel"}</th>
            <th>Total</th>
            <th>Timely</th>
            <th>Untimely</th>
            <th>Rate</th>
            <th>Avg Urgency</th>
          </tr>
        </thead>
        <tbody>
          {response?.items.length === 0 ? (
            <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 22 }}>No grouped SLA data</td></tr>
          ) : (
            response?.items.map((row, i) => {
              const label = mode === "product" ? row.product : row.channel;
              const displayLabel = label ?? "Unknown";
              return (
                <tr 
                  key={`${mode}-${displayLabel}-${i}`}
                  onClick={() => onRowClick && onRowClick(displayLabel, mode)}
                  style={{ cursor: onRowClick ? "pointer" : "default" }}
                  title="Click to open popup window with sub-analysis and complaints"
                >
                  <td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600, color: "var(--color-primary)" }}>
                    {displayLabel} <span style={{ fontSize: 10, opacity: 0.8 }}>↗</span>
                  </td>
                  <td>{row.total.toLocaleString()}</td>
                  <td style={{ color: "var(--color-resolved)", fontWeight: 600 }}>{row.timely.toLocaleString()}</td>
                  <td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit", fontWeight: row.untimely > 0 ? 600 : 400 }}>{row.untimely.toLocaleString()}</td>
                  <td><InlineRate value={row.timely_rate_pct} /></td>
                  <td>{row.avg_urgency_score != null ? Math.round(row.avg_urgency_score) : "-"}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

function ComplaintsPopupModal({
  popup,
  onClose,
  dateFrom,
  dateTo,
  summaryProduct,
  summaryChannel,
}: {
  popup: { title: string; type: "card" | "breakdown"; label: string; mode?: "product" | "channel" };
  onClose: () => void;
  dateFrom?: string;
  dateTo?: string;
  summaryProduct?: string;
  summaryChannel?: string;
}) {
  const [complaints, setComplaints] = useState<ComplaintListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");
  const [timelyFilter, setTimelyFilter] = useState<"" | "true" | "false">("");
  const [churnFilter, setChurnFilter] = useState<ChurnRisk | "">("");
  const [sentimentFilter, setSentimentFilter] = useState<Sentiment | "">("");

  useEffect(() => {
    if (popup.type === "card") {
      if (popup.label === "Timely") setTimelyFilter("true");
      else if (popup.label === "Untimely" || popup.label === "High-risk late") setTimelyFilter("false");
    }
  }, [popup]);

  useEffect(() => {
    let active = true;
    setLoading(true);

    const filters: ComplaintFilters = {
      search: search.trim(),
      sentiment: sentimentFilter,
      channel: popup.type === "breakdown" && popup.mode === "channel" ? popup.label : (summaryChannel || ""),
      product: popup.type === "breakdown" && popup.mode === "product" ? popup.label : (summaryProduct || ""),
      churn_risk: churnFilter,
      urgency_min: popup.type === "card" && popup.label === "High-risk late" ? "70" : "",
      urgency_max: "",
      date_received_min: dateFrom || "",
      date_received_max: dateTo || "",
      timely_response: timelyFilter,
      ai_status: "",
      human_review_reason: "",
      sort_by: popup.type === "card" && popup.label === "Avg urgency" ? "urgency_score" : "created_at",
      sort_direction: "desc",
    };

    getComplaints(filters, 100, 0)
      .then((res) => {
        if (active) setComplaints(res.items || []);
      })
      .catch(() => {
        if (active) setComplaints([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [popup, search, timelyFilter, churnFilter, sentimentFilter, dateFrom, dateTo, summaryProduct, summaryChannel]);

  const subBreakdown = useMemo(() => {
    if (!complaints.length) return [];
    const map = new Map<string, { total: number; timely: number; untimely: number; urgencySum: number; urgencyCount: number }>();
    for (const c of complaints) {
      const subLabel = c.sub_product?.trim() || c.issue?.trim() || "General / Unspecified";
      if (!map.has(subLabel)) {
        map.set(subLabel, { total: 0, timely: 0, untimely: 0, urgencySum: 0, urgencyCount: 0 });
      }
      const item = map.get(subLabel)!;
      item.total += 1;
      if (c.timely_response === "Yes") item.timely += 1;
      else if (c.timely_response === "No") item.untimely += 1;
      if (c.urgency_score != null) {
        item.urgencySum += c.urgency_score;
        item.urgencyCount += 1;
      }
    }
    return Array.from(map.entries()).map(([subLabel, data]) => ({
      subLabel,
      total: data.total,
      timely: data.timely,
      untimely: data.untimely,
      timely_rate_pct: data.total > 0 ? Math.round((data.timely / data.total) * 100) : 0,
      avg_urgency_score: data.urgencyCount > 0 ? Math.round(data.urgencySum / data.urgencyCount) : null,
    })).sort((a, b) => b.total - a.total);
  }, [complaints]);

  return (
    <Modal title={popup.title} onClose={onClose} size="2xl">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {subBreakdown.length > 0 && (
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)", marginBottom: 8 }}>
              Sub-product / Issue Breakdown Analysis
            </div>
            <div style={{ overflowX: "auto", maxHeight: 200, overflowY: "auto", border: "1px solid var(--color-outline-variant)", borderRadius: 8 }}>
              <table className="data-table" style={{ fontSize: 12, margin: 0 }}>
                <thead>
                  <tr>
                    <th>Sub-product / Issue</th>
                    <th>Total</th>
                    <th>Timely</th>
                    <th>Untimely</th>
                    <th>Rate</th>
                    <th>Avg Urgency</th>
                  </tr>
                </thead>
                <tbody>
                  {subBreakdown.map((sb) => (
                    <tr key={sb.subLabel}>
                      <td style={{ fontWeight: 600 }}>{sb.subLabel}</td>
                      <td>{sb.total}</td>
                      <td style={{ color: "var(--color-resolved)", fontWeight: 600 }}>{sb.timely}</td>
                      <td style={{ color: sb.untimely > 0 ? "var(--color-breach)" : "inherit" }}>{sb.untimely}</td>
                      <td><InlineRate value={sb.timely_rate_pct} /></td>
                      <td>{sb.avg_urgency_score ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", background: "var(--color-surface-container)", padding: 12, borderRadius: 8 }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search narrative/ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 180, fontSize: 12, height: 32 }}
          />
          <select
            className="form-select"
            value={timelyFilter}
            onChange={(e) => setTimelyFilter(e.target.value as "" | "true" | "false")}
            style={{ width: 140, fontSize: 12, height: 32 }}
          >
            <option value="">All Responses</option>
            <option value="true">Timely Only</option>
            <option value="false">Untimely Only</option>
          </select>
          <select
            className="form-select"
            value={churnFilter}
            onChange={(e) => setChurnFilter(e.target.value as ChurnRisk | "")}
            style={{ width: 130, fontSize: 12, height: 32 }}
          >
            <option value="">All Churn Risk</option>
            <option value="High">High Risk</option>
            <option value="Medium">Medium Risk</option>
            <option value="Low">Low Risk</option>
          </select>
          <select
            className="form-select"
            value={sentimentFilter}
            onChange={(e) => setSentimentFilter(e.target.value as Sentiment | "")}
            style={{ width: 130, fontSize: 12, height: 32 }}
          >
            <option value="">All Sentiments</option>
            <option value="Negative">Negative</option>
            <option value="Neutral">Neutral</option>
            <option value="Positive">Positive</option>
          </select>
          {(search || timelyFilter || churnFilter || sentimentFilter) && (
            <button
              className="btn-secondary"
              onClick={() => { setSearch(""); setTimelyFilter(""); setChurnFilter(""); setSentimentFilter(""); }}
              style={{ height: 32, fontSize: 11, padding: "0 10px" }}
            >
              Reset Filters
            </button>
          )}
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)", marginBottom: 8 }}>
            Matching Complaints ({complaints.length})
          </div>
          {loading ? (
            <div style={{ padding: 40, textAlign: "center" }}>
              <Loader2 size={24} className="animate-spin" style={{ margin: "0 auto", color: "var(--color-primary)" }} />
            </div>
          ) : complaints.length === 0 ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--color-on-surface-variant)", border: "1px dashed var(--color-outline-variant)", borderRadius: 8 }}>
              No complaints match the selected popup filters.
            </div>
          ) : (
            <div style={{ overflowX: "auto", maxHeight: 360, overflowY: "auto", border: "1px solid var(--color-outline-variant)", borderRadius: 8 }}>
              <table className="data-table" style={{ fontSize: 12, margin: 0 }}>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Product</th>
                    <th>Issue</th>
                    <th>Urgency</th>
                    <th>Timely?</th>
                    <th>Received</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {complaints.map((c) => (
                    <tr key={c.complaint_id}>
                      <td><span className="id-pill">{c.complaint_id.slice(0, 14)}…</span></td>
                      <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.product || "-"}</td>
                      <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.issue || c.sub_product || "-"}</td>
                      <td style={{ fontWeight: 700, color: c.urgency_score != null && c.urgency_score >= 70 ? "var(--color-breach)" : "inherit" }}>{c.urgency_score ?? "-"}</td>
                      <td>{c.timely_response === "Yes" ? <Badge variant="success">Timely</Badge> : c.timely_response === "No" ? <Badge variant="danger">Untimely</Badge> : <Badge variant="neutral">-</Badge>}</td>
                      <td>{formatDate(c.date_received)}</td>
                      <td style={{ textAlign: "right" }}>
                        <Link href={`/queue/${c.complaint_id}`} className="btn-secondary" style={{ height: 24, padding: "0 10px", fontSize: 11 }}>
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
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

// ── At-Risk Queue Tab ─────────────────────────────────────────────────────────

function AtRiskTab() {
  const [search, setSearch] = useState("");
  const [urgencyMin, setUrgencyMin] = useState(70);
  const [churnRisk, setChurnRisk] = useState<ChurnRisk | "">("");
  const [timelyFilter, setTimelyFilter] = useState<"" | "true" | "false">("");
  const [productFilter, setProductFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);

  const [complaints, setComplaints] = useState<ComplaintListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [productOptions, setProductOptions] = useState<string[]>([]);
  const [channelOptions, setChannelOptions] = useState<string[]>([]);

  useEffect(() => {
    getSlaByProduct({ limit: 50 }).then(r => setProductOptions((r.items || []).map(i => i.product).filter(Boolean) as string[])).catch(() => {});
    getSlaByChannel({ limit: 50 }).then(r => setChannelOptions((r.items || []).map(i => i.channel).filter(Boolean) as string[])).catch(() => {});
  }, []);

  const loadAtRisk = useCallback(() => {
    setLoading(true);
    getComplaints({
      search,
      sentiment: "",
      channel: channelFilter,
      product: productFilter,
      churn_risk: churnRisk,
      urgency_min: urgencyMin.toString(),
      urgency_max: "100",
      date_received_min: "",
      date_received_max: "",
      timely_response: timelyFilter,
      ai_status: "",
      human_review_reason: "",
      sort_by: "urgency_score",
      sort_direction: "desc",
    }, limit, offset)
      .then(res => {
        setComplaints(res.items);
        setTotalCount(res.count);
        if (res.items.length > 0 && Object.keys(expandedIds).length === 0) {
          setExpandedIds({ [res.items[0].complaint_id]: true });
        }
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [search, channelFilter, productFilter, churnRisk, urgencyMin, timelyFilter, limit, offset]);

  useEffect(() => {
    const t = setTimeout(() => { loadAtRisk(); }, 0);
    return () => clearTimeout(t);
  }, [loadAtRisk]);

  const highChurnCount = useMemo(() => complaints.filter(c => c.churn_risk === "High").length, [complaints]);
  const overdueCount = useMemo(() => complaints.filter(c => c.timely_response === "No").length, [complaints]);
  const reviewNeededCount = useMemo(() => complaints.filter(c => c.human_review_required).length, [complaints]);
  const avgUrgency = useMemo(() => {
    const scores = complaints.map(c => c.urgency_score).filter((s): s is number => s != null);
    return scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
  }, [complaints]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header / Banner */}
      <div className="card" style={{ background: "linear-gradient(135deg, var(--color-surface) 0%, color-mix(in oklch, var(--color-breach) 12%, var(--color-surface)) 100%)", border: "1px solid color-mix(in oklch, var(--color-breach) 35%, var(--color-outline-variant))", padding: "18px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 44, height: 44, borderRadius: 10, background: "color-mix(in oklch, var(--color-breach) 20%, transparent)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-breach)" }}>
              <ShieldAlert size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: "var(--color-on-background)", display: "flex", alignItems: "center", gap: 8 }}>
                At-Risk Complaints Command Center <Badge variant="danger">{totalCount} Critical & At Risk</Badge>
              </h2>
              <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", margin: "4px 0 0 0" }}>
                Proactively monitor, investigate, and resolve high-urgency complaints before SLA breaches or customer churn occur.
              </p>
            </div>
          </div>
          <button className="btn-secondary" style={{ height: 32, fontSize: 12 }} onClick={loadAtRisk} disabled={loading}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Refresh Queue
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <div className="card" style={{ padding: 16, borderLeft: "4px solid var(--color-breach)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)" }}>Queue Volume (Urgency ≥ {urgencyMin})</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-breach)", marginTop: 6 }}>{totalCount.toLocaleString()}</div>
          <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 4 }}>Complaints exceeding urgency threshold</div>
        </div>
        <div className="card" style={{ padding: 16, borderLeft: "4px solid var(--color-pending)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)" }}>Critical Churn Risk</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-pending)", marginTop: 6 }}>{highChurnCount}</div>
          <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 4 }}>Customers likely to terminate services</div>
        </div>
        <div className="card" style={{ padding: 16, borderLeft: "4px solid var(--color-danger, #ef4444)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)" }}>Untimely / Overdue SLA</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-breach)", marginTop: 6 }}>{overdueCount}</div>
          <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 4 }}>Missed required response timeframe</div>
        </div>
        <div className="card" style={{ padding: 16, borderLeft: "4px solid var(--color-primary)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)" }}>Average Urgency Score</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-primary)", marginTop: 6 }}>{avgUrgency ?? "-"}<span style={{ fontSize: 14, fontWeight: 600 }}>/100</span></div>
          <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 4 }}>Flagged for manual review: {reviewNeededCount}</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ padding: "14px 18px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", flex: 1 }}>
            <div style={{ position: "relative", minWidth: 240, flex: 1 }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--color-on-surface-variant)" }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search IDs, narratives, products..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
                style={{ paddingLeft: 30, width: "100%", height: 34, fontSize: 12 }}
              />
            </div>
            
            <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--color-surface-container-low)", padding: "4px 12px", borderRadius: 6, border: "1px solid var(--color-outline-variant)" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--color-on-surface)", whiteSpace: "nowrap" }}>Min Urgency: <span style={{ color: "var(--color-breach)" }}>{urgencyMin}</span></label>
              <input type="range" min={0} max={100} step={5} value={urgencyMin} onChange={(e) => { setUrgencyMin(Number(e.target.value)); setOffset(0); }} style={{ width: 90 }} />
            </div>

            <select className="form-select" value={churnRisk} onChange={(e) => { setChurnRisk(e.target.value as ChurnRisk | ""); setOffset(0); }} style={{ width: 140, height: 34, fontSize: 12 }}>
              <option value="">All Churn Risks</option>
              <option value="High">High Churn Risk</option>
              <option value="Medium">Medium Churn Risk</option>
              <option value="Low">Low Churn Risk</option>
            </select>

            <select className="form-select" value={timelyFilter} onChange={(e) => { setTimelyFilter(e.target.value as "" | "true" | "false"); setOffset(0); }} style={{ width: 140, height: 34, fontSize: 12 }}>
              <option value="">All SLA Status</option>
              <option value="false">Untimely Only</option>
              <option value="true">Timely Only</option>
            </select>

            <select className="form-select" value={productFilter} onChange={(e) => { setProductFilter(e.target.value); setOffset(0); }} style={{ width: 150, height: 34, fontSize: 12 }}>
              <option value="">All Products</option>
              {productOptions.map(p => <option key={p} value={p}>{p}</option>)}
            </select>

            <select className="form-select" value={channelFilter} onChange={(e) => { setChannelFilter(e.target.value); setOffset(0); }} style={{ width: 140, height: 34, fontSize: 12 }}>
              <option value="">All Channels</option>
              {channelOptions.map(ch => <option key={ch} value={ch}>{ch}</option>)}
            </select>
          </div>

          {(search || urgencyMin !== 70 || churnRisk || timelyFilter || productFilter || channelFilter) && (
            <button className="btn-secondary" style={{ height: 34, fontSize: 11, padding: "0 10px" }} onClick={() => { setSearch(""); setUrgencyMin(70); setChurnRisk(""); setTimelyFilter(""); setProductFilter(""); setChannelFilter(""); setOffset(0); }}>
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Main Table */}
      <div className="card">
        <div className="card-header" style={{ justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontWeight: 700 }}>Filtered At-Risk Queue</span>
            <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>Showing {complaints.length} of {totalCount} items</span>
          </div>
          <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>Click any row to inspect customer narrative & AI recommendations</span>
        </div>

        <div style={{ overflowX: "auto" }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: "center" }}><LoadingSpinner label="Analyzing at-risk queue..." /></div>
          ) : complaints.length === 0 ? (
            <EmptyState title="No at-risk complaints found" description="No complaints match your current urgency or risk filter criteria." icon={<CheckCircle2 size={32} style={{ color: "var(--color-resolved)" }} />} />
          ) : (
            <table className="data-table" style={{ margin: 0 }}>
              <thead>
                <tr>
                  <th style={{ width: 28, paddingLeft: 12 }}></th>
                  <th>Complaint ID</th>
                  <th>Product & Issue</th>
                  <th>Urgency</th>
                  <th>Risk & SLA</th>
                  <th>Customer Narrative Snippet</th>
                  <th>Received Date</th>
                  <th style={{ textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c) => {
                  const isExpanded = Boolean(expandedIds[c.complaint_id]);
                  return (
                    <Fragment key={c.complaint_id}>
                      <tr onClick={() => setExpandedIds(p => ({ ...p, [c.complaint_id]: !p[c.complaint_id] }))} style={{ background: isExpanded ? "var(--color-surface-container-low)" : undefined }}>
                        <td style={{ paddingLeft: 12, color: "var(--color-on-surface-variant)" }}>
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </td>
                        <td>
                          <span className="id-pill" style={{ fontWeight: 600 }}>{c.complaint_id.slice(0, 16)}{c.complaint_id.length > 16 ? "…" : ""}</span>
                        </td>
                        <td style={{ maxWidth: 220 }}>
                          <div style={{ fontWeight: 600, color: "var(--color-on-surface)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.product || "General"}</div>
                          <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.issue || c.sub_product || "No issue specified"}</div>
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ fontSize: 15, fontWeight: 800, color: (c.urgency_score ?? 0) >= 90 ? "var(--color-breach)" : (c.urgency_score ?? 0) >= 70 ? "var(--color-pending)" : "inherit" }}>
                              {c.urgency_score ?? "-"}
                            </span>
                            <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>/100</span>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-start" }}>
                            {c.churn_risk && <Badge variant={churnRiskVariant(c.churn_risk)}>{c.churn_risk} Churn</Badge>}
                            {c.timely_response === "Yes" ? <Badge variant="success">Timely</Badge> : c.timely_response === "No" ? <Badge variant="danger">Untimely</Badge> : <Badge variant="neutral">Pending SLA</Badge>}
                          </div>
                        </td>
                        <td style={{ maxWidth: 320 }}>
                          <p style={{ fontSize: 12, color: "var(--color-on-surface)", margin: 0, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", lineHeight: 1.4 }}>
                            {c.narrative || "No customer narrative provided."}
                          </p>
                        </td>
                        <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>
                          {formatDate(c.date_received)}
                        </td>
                        <td style={{ textAlign: "right" }} onClick={(e) => e.stopPropagation()}>
                          <Link href={`/queue/${c.complaint_id}`} className="btn-secondary" style={{ height: 26, padding: "0 10px", fontSize: 11 }}>
                            Open <ExternalLink size={10} />
                          </Link>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr style={{ cursor: "default", background: "var(--color-surface-container-lowest)" }}>
                          <td colSpan={8} style={{ padding: "16px 20px", borderBottom: "2px solid var(--color-outline-variant)" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, 1.4fr) minmax(280px, 1fr)", gap: 20 }}>
                              {/* Left column */}
                              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                <div>
                                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--color-on-surface-variant)", marginBottom: 6 }}>
                                    Full Customer Narrative & Context
                                  </div>
                                  <div style={{ padding: 14, background: "var(--color-surface-container)", borderRadius: 8, borderLeft: "4px solid var(--color-primary)", fontSize: 13, lineHeight: 1.6, color: "var(--color-on-surface)", whiteSpace: "pre-wrap" }}>
                                    {c.narrative || "No narrative text recorded for this complaint."}
                                  </div>
                                </div>

                                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10, background: "var(--color-surface-container-low)", padding: 12, borderRadius: 8, border: "1px solid var(--color-outline-variant)" }}>
                                  <div>
                                    <span style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 700, color: "var(--color-on-surface-variant)", display: "block" }}>Channel</span>
                                    <span style={{ fontSize: 12, fontWeight: 600 }}>{c.channel || "-"}</span>
                                  </div>
                                  <div>
                                    <span style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 700, color: "var(--color-on-surface-variant)", display: "block" }}>Sub-product</span>
                                    <span style={{ fontSize: 12, fontWeight: 600 }}>{c.sub_product || "-"}</span>
                                  </div>
                                  <div>
                                    <span style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 700, color: "var(--color-on-surface-variant)", display: "block" }}>Sub-issue</span>
                                    <span style={{ fontSize: 12, fontWeight: 600 }}>{c.sub_issue || "-"}</span>
                                  </div>
                                  <div>
                                    <span style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 700, color: "var(--color-on-surface-variant)", display: "block" }}>Sentiment</span>
                                    <span style={{ fontSize: 12 }}>{c.sentiment ? <Badge variant={c.sentiment === "Negative" ? "danger" : c.sentiment === "Positive" ? "success" : "neutral"}>{c.sentiment}</Badge> : "-"}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Right column */}
                              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                {c.human_review_required && (
                                  <div className="alert-warning" style={{ margin: 0 }}>
                                    <AlertTriangle size={16} style={{ flexShrink: 0, color: "var(--color-pending)" }} />
                                    <div>
                                      <div style={{ fontWeight: 700, fontSize: 12 }}>Human Review Required</div>
                                      <div style={{ fontSize: 11, marginTop: 2 }}>{c.review_reason || c.human_review_reason || "Flagged by AI or supervisor for manual verification."}</div>
                                    </div>
                                  </div>
                                )}

                                {c.retrieval_warning && (
                                  <div style={{ padding: 10, background: "var(--color-breach-bg)", border: "1px solid color-mix(in oklch, var(--color-breach) 35%, transparent)", borderRadius: 6, fontSize: 11, color: "var(--color-breach-text)" }}>
                                    <span style={{ fontWeight: 700 }}>⚠️ AI Groundedness Notice: </span>
                                    {c.retrieval_warning}
                                  </div>
                                )}

                                <div style={{ padding: 14, background: "var(--color-surface-container-low)", borderRadius: 8, border: "1px solid var(--color-outline-variant)" }}>
                                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--color-primary)", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
                                    <Zap size={13} /> AI Recommended Next Action
                                  </div>
                                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-on-surface)", lineHeight: 1.5 }}>
                                    {c.next_action || "Standard escalation procedure. Review customer history, verify account status, and contact customer within SLA timeframe."}
                                  </div>
                                  {c.draft_response && (
                                    <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px dashed var(--color-outline-variant)", fontSize: 11, color: "var(--color-on-surface-variant)" }}>
                                      <span style={{ fontWeight: 600, color: "var(--color-on-surface)" }}>Draft Response Prepared: </span>
                                      &quot;{c.draft_response.slice(0, 120)}…&quot;
                                    </div>
                                  )}
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: "auto" }}>
                                  <Link href={`/queue/${c.complaint_id}`} className="btn-primary" style={{ height: 32, fontSize: 12, padding: "0 16px", width: "100%", justifyContent: "center" }}>
                                    Investigate & Resolve Complaint <ArrowUpRight size={14} />
                                  </Link>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <Pagination total={totalCount} limit={limit} offset={offset} onOffsetChange={setOffset} onLimitChange={setLimit} pageSizes={[10, 25, 50, 100]} isLoading={loading} />
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

// ── AI Jobs & Backfill Tab ──────────────────────────────────────────────────


function InfoChip({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ minWidth: 0, padding: 10, background: "var(--color-surface-container)", border: "1px solid var(--color-outline-variant)", borderRadius: 6 }}>
      <div style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 700, color: "var(--color-on-surface-variant)", marginBottom: 4 }}>{label}</div>
      <div title={value} style={{ fontSize: 12, fontWeight: 700, color: "var(--color-on-background)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</div>
    </div>
  );
}

function JobsTab() {
  const [dispatchMode, setDispatchMode] = useState<"filter" | "manual">("filter");
  const [filterProduct, setFilterProduct] = useState("");
  const [filterChannel, setFilterChannel] = useState("");
  const [filterStatus, setFilterStatus] = useState<any>("pending");
  const [filterLimit, setFilterLimit] = useState(50);
  const [matchingIds, setMatchingIds] = useState<string[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [productOptions, setProductOptions] = useState<string[]>([]);
  const [channelOptions, setChannelOptions] = useState<string[]>([]);

  const [jobIds, setJobIds] = useState("");
  const [jobResult, setJobResult] = useState<ProcessingJobResponse | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [backfillLoading, setBackfillLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [jobsHistory, setJobsHistory] = useState<ProcessingJobResponse[]>([]);
  const [expandedJobs, setExpandedJobs] = useState<Record<string, boolean>>({});
  const [retryingJob, setRetryingJob] = useState<string | null>(null);
  const [continuousStatus, setContinuousStatus] = useState<ContinuousProcessingStatus | null>(null);
  const [continuousLoading, setContinuousLoading] = useState(false);
  const [continuousHistoryStatus, setContinuousHistoryStatus] = useState("");
  const [continuousHistorySearch, setContinuousHistorySearch] = useState("");
  const [continuousHistoryWindow, setContinuousHistoryWindow] = useState<"all" | "active" | "done" | "attention">("all");

  useEffect(() => {
    getSlaByProduct({ limit: 50 }).then(r => setProductOptions((r.items || []).map(i => i.product).filter(Boolean) as string[])).catch(() => {});
    getSlaByChannel({ limit: 50 }).then(r => setChannelOptions((r.items || []).map(i => i.channel).filter(Boolean) as string[])).catch(() => {});
  }, []);

  const reloadJobs = useCallback(() => {
    listJobs({ limit: 25 }).then((r) => {
      setJobsHistory(r.items);
      setExpandedJobs((prev) => {
        const next = { ...prev };
        r.items.forEach((j) => {
          const hasErr = j.status === "completed_with_errors" || j.status === "failed" || j.status === "error" || (j.counts && j.counts.failed > 0);
          if (hasErr && next[j.job_id] === undefined) {
            next[j.job_id] = true;
          }
        });
        return next;
      });
    }).catch(() => null);
  }, []);

  const reloadContinuousStatus = useCallback(() => {
    getContinuousProcessingStatus().then(setContinuousStatus).catch(() => null);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => { reloadJobs(); reloadContinuousStatus(); }, 0);
    const interval = setInterval(() => { reloadJobs(); reloadContinuousStatus(); }, 4000);
    return () => { clearTimeout(t); clearInterval(interval); };
  }, [reloadJobs, reloadContinuousStatus]);

  async function previewMatchingComplaints() {
    setPreviewLoading(true);
    setJobError(null);
    try {
      const res = await getComplaints({
        search: "",
        sentiment: "",
        channel: filterChannel,
        product: filterProduct,
        churn_risk: "",
        urgency_min: "",
        urgency_max: "",
        date_received_min: "",
        date_received_max: "",
        timely_response: "",
        ai_status: filterStatus,
        human_review_reason: "",
        sort_by: "created_at",
        sort_direction: "desc",
      }, filterLimit, 0);
      const ids = res.items.map(i => i.complaint_id);
      setMatchingIds(ids);
      if (ids.length === 0) {
        setJobError("No complaints match your selected filters.");
      }
    } catch (e) {
      setJobError(e instanceof Error ? e.message : "Failed to preview matching complaints");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleFilteredBatchJob() {
    let idsToProcess = matchingIds;
    if (idsToProcess.length === 0) {
      setJobLoading(true);
      setJobError(null);
      try {
        const res = await getComplaints({
          search: "",
          sentiment: "",
          channel: filterChannel,
          product: filterProduct,
          churn_risk: "",
          urgency_min: "",
          urgency_max: "",
          date_received_min: "",
          date_received_max: "",
          timely_response: "",
          ai_status: filterStatus,
          human_review_reason: "",
          sort_by: "created_at",
          sort_direction: "desc",
        }, filterLimit, 0);
        idsToProcess = res.items.map(i => i.complaint_id);
        setMatchingIds(idsToProcess);
      } catch (e) {
        setJobError(e instanceof Error ? e.message : "Failed to query complaints");
        setJobLoading(false);
        return;
      }
    }
    if (idsToProcess.length === 0) {
      setJobError("No matching complaints found to process.");
      setJobLoading(false);
      return;
    }
    setJobLoading(true); setJobError(null);
    try {
      const result = await createProcessingJob(idsToProcess);
      setJobResult(result);
      setMatchingIds([]);
      reloadJobs();
    } catch (e) { setJobError(e instanceof Error ? e.message : "Failed to dispatch batch job"); }
    finally { setJobLoading(false); }
  }

  async function handleManualBatchJob() {
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

  async function handleContinuousStart() {
    setContinuousLoading(true);
    setJobError(null);
    try {
      const status = await startContinuousProcessing();
      setContinuousStatus(status);
      reloadJobs();
    } catch (e) {
      setJobError(e instanceof Error ? e.message : "Failed to start continuous AI processing");
    } finally {
      setContinuousLoading(false);
    }
  }

  async function handleContinuousStop() {
    setContinuousLoading(true);
    setJobError(null);
    try {
      const status = await stopContinuousProcessing();
      setContinuousStatus(status);
      reloadJobs();
    } catch (e) {
      setJobError(e instanceof Error ? e.message : "Failed to stop continuous AI processing");
    } finally {
      setContinuousLoading(false);
    }
  }

  async function handleRetryJob(jobId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setRetryingJob(jobId);
    try {
      await retryJob(jobId);
      reloadJobs();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to retry job");
    } finally {
      setRetryingJob(null);
    }
  }

  const continuousHistory = (continuousStatus?.history ?? [])
    .filter((item) => {
      if (continuousHistoryStatus && item.status !== continuousHistoryStatus) return false;
      if (continuousHistorySearch.trim() && !item.complaint_id.toLowerCase().includes(continuousHistorySearch.trim().toLowerCase())) return false;
      if (continuousHistoryWindow === "active") return item.status === "queued" || item.status === "running";
      if (continuousHistoryWindow === "done") return item.status === "completed" || item.status === "human_review";
      if (continuousHistoryWindow === "attention") return item.status === "failed" || Boolean(item.error_message);
      return true;
    })
    .slice(0, 10);

  const continuousCounts = (continuousStatus?.history ?? []).reduce((acc, item) => {
    acc.total += 1;
    if (item.status === "queued" || item.status === "running") acc.active += 1;
    if (item.status === "completed" || item.status === "human_review") acc.done += 1;
    if (item.status === "failed" || item.error_message) acc.attention += 1;
    return acc;
  }, { total: 0, active: 0, done: 0, attention: 0 });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card">
        <div className="card-header" style={{ justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Sparkles size={16} style={{ color: "var(--color-primary)" }} />
            <div>
              <span style={{ fontWeight: 800 }}>Continuous Important AI Processing</span>
              <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 2 }}>Processes urgent pending complaints one by one until stopped.</p>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge variant={continuousStatus?.running ? continuousStatus.stopping ? "warning" : "success" : "neutral"}>
              {continuousStatus?.running ? continuousStatus.stopping ? "Stopping" : "Running" : "Stopped"}
            </Badge>
            <button className="btn-primary" style={{ height: 32, fontSize: 12, padding: "0 14px" }} onClick={handleContinuousStart} disabled={continuousLoading || Boolean(continuousStatus?.running)}>
              {continuousLoading && !continuousStatus?.running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
              Start
            </button>
            <button className="btn-secondary" style={{ height: 32, fontSize: 12, padding: "0 14px", borderColor: continuousStatus?.running ? "var(--color-breach)" : undefined, color: continuousStatus?.running ? "var(--color-breach)" : undefined }} onClick={handleContinuousStop} disabled={continuousLoading || !continuousStatus?.running}>
              {continuousLoading && continuousStatus?.running ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
              Stop
            </button>
          </div>
        </div>
        <div style={{ padding: 16, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))", gap: 16, alignItems: "start" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10 }}>
              <InfoChip label="Current" value={continuousStatus?.current_complaint_id ?? "-"} />
              <InfoChip label="Processed" value={String(continuousStatus?.processed_count ?? 0)} />
            </div>
            <InfoChip label="Last update" value={continuousStatus?.last_message ?? "Not started"} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(72px, 1fr))", gap: 8 }}>
              <InfoChip label="Rows" value={String(continuousCounts.total)} />
              <InfoChip label="Active" value={String(continuousCounts.active)} />
              <InfoChip label="Done" value={String(continuousCounts.done)} />
              <InfoChip label="Issues" value={String(continuousCounts.attention)} />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <div>
                <span style={{ fontSize: 13, fontWeight: 800 }}>Detailed History</span>
                <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginLeft: 8 }}>Showing top 10 complaints after filters</span>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <input className="form-input" placeholder="Search complaint ID" value={continuousHistorySearch} onChange={(e) => setContinuousHistorySearch(e.target.value)} style={{ width: 180, height: 32, fontSize: 12 }} />
                <select className="form-select" value={continuousHistoryStatus} onChange={(e) => setContinuousHistoryStatus(e.target.value)} style={{ width: 145, height: 32, fontSize: 12 }}>
                  <option value="">All statuses</option>
                  <option value="queued">Queued</option>
                  <option value="running">Running</option>
                  <option value="completed">Completed</option>
                  <option value="human_review">Human review</option>
                  <option value="failed">Failed</option>
                </select>
                <select className="form-select" value={continuousHistoryWindow} onChange={(e) => setContinuousHistoryWindow(e.target.value as "all" | "active" | "done" | "attention")} style={{ width: 145, height: 32, fontSize: 12 }}>
                  <option value="all">All history</option>
                  <option value="active">Active only</option>
                  <option value="done">Done only</option>
                  <option value="attention">Needs attention</option>
                </select>
              </div>
            </div>
            <div style={{ overflowX: "auto", border: "1px solid var(--color-outline-variant)", borderRadius: 6 }}>
              <table className="data-table" style={{ margin: 0 }}>
                <thead>
                  <tr><th>Complaint</th><th>Status</th><th>Attempts</th><th>Started</th><th>Finished</th><th>Message</th></tr>
                </thead>
                <tbody>
                  {continuousHistory.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", padding: 18, color: "var(--color-on-surface-variant)" }}>No complaints match the selected filters.</td></tr>
                  ) : continuousHistory.map((item, idx) => (
                    <tr key={`${item.job_id}-${item.complaint_id}-${idx}`}>
                      <td><Link href={`/queue/${item.complaint_id}`} className="id-pill" style={{ textDecoration: "none", color: "var(--color-on-background)" }}>{item.complaint_id}</Link></td>
                      <td><Badge variant={item.status === "completed" ? "success" : item.status === "failed" ? "danger" : item.status === "human_review" ? "warning" : "info"}>{humanize(item.status)}</Badge></td>
                      <td>{item.attempt_count}</td>
                      <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>{item.started_at ? formatRelative(item.started_at) : "-"}</td>
                      <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>{item.finished_at ? formatDateTime(item.finished_at) : "-"}</td>
                      <td style={{ fontSize: 11, color: item.error_message ? "var(--color-breach)" : "var(--color-on-surface-variant)", maxWidth: 260 }}>{item.error_message || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(360px, 1fr) minmax(460px, 1.4fr)", gap: 16 }}>
      {/* Left Column: Job Dispatchers */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card">
          <div className="card-header" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Sparkles size={16} style={{ color: "var(--color-primary)" }} />
              <span style={{ fontWeight: 700 }}>Dispatch AI Processing Job</span>
            </div>
            <div style={{ display: "flex", background: "var(--color-surface-container)", padding: 2, borderRadius: 6, border: "1px solid var(--color-outline-variant)" }}>
              <button
                className="btn-secondary"
                style={{ height: 24, fontSize: 11, padding: "0 10px", border: "none", background: dispatchMode === "filter" ? "var(--color-primary)" : "transparent", color: dispatchMode === "filter" ? "var(--color-on-primary)" : "var(--color-on-surface-variant)" }}
                onClick={() => { setDispatchMode("filter"); setJobError(null); }}
              >
                <Filter size={11} style={{ marginRight: 4 }} /> Filter & Select
              </button>
              <button
                className="btn-secondary"
                style={{ height: 24, fontSize: 11, padding: "0 10px", border: "none", background: dispatchMode === "manual" ? "var(--color-primary)" : "transparent", color: dispatchMode === "manual" ? "var(--color-on-primary)" : "var(--color-on-surface-variant)" }}
                onClick={() => { setDispatchMode("manual"); setJobError(null); }}
              >
                Paste ID List
              </button>
            </div>
          </div>

          <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 14 }}>
            {jobError && <div className="alert-error" style={{ margin: 0 }}><AlertTriangle size={14} />{jobError}</div>}

            {dispatchMode === "filter" ? (
              <>
                <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", margin: 0 }}>
                  Easily target specific products, categories, or pending complaints for batch AI sentiment, churn risk, and recommendation analysis.
                </p>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label className="form-label" style={{ fontSize: 11, fontWeight: 700 }}>Product Category</label>
                    <select className="form-select" value={filterProduct} onChange={(e) => { setFilterProduct(e.target.value); setMatchingIds([]); }} style={{ width: "100%", height: 34, fontSize: 12 }}>
                      <option value="">All Products</option>
                      {productOptions.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="form-label" style={{ fontSize: 11, fontWeight: 700 }}>Ingestion Channel</label>
                    <select className="form-select" value={filterChannel} onChange={(e) => { setFilterChannel(e.target.value); setMatchingIds([]); }} style={{ width: "100%", height: 34, fontSize: 12 }}>
                      <option value="">All Channels</option>
                      {channelOptions.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="form-label" style={{ fontSize: 11, fontWeight: 700 }}>AI Processing Status</label>
                    <select className="form-select" value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setMatchingIds([]); }} style={{ width: "100%", height: 34, fontSize: 12 }}>
                      <option value="pending">Pending AI Analysis</option>
                      <option value="human_review">Human Review Required</option>
                      <option value="completed">Completed Analysis</option>
                      <option value="">All Statuses</option>
                    </select>
                  </div>

                  <div>
                    <label className="form-label" style={{ fontSize: 11, fontWeight: 700 }}>Batch Limit</label>
                    <select className="form-select" value={filterLimit} onChange={(e) => { setFilterLimit(Number(e.target.value)); setMatchingIds([]); }} style={{ width: "100%", height: 34, fontSize: 12 }}>
                      <option value={25}>Up to 25 complaints</option>
                      <option value={50}>Up to 50 complaints</option>
                      <option value={100}>Up to 100 complaints</option>
                      <option value={200}>Up to 200 complaints</option>
                    </select>
                  </div>
                </div>

                {matchingIds.length > 0 && (
                  <div style={{ padding: 10, background: "var(--color-surface-container)", borderRadius: 6, border: "1px solid var(--color-outline-variant)", fontSize: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 600, color: "var(--color-primary)" }}>✨ {matchingIds.length} matching complaints found</span>
                    <button className="btn-secondary" style={{ height: 24, fontSize: 10, padding: "0 8px" }} onClick={() => { setJobIds(matchingIds.join("\n")); setDispatchMode("manual"); }}>
                      Edit ID List →
                    </button>
                  </div>
                )}

                <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                  <button className="btn-secondary" style={{ flex: 1, height: 36, fontSize: 12, justifyContent: "center" }} onClick={previewMatchingComplaints} disabled={previewLoading}>
                    {previewLoading ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
                    Preview Count
                  </button>
                  <button className="btn-primary" style={{ flex: 1.5, height: 36, fontSize: 12, justifyContent: "center" }} onClick={handleFilteredBatchJob} disabled={jobLoading}>
                    {jobLoading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                    Dispatch AI Batch Job
                  </button>
                </div>
              </>
            ) : (
              <>
                <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", margin: 0 }}>
                  Manually paste or enter specific Complaint IDs separated by newlines or commas.
                </p>
                <textarea
                  className="form-textarea"
                  rows={5}
                  value={jobIds}
                  onChange={(e) => setJobIds(e.target.value)}
                  placeholder={"complaint-id-1\ncomplaint-id-2\n..."}
                  style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
                />
                <button className="btn-primary" style={{ height: 36, fontSize: 12, justifyContent: "center" }} onClick={handleManualBatchJob} disabled={jobLoading || !jobIds.trim()}>
                  {jobLoading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                  Dispatch Manual ID Batch Job ({jobIds.split(/[\n,]+/).filter(Boolean).length} IDs)
                </button>
              </>
            )}
          </div>
        </div>

        {/* Embedding Backfill Card */}
        <div className="card">
          <div className="card-header"><span style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}><Zap size={16} style={{ color: "var(--color-pending)" }} /> Vector Embedding Backfill</span></div>
          <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", margin: 0, lineHeight: 1.5 }}>
              Automatically scan and generate high-dimensional vector embeddings for all complaints lacking embeddings. Required for AI semantic search groundedness and duplicate clustering.
            </p>
            <button className="btn-secondary" style={{ height: 34, fontSize: 12, justifyContent: "center" }} onClick={handleBackfill} disabled={backfillLoading}>
              {backfillLoading ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
              Run Embedding Backfill Job
            </button>
          </div>
        </div>

        {jobResult && (
          <div className="card" style={{ borderLeft: "4px solid var(--color-primary)" }}>
            <div className="card-header"><span style={{ fontWeight: 700 }}>Latest Job Dispatched</span><Badge variant="info">{jobResult.status}</Badge></div>
            <div style={{ padding: "12px 16px" }}>
              <div className="info-row"><span className="info-label">Job ID</span><span className="info-value" style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700 }}>{jobResult.job_id}</span></div>
              <div className="info-row"><span className="info-label">Type</span><span className="info-value">{humanize(jobResult.job_type)}</span></div>
              <div className="info-row"><span className="info-label">Total Items Dispatched</span><span className="info-value" style={{ fontWeight: 700 }}>{jobResult.total_items}</span></div>
              <div className="info-row"><span className="info-label">Created At</span><span className="info-value">{formatDateTime(jobResult.created_at)}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Right Column: System Jobs History Log */}
      <div className="card" style={{ alignSelf: "start" }}>
        <div className="card-header" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <div>
            <span style={{ fontWeight: 600, display: "block" }}>System Jobs History Log</span>
            <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontWeight: 400 }}>Click any job row to expand detailed logs and failure reasons</span>
          </div>
          <button className="btn-secondary" style={{ height: 26, fontSize: 11, padding: "0 8px" }} onClick={reloadJobs}>
            <RefreshCw size={12} /> Refresh Log
          </button>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th style={{ width: 28, paddingLeft: 12 }}></th>
                <th>Job ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Summary</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {jobsHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: 24, color: "var(--color-on-surface-variant)" }}>
                    No historical jobs found
                  </td>
                </tr>
              ) : (
                jobsHistory.map((j) => {
                  const isExpanded = Boolean(expandedJobs[j.job_id]);
                  const hasErrors = j.status === "completed_with_errors" || j.status === "failed" || j.status === "error" || (j.counts && j.counts.failed > 0);
                  const errorItems = j.items?.filter(i => i.status === "failed" || i.status === "error" || i.status === "completed_with_errors" || Boolean(i.error_message)) ?? [];
                  const badgeVariant = j.status === "completed" ? "success" : j.status === "failed" || j.status === "error" ? "danger" : j.status === "completed_with_errors" ? "warning" : "info";

                  return (
                    <Fragment key={j.job_id}>
                      <tr
                        onClick={() => setExpandedJobs(prev => ({ ...prev, [j.job_id]: !prev[j.job_id] }))}
                        style={{ background: isExpanded ? "var(--color-surface-container-low)" : undefined }}
                      >
                        <td style={{ paddingLeft: 12, color: "var(--color-on-surface-variant)" }}>
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </td>
                        <td style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600 }}>
                          {j.job_id.slice(0, 12)}…
                        </td>
                        <td>{humanize(j.job_type)}</td>
                        <td>
                          <Badge variant={badgeVariant}>
                            {humanize(j.status)}
                          </Badge>
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontWeight: 600 }}>{j.total_items} items</span>
                            {(j.counts?.failed ?? 0) > 0 && (
                              <span style={{ color: "var(--color-breach)", fontSize: 11, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 3 }}>
                                <AlertCircle size={12} /> {j.counts.failed} failed
                              </span>
                            )}
                          </div>
                        </td>
                        <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>
                          {formatRelative(j.created_at)}
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr style={{ cursor: "default", background: "var(--color-surface-container-lowest)" }}>
                          <td colSpan={6} style={{ padding: "16px 20px", borderBottom: "2px solid var(--color-outline-variant)" }}>
                            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                              {/* Header info */}
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, paddingBottom: 10, borderBottom: "1px solid var(--color-outline-variant)" }}>
                                <div>
                                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                    <span style={{ fontWeight: 700, fontSize: 13, color: "var(--color-on-background)" }}>Job Details</span>
                                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-on-surface-variant)", background: "var(--color-surface-container)", padding: "2px 6px", borderRadius: 4 }}>{j.job_id}</span>
                                  </div>
                                  <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 4 }}>
                                    Created by <span style={{ fontWeight: 600, color: "var(--color-on-surface)" }}>{j.created_by}</span> on {formatDateTime(j.created_at)}
                                    {j.started_at && ` • Started: ${formatDateTime(j.started_at)}`}
                                    {j.finished_at && ` • Finished: ${formatDateTime(j.finished_at)}`}
                                  </p>
                                </div>
                                {hasErrors && (
                                  <button
                                    className="btn-secondary"
                                    style={{ height: 28, fontSize: 11, padding: "0 10px", borderColor: "var(--color-breach)", color: "var(--color-breach)" }}
                                    onClick={(e) => handleRetryJob(j.job_id, e)}
                                    disabled={retryingJob === j.job_id}
                                  >
                                    {retryingJob === j.job_id ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                                    Retry Failed Items
                                  </button>
                                )}
                              </div>

                              {/* Counts breakdown */}
                              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: 8, background: "var(--color-surface-container)", padding: 10, borderRadius: 6 }}>
                                <div style={{ textAlign: "center" }}>
                                  <div style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 600, color: "var(--color-on-surface-variant)" }}>Queued</div>
                                  <div style={{ fontWeight: 700, fontSize: 14 }}>{j.counts?.queued ?? 0}</div>
                                </div>
                                <div style={{ textAlign: "center" }}>
                                  <div style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 600, color: "var(--color-on-surface-variant)" }}>Running</div>
                                  <div style={{ fontWeight: 700, fontSize: 14 }}>{j.counts?.running ?? 0}</div>
                                </div>
                                <div style={{ textAlign: "center" }}>
                                  <div style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 600, color: "var(--color-on-surface-variant)" }}>Completed</div>
                                  <div style={{ fontWeight: 700, fontSize: 14, color: "var(--color-resolved)" }}>{j.counts?.completed ?? 0}</div>
                                </div>
                                <div style={{ textAlign: "center" }}>
                                  <div style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 600, color: "var(--color-on-surface-variant)" }}>Review</div>
                                  <div style={{ fontWeight: 700, fontSize: 14, color: "var(--color-pending)" }}>{j.counts?.human_review ?? 0}</div>
                                </div>
                                <div style={{ textAlign: "center" }}>
                                  <div style={{ fontSize: 10, textTransform: "uppercase", fontWeight: 600, color: "var(--color-on-surface-variant)" }}>Errors</div>
                                  <div style={{ fontWeight: 700, fontSize: 14, color: (j.counts?.failed ?? 0) > 0 ? "var(--color-breach)" : "inherit" }}>{j.counts?.failed ?? 0}</div>
                                </div>
                              </div>

                              {/* Detailed Error Log section */}
                              {errorItems.length > 0 ? (
                                <div>
                                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                                    <AlertTriangle size={14} style={{ color: "var(--color-breach)" }} />
                                    <span style={{ fontWeight: 700, fontSize: 12, color: "var(--color-breach)" }}>
                                      Detailed Failure & Error Log ({errorItems.length} complaints)
                                    </span>
                                  </div>
                                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                    {errorItems.map((item, idx) => (
                                      <div key={item.complaint_id + idx} style={{ border: "1px solid color-mix(in oklch, var(--color-breach) 35%, transparent)", background: "var(--color-breach-bg)", borderRadius: 6, padding: 12 }}>
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 6 }}>
                                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                            <Link href={`/queue/${item.complaint_id}`} className="id-pill" style={{ textDecoration: "none", color: "var(--color-on-background)", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 4 }}>
                                              {item.complaint_id} <ExternalLink size={10} />
                                            </Link>
                                            <Badge variant="danger">{humanize(item.status)}</Badge>
                                            <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontWeight: 600 }}>Attempt #{item.attempt_count}</span>
                                          </div>
                                        </div>
                                        <div style={{ fontSize: 12, color: "var(--color-breach-text)", fontWeight: 600, display: "flex", alignItems: "flex-start", gap: 6, marginTop: 6 }}>
                                          <XCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                                          <div>
                                            <span>Error Reason: </span>
                                            <span style={{ fontWeight: 400, fontFamily: "var(--font-mono)" }}>
                                              {item.error_message || "Execution failed or timed out without an explicit error message."}
                                            </span>
                                          </div>
                                        </div>
                                        {item.attempt_history && item.attempt_history.length > 0 && (
                                          <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px dashed color-mix(in oklch, var(--color-breach) 25%, transparent)", fontSize: 11 }}>
                                            <div style={{ fontWeight: 600, color: "var(--color-on-surface-variant)", marginBottom: 4 }}>Previous Attempt History:</div>
                                            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                              {(item.attempt_history as any[]).map((h, hIdx) => (
                                                <div key={hIdx} style={{ display: "flex", justifyContent: "space-between", color: "var(--color-on-surface-variant)" }}>
                                                  <span>Attempt #{h.attempt || hIdx + 1}: {humanize(String(h.status || ""))}</span>
                                                  <span style={{ fontFamily: "var(--font-mono)" }}>{String(h.error_message || "No error text")}</span>
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ) : (
                                <div style={{ padding: 12, background: "var(--color-surface-container)", borderRadius: 6, fontSize: 12, color: "var(--color-on-surface-variant)", textAlign: "center" }}>
                                  No failed or error items reported for this job.
                                </div>
                              )}

                              {/* Item list toggle */}
                              <details style={{ fontSize: 12 }}>
                                <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--color-primary)", padding: "4px 0" }}>
                                  View All {j.items?.length ?? 0} Processed Items
                                </summary>
                                <div style={{ marginTop: 8, maxHeight: 240, overflowY: "auto", border: "1px solid var(--color-outline-variant)", borderRadius: 6 }}>
                                  <table className="data-table" style={{ margin: 0 }}>
                                    <thead>
                                      <tr>
                                        <th>Complaint ID</th>
                                        <th>Status</th>
                                        <th>Attempts</th>
                                        <th>Message / Outcome</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {j.items?.map((item, idx) => (
                                        <tr key={item.complaint_id + idx}>
                                          <td>
                                            <Link href={`/queue/${item.complaint_id}`} className="id-pill" style={{ textDecoration: "none", color: "var(--color-on-background)" }}>
                                              {item.complaint_id}
                                            </Link>
                                          </td>
                                          <td><Badge variant={item.status === "completed" ? "success" : item.status === "failed" ? "danger" : "neutral"}>{humanize(item.status)}</Badge></td>
                                          <td>{item.attempt_count}</td>
                                          <td style={{ fontSize: 11, color: item.error_message ? "var(--color-breach)" : "var(--color-on-surface-variant)", fontFamily: item.error_message ? "var(--font-mono)" : "inherit" }}>{item.error_message || "Success"}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </details>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </div>
  );
}

// ── Data Exports Tab ──────────────────────────────────────────────────────────

function ExportsTab() {
  const [exportLoading, setExportLoading] = useState<string | null>(null);

  const exports = [
    { label: "Full Complaints Database (CSV)", path: "complaints/csv" as const, description: "Complete raw complaint records enriched with AI urgency scores, churn risk, sentiment, and recommended actions.", icon: <FileSpreadsheet size={24} style={{ color: "var(--color-primary)" }} />, badge: "CSV Format" },
    { label: "Executive Compliance Report (PDF)", path: "complaints/pdf" as const, description: "Formatted multi-page executive summary report designed for regulatory audits and stakeholder distribution.", icon: <FileText size={24} style={{ color: "var(--color-breach)" }} />, badge: "PDF Report" },
    { label: "Aggregated Analytics & KPIs (CSV)", path: "analytics/csv" as const, description: "Time-series volume, SLA timely response rates, and product breakdown metrics for data modeling.", icon: <BarChart3 size={24} style={{ color: "var(--color-pending)" }} />, badge: "CSV Format" },
    { label: "Agent Feedback & Audit Log (CSV)", path: "feedback/csv" as const, description: "Reviewer overrides, human supervisor notes, and AI accuracy ratings for governance compliance.", icon: <MessageSquare size={24} style={{ color: "var(--color-resolved)" }} />, badge: "CSV Format" },
  ];

  async function handleExport(path: Parameters<typeof downloadExport>[0], filename: string) {
    setExportLoading(path);
    try {
      const blob = await downloadExport(path);
      triggerBlobDownload(blob, filename);
    } catch (e) { alert(e instanceof Error ? e.message : "Export failed"); }
    finally { setExportLoading(null); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Banner */}
      <div className="card" style={{ background: "linear-gradient(135deg, var(--color-surface) 0%, color-mix(in oklch, var(--color-primary) 10%, var(--color-surface)) 100%)", border: "1px solid color-mix(in oklch, var(--color-primary) 30%, var(--color-outline-variant))", padding: "20px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: "color-mix(in oklch, var(--color-primary) 20%, transparent)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-primary)" }}>
            <Download size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: "var(--color-on-background)" }}>
              Enterprise Data Exports Center
            </h2>
            <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", margin: "4px 0 0 0" }}>
              Download enriched complaint data, compliance reports, and analytical metrics. All files are generated in real-time with active AI annotations.
            </p>
          </div>
        </div>
      </div>

      {/* Grid of Exports */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>
        {exports.map(({ label, path, description, icon, badge }) => (
          <div key={path} className="card" style={{ padding: 20, display: "flex", flexDirection: "column", justifyContent: "space-between", gap: 16, borderTop: "3px solid var(--color-primary)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ width: 44, height: 44, borderRadius: 10, background: "var(--color-surface-container-low)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid var(--color-outline-variant)" }}>
                  {icon}
                </div>
                <Badge variant="neutral">{badge}</Badge>
              </div>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 6px 0", color: "var(--color-on-background)" }}>{label}</h3>
                <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", margin: 0, lineHeight: 1.5 }}>{description}</p>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ height: 36, fontSize: 12, width: "100%", justifyContent: "center" }}
              disabled={exportLoading === path}
              onClick={() => handleExport(path, `${path.replace("/", "-")}-${Date.now()}.${path.endsWith("pdf") ? "pdf" : "csv"}`)}
            >
              {exportLoading === path ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              {exportLoading === path ? "Generating Export File..." : "Download Export File"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
