"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { getComplaintTrends, getHighUrgency, getProductSummary } from "@/lib/api/analytics";
import { getComplaints } from "@/lib/api/complaints";
import { getSlaSummary } from "@/lib/api/sla";
import type {
  ComplaintListItem,
  HighUrgencyResponse,
  ProductSummaryResponse,
  SLASummaryResponse,
  TrendResponse,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { TrendChart } from "@/components/ui/TrendChart";
import {
  aiStatusVariant,
  churnRiskVariant,
  formatDate,
  formatRelative,
  sentimentVariant,
  toPercent,
  truncate,
} from "@/lib/utils/format";

const DEFAULT_FILTERS = {
  search: "",
  sentiment: "" as const,
  channel: "",
  product: "",
  churn_risk: "" as const,
  urgency_min: "",
  urgency_max: "",
  date_received_min: "",
  date_received_max: "",
  timely_response: "" as const,
  ai_status: "" as const,
  human_review_reason: "",
  sort_by: "created_at" as const,
  sort_direction: "desc" as const,
};

interface DashboardData {
  sla: SLASummaryResponse;
  trend: TrendResponse;
  trendMonthly: TrendResponse;
  products: ProductSummaryResponse;
  highUrgency: HighUrgencyResponse;
  recent: ComplaintListItem[];
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<"week" | "month">("week");
  const [refreshing, setRefreshing] = useState(false);

  const fetchAll = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [sla, trend, trendMonthly, products, highUrgency, recent] =
        await Promise.all([
          getSlaSummary(),
          getComplaintTrends("week"),
          getComplaintTrends("month"),
          getProductSummary(),
          getHighUrgency(5),
          getComplaints(DEFAULT_FILTERS, 5, 0),
        ]);
      setData({
        sla,
        trend,
        trendMonthly,
        products,
        highUrgency,
        recent: recent.items,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (loading) return <LoadingSpinner fullPage label="Loading dashboard…" />;

  if (error) {
    return (
      <div className="max-w-lg mx-auto mt-xl">
        <div className="alert-error">
          <AlertTriangle size={16} className="shrink-0 mt-px" />
          <div>
            <p className="font-semibold">Failed to load dashboard</p>
            <p style={{ marginTop: 2 }}>{error}</p>
          </div>
        </div>
        <button
          onClick={() => fetchAll()}
          className="btn-secondary mt-4"
        >
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { sla, trend, trendMonthly, products, highUrgency, recent } = data;
  const trendData = granularity === "week" ? trend : trendMonthly;
  const slaHealth = dashboardSlaHealth(sla);

  // Compute product distribution
  const topProducts = [...products.items]
    .filter((p) => p.product)
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
  const maxProdCount = topProducts[0]?.count ?? 1;

  return (
    <div className="flex flex-col gap-6">
      {/* ── Page Header ───────────────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Operational Overview</h1>
          <p className="page-subtitle">
            Real-time snapshot of complaint processing and SLA health.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={() => fetchAll(true)}
            className="btn-secondary"
            disabled={refreshing}
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
          <Link href="/queue" className="btn-primary">
            View Queue <ArrowRight size={14} />
          </Link>
        </div>
      </div>

      {/* ── KPI Row ───────────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <KpiCard
          icon={<Users size={18} />}
          label="Total Complaints"
          value={sla.total_complaints.toLocaleString()}
          iconColor="var(--color-primary)"
          iconBg="var(--color-surface-container)"
        />
        <KpiCard
          icon={<CheckCircle2 size={18} />}
          label="Timely Responses"
          value={sla.timely_count.toLocaleString()}
          sub={`${Math.round(sla.timely_rate_pct)}%`}
          iconColor="var(--color-resolved)"
          iconBg="var(--color-resolved-bg)"
        />
        <KpiCard
          icon={<Clock size={18} />}
          label="Untimely"
          value={sla.untimely_count.toLocaleString()}
          iconColor="var(--color-pending)"
          iconBg="var(--color-pending-bg)"
          valueColor={sla.untimely_count > 0 ? "var(--color-pending)" : undefined}
        />
        <KpiCard
          icon={<TrendingUp size={18} />}
          label="SLA Timely Rate"
          value={`${Math.round(sla.timely_rate_pct)}%`}
          iconColor="var(--color-processing)"
          iconBg="var(--color-processing-bg)"
          valueColor={sla.timely_rate_pct >= 80 ? "var(--color-resolved)" : sla.timely_rate_pct >= 60 ? "var(--color-pending)" : "var(--color-breach)"}
        />
        <KpiCard
          icon={<Zap size={18} />}
          label="High Urgency"
          value={highUrgency.count.toLocaleString()}
          iconColor="var(--color-breach)"
          iconBg="var(--color-breach-bg)"
          valueColor={highUrgency.count > 0 ? "var(--color-breach)" : undefined}
        />
        <KpiCard
          icon={<ShieldAlert size={18} />}
          label="Untimely + High Risk"
          value={sla.high_urgency_untimely_count.toLocaleString()}
          iconColor={sla.high_urgency_untimely_count > 0 ? "var(--color-error)" : "var(--color-on-surface-variant)"}
          iconBg={sla.high_urgency_untimely_count > 0 ? "var(--color-breach-bg)" : "var(--color-surface-container)"}
          valueColor={sla.high_urgency_untimely_count > 0 ? "var(--color-error)" : undefined}
        />
      </div>

      {/* ── Main content: trend + product dist + high urgency + SLA ─────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16 }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Trend chart card */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <BarChart3 size={18} style={{ color: "var(--color-primary)" }} />
                <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                  Complaint Volume
                </span>
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                {(["week", "month"] as const).map((g) => (
                  <button
                    key={g}
                    onClick={() => setGranularity(g)}
                    className={granularity === g ? "btn-primary" : "btn-secondary"}
                    style={{ height: 28, padding: "0 12px", fontSize: 11 }}
                  >
                    {g === "week" ? "Weekly" : "Monthly"}
                  </button>
                ))}
              </div>
            </div>
            <div className="card-body" style={{ paddingBottom: 12 }}>
              <TrendChart
                data={trendData.items}
                height={160}
                color="var(--color-primary)"
                label="Complaint Volume Trend"
              />
              {/* Period labels */}
              {trendData.items.length > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                  <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>
                    {trendData.items[0]?.period}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>
                    {trendData.items[trendData.items.length - 1]?.period}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Product distribution */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                Top Products by Volume
              </span>
              <span className="badge-neutral">{topProducts.length} products</span>
            </div>
            <div style={{ padding: "12px 24px" }}>
              {topProducts.length === 0 ? (
                <p style={{ color: "var(--color-on-surface-variant)", fontSize: "var(--text-body-sm)", padding: "16px 0" }}>
                  No product data available
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {topProducts.map((p) => {
                    const pct = Math.round((p.count / maxProdCount) * 100);
                    return (
                      <div key={`${p.product}-${p.category}`}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                          <span style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", fontWeight: 500, maxWidth: "70%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {p.product ?? "Unknown"}
                          </span>
                          <span style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface-variant)" }}>
                            {p.count.toLocaleString()}
                          </span>
                        </div>
                        <div className="progress-bar">
                          <div
                            className="progress-fill"
                            style={{
                              width: `${pct}%`,
                              background: "var(--color-primary)",
                              opacity: 0.7 + pct * 0.003,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Recent complaints */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                Recent Complaints
              </span>
              <Link href="/queue" className="btn-ghost" style={{ height: 28, padding: "0 10px", fontSize: 11 }}>
                View all <ArrowRight size={12} />
              </Link>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Product</th>
                    <th>Sentiment</th>
                    <th>Urgency</th>
                    <th>Status</th>
                    <th>Received</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 24 }}>
                        No recent complaints
                      </td>
                    </tr>
                  ) : (
                    recent.map((c) => (
                      <tr
                        key={c.complaint_id}
                        onClick={() => window.location.assign(`/queue/${c.complaint_id}`)}
                      >
                        <td>
                          <span className="id-pill">{c.complaint_id.slice(0, 12)}…</span>
                        </td>
                        <td style={{ maxWidth: 140 }}>
                          <span style={{ fontSize: "var(--text-body-sm)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", maxWidth: 140 }}>
                            {c.product ?? "—"}
                          </span>
                        </td>
                        <td>
                          {c.sentiment ? (
                            <Badge variant={sentimentVariant(c.sentiment)}>{c.sentiment}</Badge>
                          ) : "—"}
                        </td>
                        <td>
                          <UrgencyBar score={c.urgency_score} />
                        </td>
                        <td>
                          <Badge variant={aiStatusVariant(c.ai_status)}>
                            {c.ai_status.replace("_", " ")}
                          </Badge>
                        </td>
                        <td style={{ whiteSpace: "nowrap", color: "var(--color-on-surface-variant)" }}>
                          {formatDate(c.date_received)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* SLA health card */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                SLA Health
              </span>
              <Badge variant={slaHealth.variant}>
                {slaHealth.label}
              </Badge>
            </div>
            <div className="card-body" style={{ paddingTop: 12 }}>
              {/* Big donut-style metric */}
              <div style={{ textAlign: "center", marginBottom: 16 }}>
                <div style={{ fontSize: 40, fontWeight: 700, color: slaHealth.color, lineHeight: 1.1 }}>
                  {Math.round(sla.timely_rate_pct)}%
                </div>
                <div style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface-variant)", marginTop: 2 }}>
                  timely response rate
                </div>
              </div>
              {/* Timely / Untimely bar */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", height: 8, borderRadius: 999, overflow: "hidden", gap: 2 }}>
                  <div style={{ flex: sla.timely_count, background: "var(--color-resolved)", borderRadius: 999 }} />
                  <div style={{ flex: sla.untimely_count, background: "var(--color-breach)", borderRadius: 999 }} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                  <span style={{ fontSize: 10, color: "var(--color-resolved)" }}>
                    ✓ Timely ({sla.timely_count.toLocaleString()})
                  </span>
                  <span style={{ fontSize: 10, color: "var(--color-breach)" }}>
                    ✗ Untimely ({sla.untimely_count.toLocaleString()})
                  </span>
                </div>
              </div>
              {/* Info rows */}
              <div>
                <div className="info-row">
                  <span className="info-label">Avg Urgency</span>
                  <span className="info-value">
                    {sla.avg_urgency_score != null ? Math.round(sla.avg_urgency_score) : "—"}/100
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">High Risk + Untimely</span>
                  <span className="info-value" style={{ color: sla.high_urgency_untimely_count > 0 ? "var(--color-error)" : "var(--color-resolved)" }}>
                    {sla.high_urgency_untimely_count}
                  </span>
                </div>
                {sla.period_from && (
                  <div className="info-row">
                    <span className="info-label">Period</span>
                    <span className="info-value" style={{ fontSize: 11 }}>
                      {formatDate(sla.period_from)} – {formatDate(sla.period_to)}
                    </span>
                  </div>
                )}
              </div>
              <Link href="/operations" className="btn-secondary" style={{ width: "100%", marginTop: 14, justifyContent: "center" }}>
                View Details <ArrowRight size={14} />
              </Link>
            </div>
          </div>

          {/* High urgency list */}
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Zap size={16} style={{ color: "var(--color-breach)" }} />
                <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>
                  High Urgency
                </span>
              </div>
              <Link href="/insights" className="btn-ghost" style={{ height: 28, padding: "0 10px", fontSize: 11 }}>
                View all
              </Link>
            </div>
            <div style={{ padding: "8px 0" }}>
              {highUrgency.items.length === 0 ? (
                <p style={{ padding: 16, color: "var(--color-on-surface-variant)", fontSize: "var(--text-body-sm)", textAlign: "center" }}>
                  No high urgency items
                </p>
              ) : (
                highUrgency.items.map((item) => (
                  <Link
                    key={item.complaint_id}
                    href={`/queue/${item.complaint_id}`}
                    style={{
                      display: "block",
                      padding: "10px 24px",
                      borderBottom: "1px solid var(--color-outline-variant)",
                      transition: "background 0.1s",
                    }}
                    className="hover-surface"
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", marginBottom: 2 }}>
                          {truncate(item.narrative, 80)}
                        </p>
                        <p style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>
                          {item.product ?? "Unknown"} · {formatRelative(item.created_at)}
                        </p>
                      </div>
                      <UrgencyBadge score={item.urgency_score} />
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function dashboardSlaHealth(sla: SLASummaryResponse): { label: "Healthy" | "At Risk" | "Critical"; variant: "success" | "warning" | "danger"; color: string } {
  if (sla.high_urgency_untimely_count > 0 || sla.timely_rate_pct < 70) {
    return { label: "Critical", variant: "danger", color: "var(--color-breach)" };
  }
  if (sla.timely_rate_pct < 90 || sla.untimely_count > 0) {
    return { label: "At Risk", variant: "warning", color: "var(--color-pending)" };
  }
  return { label: "Healthy", variant: "success", color: "var(--color-resolved)" };
}

function KpiCard({
  icon,
  label,
  value,
  sub,
  iconColor,
  iconBg,
  valueColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  iconColor: string;
  iconBg: string;
  valueColor?: string;
}) {
  return (
    <div className="stat-card" style={{ boxShadow: "var(--shadow-card)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: 8,
            background: iconBg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: iconColor,
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
        <span
          style={{
            fontSize: "var(--text-label-md)",
            color: "var(--color-on-surface-variant)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            fontWeight: 600,
          }}
        >
          {label}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 4 }}>
        <span
          style={{
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
            color: valueColor ?? "var(--color-on-background)",
          }}
        >
          {value}
        </span>
        {sub && (
          <span style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface-variant)" }}>
            {sub}
          </span>
        )}
      </div>
    </div>
  );
}

function UrgencyBar({ score }: { score: number | null | undefined }) {
  if (score == null) return <span style={{ color: "var(--color-on-surface-variant)" }}>—</span>;
  const color =
    score >= 70 ? "var(--color-breach)"
    : score >= 40 ? "var(--color-pending)"
    : "var(--color-resolved)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 48, height: 4, background: "var(--color-surface-container)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${score}%`, background: color, borderRadius: 999 }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 600 }}>{score}</span>
    </div>
  );
}

function UrgencyBadge({ score }: { score: number }) {
  const color =
    score >= 70 ? "var(--color-breach-text)"
    : score >= 40 ? "var(--color-pending-text)"
    : "var(--color-resolved-text)";
  const bg =
    score >= 70 ? "var(--color-breach-bg)"
    : score >= 40 ? "var(--color-pending-bg)"
    : "var(--color-resolved-bg)";
  return (
    <div
      style={{
        minWidth: 32,
        padding: "2px 8px",
        borderRadius: 999,
        background: bg,
        color,
        fontSize: 11,
        fontWeight: 700,
        textAlign: "center",
        flexShrink: 0,
      }}
    >
      {score}
    </div>
  );
}
