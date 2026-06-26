"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, BarChart3, TrendingUp } from "lucide-react";
import { getComplaintTrends, getHighUrgency, getHumanReviewTrends, getProductSummary } from "@/lib/api/analytics";
import { getSlaTrend } from "@/lib/api/sla";
import type { HighUrgencyResponse, ProductSummaryResponse, SLATrendResponse, TrendResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { TrendChart } from "@/components/ui/TrendChart";
import { formatDate, sentimentVariant } from "@/lib/utils/format";
import Link from "next/link";

type Tab = "trends" | "products" | "review" | "sla" | "urgency";
type Granularity = "week" | "month";

export default function InsightsPage() {
  const [tab, setTab] = useState<Tab>("trends");
  const [granularity, setGranularity] = useState<Granularity>("week");

  const [weekTrend, setWeekTrend] = useState<TrendResponse | null>(null);
  const [monthTrend, setMonthTrend] = useState<TrendResponse | null>(null);
  const [reviewTrend, setReviewTrend] = useState<TrendResponse | null>(null);
  const [products, setProducts] = useState<ProductSummaryResponse | null>(null);
  const [slaTrend, setSlaTrend] = useState<SLATrendResponse | null>(null);
  const [highUrgency, setHighUrgency] = useState<HighUrgencyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getComplaintTrends("week"),
      getComplaintTrends("month"),
      getHumanReviewTrends("week"),
      getProductSummary(),
      getSlaTrend("weekly"),
      getHighUrgency(25),
    ])
      .then(([wt, mt, rt, prod, sla, hu]) => {
        setWeekTrend(wt); setMonthTrend(mt); setReviewTrend(rt);
        setProducts(prod); setSlaTrend(sla); setHighUrgency(hu);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load insights"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner fullPage label="Loading insights…" />;
  if (error) return <div className="alert-error" style={{ maxWidth: 480, margin: "32px auto" }}><AlertTriangle size={14} />{error}</div>;

  const trendData = granularity === "week" ? weekTrend : monthTrend;
  const topProducts = [...(products?.items ?? [])].filter((p) => p.product).sort((a, b) => b.count - a.count).slice(0, 15);
  const maxProd = topProducts[0]?.count ?? 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Insights & Analytics</h1>
          <p className="page-subtitle">Complaint trends, product breakdown, review patterns, and SLA performance.</p>
        </div>
      </div>

      <div className="tab-bar">
        {([
          { id: "trends", label: "Complaint Trends" },
          { id: "products", label: "Product Breakdown" },
          { id: "review", label: "Human Review" },
          { id: "sla", label: "SLA Trend" },
          { id: "urgency", label: "High Urgency" },
        ] as const).map(({ id, label }) => (
          <button key={id} className={`tab-item ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      {/* ── Complaint Trends ──────────────────────────────────────────────── */}
      {tab === "trends" && trendData && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <BarChart3 size={18} style={{ color: "var(--color-primary)" }} />
                <span style={{ fontWeight: 600 }}>Complaint Volume</span>
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                {(["week", "month"] as const).map((g) => (
                  <button key={g} onClick={() => setGranularity(g)}
                    className={granularity === g ? "btn-primary" : "btn-secondary"}
                    style={{ height: 28, padding: "0 12px", fontSize: 11 }}>
                    {g === "week" ? "Weekly" : "Monthly"}
                  </button>
                ))}
              </div>
            </div>
            <div className="card-body">
              <TrendChart data={trendData.items} height={200} color="var(--color-primary)" label="Complaint Volume" />
            </div>
          </div>
          {/* Data table */}
          <div className="card">
            <div className="card-header"><span style={{ fontWeight: 600 }}>Period Detail</span></div>
            <table className="data-table">
              <thead><tr><th>Period</th><th>Count</th></tr></thead>
              <tbody>
                {trendData.items.length === 0 ? (
                  <tr><td colSpan={2} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 20 }}>No data</td></tr>
                ) : trendData.items.map((point) => (
                  <tr key={point.period}>
                    <td>{point.period}</td>
                    <td style={{ fontWeight: 600 }}>{point.count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Product Breakdown ─────────────────────────────────────────────── */}
      {tab === "products" && (
        <div className="card">
          <div className="card-header">
            <span style={{ fontWeight: 600 }}>Product Distribution</span>
            <Badge variant="neutral">{topProducts.length} products</Badge>
          </div>
          <div style={{ padding: "16px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
            {topProducts.length === 0 ? (
              <p style={{ color: "var(--color-on-surface-variant)", fontSize: "var(--text-body-sm)" }}>No product data available</p>
            ) : topProducts.map((p) => {
              const pct = Math.round((p.count / maxProd) * 100);
              const avgUrgency = p.avg_urgency != null ? Math.round(p.avg_urgency) : null;
              return (
                <div key={`${p.product}-${p.category}`}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, alignItems: "baseline" }}>
                    <span style={{ fontSize: "var(--text-body-sm)", fontWeight: 600, maxWidth: "65%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.product}
                    </span>
                    <div style={{ display: "flex", gap: 16, fontSize: 12 }}>
                      <span style={{ color: "var(--color-on-surface-variant)" }}>
                        {p.count.toLocaleString()} complaints
                      </span>
                      {avgUrgency != null && (
                        <span style={{ color: avgUrgency >= 70 ? "var(--color-breach)" : avgUrgency >= 40 ? "var(--color-pending)" : "var(--color-resolved)", fontWeight: 600 }}>
                          Urgency: {avgUrgency}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${pct}%`, background: "var(--color-primary)", opacity: 0.6 + pct * 0.004 }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Human Review Trend ────────────────────────────────────────────── */}
      {tab === "review" && reviewTrend && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {[
              { label: "Total Periods", value: reviewTrend.items.length },
              { label: "Total Reviews", value: reviewTrend.items.reduce((s, d) => s + d.count, 0).toLocaleString() },
              { label: "Avg Per Period", value: reviewTrend.items.length > 0 ? Math.round(reviewTrend.items.reduce((s, d) => s + d.count, 0) / reviewTrend.items.length) : 0 },
            ].map(({ label, value }) => (
              <div key={label} className="stat-card">
                <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-on-surface-variant)", fontWeight: 600 }}>{label}</span>
                <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em" }}>{value}</span>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <TrendingUp size={18} style={{ color: "var(--color-pending)" }} />
                <span style={{ fontWeight: 600 }}>Human Review Trend (Weekly)</span>
              </div>
            </div>
            <div className="card-body">
              <TrendChart data={reviewTrend.items} height={180} color="var(--color-pending)" label="Human Review Trend" />
            </div>
          </div>
        </div>
      )}

      {/* ── SLA Trend ─────────────────────────────────────────────────────── */}
      {tab === "sla" && slaTrend && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <div className="card-header"><span style={{ fontWeight: 600 }}>Timely Response Trend ({slaTrend.granularity})</span></div>
            <div className="card-body">
              <TrendChart
                data={slaTrend.items.map((i) => ({ period: i.period, count: i.timely }))}
                height={180}
                color="var(--color-resolved)"
                label="Timely SLA Trend"
              />
            </div>
          </div>
          <div className="card">
            <div className="card-header"><span style={{ fontWeight: 600 }}>SLA Period Detail</span></div>
            <table className="data-table">
              <thead><tr><th>Period</th><th>Total</th><th>Timely</th><th>Untimely</th><th>Timely Rate</th></tr></thead>
              <tbody>
                {slaTrend.items.length === 0 ? (
                  <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 20 }}>No SLA trend data</td></tr>
                ) : slaTrend.items.map((row) => (
                  <tr key={row.period}>
                    <td style={{ fontWeight: 500 }}>{row.period}</td>
                    <td>{row.total.toLocaleString()}</td>
                    <td style={{ color: "var(--color-resolved)" }}>{row.timely.toLocaleString()}</td>
                    <td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit" }}>{row.untimely.toLocaleString()}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div className="progress-bar" style={{ width: 70 }}>
                          <div className="progress-fill" style={{ width: `${row.timely_rate_pct}%`, background: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-pending)" }} />
                        </div>
                        <span style={{ fontWeight: 600, fontSize: 12, color: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-breach)" }}>
                          {Math.round(row.timely_rate_pct)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── High Urgency ──────────────────────────────────────────────────── */}
      {tab === "urgency" && highUrgency && (
        <div className="card">
          <div className="card-header">
            <span style={{ fontWeight: 600 }}>High Urgency Complaints</span>
            <Badge variant={highUrgency.count > 0 ? "danger" : "neutral"}>{highUrgency.count} total</Badge>
          </div>
          <table className="data-table">
            <thead><tr><th>Complaint ID</th><th>Product</th><th>Channel</th><th>Urgency</th><th>Sentiment</th><th>Created</th></tr></thead>
            <tbody>
              {highUrgency.items.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 24 }}>No high urgency complaints</td></tr>
              ) : highUrgency.items.map((item) => (
                <tr key={item.complaint_id} onClick={() => window.location.assign(`/queue/${item.complaint_id}`)}>
                  <td><span className="id-pill">{item.complaint_id.slice(0, 14)}…</span></td>
                  <td style={{ maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.product ?? "—"}</td>
                  <td>{item.channel ?? "—"}</td>
                  <td>
                    <span style={{ fontWeight: 700, color: item.urgency_score >= 80 ? "var(--color-breach)" : item.urgency_score >= 60 ? "var(--color-pending)" : "inherit" }}>
                      {item.urgency_score}
                    </span>
                  </td>
                  <td>{item.sentiment ? <Badge variant={sentimentVariant(item.sentiment)}>{item.sentiment}</Badge> : "—"}</td>
                  <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>{formatDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
