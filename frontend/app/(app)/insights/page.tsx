"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  MessageSquare,
  Shield,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  getComplaintTrends,
  getComplaintVolumeInsights,
  getHighUrgency,
  getHumanReviewTrends,
  getProductSummary,
  type ComplaintVolumeGroupBy,
} from "@/lib/api/analytics";
import {
  getSlaByChannel,
  getSlaByProduct,
  getSlaTrend,
} from "@/lib/api/sla";
import type {
  ComplaintVolumeInsightsResponse,
  HighUrgencyResponse,
  ProductSummaryResponse,
  SLAGroupedResponse,
  SLATrendResponse,
  TrendResponse,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { EChart } from "@/components/ui/EChart";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { TrendChart } from "@/components/ui/TrendChart";
import { formatDate, sentimentVariant } from "@/lib/utils/format";

type Tab = "trends" | "products" | "review" | "sla" | "urgency";
type Granularity = "week" | "month";
type SlaGroupMode = "product" | "channel";

export default function InsightsPage() {
  const [tab, setTab] = useState<Tab>("trends");
  const [granularity, setGranularity] = useState<Granularity>("week");
  const [slaGroupMode, setSlaGroupMode] = useState<SlaGroupMode>("product");
  const [urgencyThreshold, setUrgencyThreshold] = useState(70);

  const [weekTrend, setWeekTrend] = useState<TrendResponse | null>(null);
  const [monthTrend, setMonthTrend] = useState<TrendResponse | null>(null);
  const [reviewTrend, setReviewTrend] = useState<TrendResponse | null>(null);
  const [products, setProducts] = useState<ProductSummaryResponse | null>(null);
  const [slaTrend, setSlaTrend] = useState<SLATrendResponse | null>(null);
  const [slaGrouped, setSlaGrouped] = useState<SLAGroupedResponse | null>(null);
  const [highUrgency, setHighUrgency] = useState<HighUrgencyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getComplaintTrends("week"),
      getComplaintTrends("month"),
      getHumanReviewTrends("week"),
      getProductSummary(),
      getSlaTrend("weekly"),
      getHighUrgency(25),
    ])
      .then(([wt, mt, rt, prod, sla, hu]) => {
        setWeekTrend(wt);
        setMonthTrend(mt);
        setReviewTrend(rt);
        setProducts(prod);
        setSlaTrend(sla);
        setHighUrgency(hu);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load insights"))
      .finally(() => setLoading(false));
  }, []);

  // Reload SLA grouping when toggle changes
  useEffect(() => {
    (slaGroupMode === "product" ? getSlaByProduct() : getSlaByChannel())
      .then(setSlaGrouped)
      .catch(() => null);
  }, [slaGroupMode]);

  if (loading) return <LoadingSpinner fullPage label="Loading insights…" />;

  if (error) {
    return (
      <div className="alert-error" style={{ maxWidth: 480, margin: "32px auto" }}>
        <AlertTriangle size={14} />
        {error}
      </div>
    );
  }

  const trendData = granularity === "week" ? weekTrend : monthTrend;
  const topProducts = [...(products?.items ?? [])]
    .filter((p) => p.product)
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);
  const maxProd = topProducts[0]?.count ?? 1;

  const totalReviews = reviewTrend?.items.reduce((s, d) => s + d.count, 0) ?? 0;
  const avgReviews =
    reviewTrend && reviewTrend.items.length > 0
      ? Math.round(totalReviews / reviewTrend.items.length)
      : 0;

  const filteredHighUrgency =
    highUrgency?.items.filter((i) => i.urgency_score >= urgencyThreshold) ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Insights & Analytics</h1>
          <p className="page-subtitle">
            Complaint trends, product breakdown, review patterns, and SLA performance.
          </p>
        </div>
      </div>

      {/* ── Tab bar ───────────────────────────────────────────────────────── */}
      <div className="tab-bar">
        {(
          [
            { id: "trends", label: "Complaint Trends", icon: <BarChart3 size={13} /> },
            { id: "products", label: "Product Breakdown", icon: <TrendingUp size={13} /> },
            { id: "review", label: "Human Review", icon: <MessageSquare size={13} /> },
            { id: "sla", label: "SLA Trend", icon: <Shield size={13} /> },
            { id: "urgency", label: "High Urgency", icon: <Zap size={13} /> },
          ] as const
        ).map(({ id, label, icon }) => (
          <button
            key={id}
            className={`tab-item ${tab === id ? "active" : ""}`}
            onClick={() => setTab(id)}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
              {icon}
              {label}
            </span>
          </button>
        ))}
      </div>

      {/* ── Complaint Trends ──────────────────────────────────────────────── */}
      {tab === "trends" && (
        <ComplaintTrendsCockpit granularity={granularity} setGranularity={setGranularity} />
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
              <p style={{ color: "var(--color-on-surface-variant)", fontSize: "var(--text-body-sm)" }}>
                No product data available
              </p>
            ) : (
              topProducts.map((p) => {
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
                      <div
                        className="progress-fill"
                        style={{ width: `${pct}%`, background: "var(--color-primary)", opacity: 0.55 + pct * 0.004 }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ── Human Review Trend ────────────────────────────────────────────── */}
      {tab === "review" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Stats row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {[
              { label: "Total Periods", value: reviewTrend?.items.length ?? 0 },
              { label: "Total Reviews", value: totalReviews.toLocaleString() },
              { label: "Avg Per Period", value: avgReviews },
            ].map(({ label, value }) => (
              <div key={label} className="stat-card">
                <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-on-surface-variant)", fontWeight: 600 }}>
                  {label}
                </span>
                <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em" }}>{value}</span>
              </div>
            ))}
          </div>
          {/* Chart */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <TrendingUp size={18} style={{ color: "var(--color-pending)" }} />
                <span style={{ fontWeight: 600 }}>Human Review Trend (Weekly)</span>
              </div>
            </div>
            <div className="card-body">
              {reviewTrend && reviewTrend.items.length > 0 ? (
                <TrendChart
                  data={reviewTrend.items}
                  height={180}
                  color="var(--color-pending)"
                  label="Human Review Trend"
                />
              ) : (
                <p style={{ color: "var(--color-on-surface-variant)", textAlign: "center", padding: 32 }}>
                  No review trend data
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── SLA Trend ─────────────────────────────────────────────────────── */}
      {tab === "sla" && slaTrend && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Chart */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600 }}>
                Timely Response Trend ({slaTrend.granularity})
              </span>
            </div>
            <div className="card-body">
              <TrendChart
                data={slaTrend.items.map((i) => ({ period: i.period, count: i.timely }))}
                height={180}
                color="var(--color-resolved)"
                label="Timely SLA Trend"
              />
            </div>
          </div>

          {/* Grouped SLA breakdown with toggle */}
          <div className="card">
            <div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 600 }}>SLA Breakdown</span>
              <div style={{ display: "flex", gap: 4 }}>
                {(["product", "channel"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setSlaGroupMode(mode)}
                    className={slaGroupMode === mode ? "btn-primary" : "btn-secondary"}
                    style={{ height: 28, padding: "0 12px", fontSize: 11 }}
                  >
                    {mode === "product" ? "By Product" : "By Channel"}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{slaGroupMode === "product" ? "Product" : "Channel"}</th>
                    <th>Total</th>
                    <th>Timely</th>
                    <th>Untimely</th>
                    <th>Rate</th>
                    <th>Avg Urgency</th>
                  </tr>
                </thead>
                <tbody>
                  {!slaGrouped || slaGrouped.items.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 20 }}>
                        No data
                      </td>
                    </tr>
                  ) : (
                    slaGrouped.items.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 500, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {slaGroupMode === "product" ? row.product ?? "Unknown" : row.channel ?? "Unknown"}
                        </td>
                        <td>{row.total.toLocaleString()}</td>
                        <td style={{ color: "var(--color-resolved)" }}>{row.timely.toLocaleString()}</td>
                        <td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit" }}>
                          {row.untimely.toLocaleString()}
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <div className="progress-bar" style={{ width: 60 }}>
                              <div
                                className="progress-fill"
                                style={{
                                  width: `${row.timely_rate_pct}%`,
                                  background: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-pending)",
                                }}
                              />
                            </div>
                            <span style={{ fontWeight: 600, fontSize: 12, color: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-breach)" }}>
                              {Math.round(row.timely_rate_pct)}%
                            </span>
                          </div>
                        </td>
                        <td>{row.avg_urgency_score != null ? Math.round(row.avg_urgency_score) : "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Period detail table */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600 }}>SLA Period Detail</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Total</th>
                  <th>Timely</th>
                  <th>Untimely</th>
                  <th>Timely Rate</th>
                </tr>
              </thead>
              <tbody>
                {slaTrend.items.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 20 }}>
                      No SLA trend data
                    </td>
                  </tr>
                ) : (
                  slaTrend.items.map((row) => (
                    <tr key={row.period}>
                      <td style={{ fontWeight: 500 }}>{row.period}</td>
                      <td>{row.total.toLocaleString()}</td>
                      <td style={{ color: "var(--color-resolved)" }}>{row.timely.toLocaleString()}</td>
                      <td style={{ color: row.untimely > 0 ? "var(--color-breach)" : "inherit" }}>
                        {row.untimely.toLocaleString()}
                      </td>
                      <td style={{ fontWeight: 600, color: row.timely_rate_pct >= 80 ? "var(--color-resolved)" : "var(--color-breach)" }}>
                        {Math.round(row.timely_rate_pct)}%
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── High Urgency ──────────────────────────────────────────────────── */}
      {tab === "urgency" && (
        <div className="card">
          <div className="card-header" style={{ gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 600 }}>High Urgency Complaints</span>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <label style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface-variant)", display: "flex", alignItems: "center", gap: 6 }}>
                Threshold:
                <strong style={{ color: urgencyThreshold >= 80 ? "var(--color-breach)" : "var(--color-pending)" }}>
                  {urgencyThreshold}+
                </strong>
              </label>
              <input
                type="range"
                min={50}
                max={95}
                step={5}
                value={urgencyThreshold}
                onChange={(e) => setUrgencyThreshold(Number(e.target.value))}
                style={{ width: 140 }}
              />
              <Badge variant={filteredHighUrgency.length > 0 ? "danger" : "neutral"}>
                {filteredHighUrgency.length} complaints
              </Badge>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Complaint ID</th>
                  <th>Product</th>
                  <th>Channel</th>
                  <th>Urgency</th>
                  <th>Sentiment</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {filteredHighUrgency.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", color: "var(--color-on-surface-variant)", padding: 24 }}>
                      No complaints above urgency {urgencyThreshold}
                    </td>
                  </tr>
                ) : (
                  filteredHighUrgency.map((item) => (
                    <tr
                      key={item.complaint_id}
                      onClick={() => window.location.assign(`/queue/${item.complaint_id}`)}
                    >
                      <td>
                        <span className="id-pill">{item.complaint_id.slice(0, 14)}…</span>
                      </td>
                      <td style={{ maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {item.product ?? "—"}
                      </td>
                      <td>{item.channel ?? "—"}</td>
                      <td>
                        <span style={{ fontWeight: 700, color: item.urgency_score >= 80 ? "var(--color-breach)" : "var(--color-pending)" }}>
                          {item.urgency_score}
                        </span>
                      </td>
                      <td>
                        {item.sentiment ? (
                          <Badge variant={sentimentVariant(item.sentiment)}>{item.sentiment}</Badge>
                        ) : "—"}
                      </td>
                      <td style={{ fontSize: 11, color: "var(--color-on-surface-variant)", whiteSpace: "nowrap" }}>
                        {formatDate(item.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function ComplaintTrendsCockpit({
  granularity,
  setGranularity,
}: {
  granularity: "week" | "month";
  setGranularity: (g: "week" | "month") => void;
}) {
  const [data, setData] = useState<ComplaintVolumeInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"volume" | "driver" | "heatmap" | "mix">("volume");
  const [groupBy, setGroupBy] = useState<ComplaintVolumeGroupBy>("product");
  const [selectedInsight, setSelectedInsight] = useState<string>("Click any chart element or card to inspect specific driver metrics.");

  useEffect(() => {
    setLoading(true);
    getComplaintVolumeInsights({ granularity, group_by: groupBy, limit: 15 })
      .then(setData)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [granularity, groupBy]);

  if (loading) return <LoadingSpinner fullPage label="Computing ECharts volume insights…" />;
  if (!data) return <p style={{ padding: 32, textAlign: "center" }}>No volume insights available.</p>;

  const { summary, timeline, groups, heatmap, sentiment_mix, samples } = data;

  let chartOption: Record<string, any> = {};
  if (mode === "volume") {
    chartOption = {
      tooltip: { trigger: "axis" },
      legend: { data: ["Total Volume", "High Urgency"], textStyle: { color: "#888" } },
      grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: "category", data: timeline.map((t) => t.period), axisLabel: { color: "#888" } },
      yAxis: { type: "value", axisLabel: { color: "#888" } },
      series: [
        { name: "Total Volume", type: "bar", data: timeline.map((t) => t.total), itemStyle: { color: "#6366f1", borderRadius: [4, 4, 0, 0] } },
        { name: "High Urgency", type: "line", data: timeline.map((t) => t.high_urgency), lineStyle: { color: "#ef4444", width: 3 } },
      ],
    };
  } else if (mode === "driver") {
    chartOption = {
      tooltip: { trigger: "axis" },
      grid: { left: 140, right: 20, top: 20, bottom: 30 },
      xAxis: { type: "value", axisLabel: { color: "#888" } },
      yAxis: { type: "category", data: [...groups].map((g) => g.group).reverse(), axisLabel: { color: "#888" } },
      series: [
        { name: "Complaints", type: "bar", data: [...groups].map((g) => g.count).reverse(), itemStyle: { color: "#3b82f6", borderRadius: [0, 4, 4, 0] } },
      ],
    };
  } else if (mode === "heatmap") {
    const productsList = Array.from(new Set(heatmap.map((h) => h.product)));
    const channelsList = Array.from(new Set(heatmap.map((h) => h.channel)));
    const scatterData = heatmap.map((h) => [productsList.indexOf(h.product), channelsList.indexOf(h.channel), h.count]);
    chartOption = {
      tooltip: { formatter: (p: { value: number[] }) => `${productsList[p.value[0]]} × ${channelsList[p.value[1]]}: ${p.value[2]}` },
      grid: { left: 110, bottom: 60, top: 20, right: 20 },
      xAxis: { type: "category", data: productsList, axisLabel: { rotate: 30, color: "#888" } },
      yAxis: { type: "category", data: channelsList, axisLabel: { color: "#888" } },
      visualMap: { min: 0, max: Math.max(...heatmap.map((h) => h.count), 1), calculable: true, orient: "horizontal", left: "center", bottom: 0 },
      series: [{ type: "heatmap", data: scatterData }],
    };
  } else {
    chartOption = {
      tooltip: { trigger: "item" },
      legend: { orient: "vertical", left: "left", textStyle: { color: "#888" } },
      series: [
        { name: "Sentiment Mix", type: "pie", radius: ["40%", "70%"], data: sentiment_mix.map((m) => ({ name: m.label, value: m.count })) },
      ],
    };
  }

  const handleChartClick = (p: { name?: string; seriesName?: string; value?: unknown; data?: unknown }) => {
    setSelectedInsight(`Inspected point [${p.name ?? p.seriesName ?? "Chart"}]: Metric Value = ${String(p.value ?? p.data)}`);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* KPI Analysis Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14 }}>
        <div
          className={`card stat-card ${mode === "volume" ? "active-mode" : ""}`}
          onClick={() => setMode("volume")}
          style={{ cursor: "pointer", border: mode === "volume" ? "2px solid var(--color-primary)" : undefined }}
        >
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--color-on-surface-variant)" }}>📊 Volume pulse</span>
          <span style={{ fontSize: 26, fontWeight: 700 }}>{summary.total_count.toLocaleString()}</span>
          <span style={{ fontSize: 12, color: "var(--color-on-surface-variant)" }}>Peak: {summary.peak_count}</span>
        </div>
        <div
          className={`card stat-card ${mode === "driver" ? "active-mode" : ""}`}
          onClick={() => setMode("driver")}
          style={{ cursor: "pointer", border: mode === "driver" ? "2px solid var(--color-primary)" : undefined }}
        >
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--color-on-surface-variant)" }}>🎯 Top driver</span>
          <span style={{ fontSize: 18, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{groups[0]?.group ?? "—"}</span>
          <span style={{ fontSize: 12, color: "var(--color-primary)" }}>{groups[0]?.count ?? 0} complaints</span>
        </div>
        <div
          className={`card stat-card ${mode === "heatmap" ? "active-mode" : ""}`}
          onClick={() => setMode("heatmap")}
          style={{ cursor: "pointer", border: mode === "heatmap" ? "2px solid var(--color-primary)" : undefined }}
        >
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--color-on-surface-variant)" }}>🔥 Hotspots</span>
          <span style={{ fontSize: 18, fontWeight: 700 }}>{heatmap[0]?.product ?? "—"}</span>
          <span style={{ fontSize: 12, color: "var(--color-on-surface-variant)" }}>{heatmap[0]?.channel ?? "—"}</span>
        </div>
        <div
          className={`card stat-card ${mode === "mix" ? "active-mode" : ""}`}
          onClick={() => setMode("mix")}
          style={{ cursor: "pointer", border: mode === "mix" ? "2px solid var(--color-primary)" : undefined }}
        >
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--color-on-surface-variant)" }}>⚠️ Risk mix</span>
          <span style={{ fontSize: 26, fontWeight: 700 }}>{summary.negative_count}</span>
          <span style={{ fontSize: 12, color: "var(--color-breach)" }}>Negative sentiment</span>
        </div>
      </div>

      {/* Main Graph & Insight Panel Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 16 }}>
        <div className="card">
          <div className="card-header" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
            <span style={{ fontWeight: 600 }}>Interactive Cockpit ({mode.toUpperCase()})</span>
            <div style={{ display: "flex", gap: 6 }}>
              {mode === "driver" &&
                (["product", "channel", "category"] as const).map((gb) => (
                  <button key={gb} className={groupBy === gb ? "btn-primary" : "btn-secondary"} style={{ height: 26, fontSize: 11, padding: "0 8px" }} onClick={() => setGroupBy(gb)}>
                    {gb}
                  </button>
                ))}
              {(["week", "month"] as const).map((g) => (
                <button key={g} className={granularity === g ? "btn-primary" : "btn-secondary"} style={{ height: 26, fontSize: 11, padding: "0 8px" }} onClick={() => setGranularity(g)}>
                  {g}
                </button>
              ))}
            </div>
          </div>
          <div className="card-body">
            <EChart option={chartOption} height={300} onClick={handleChartClick as (p: unknown) => void} />
          </div>
        </div>

        <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12, background: "var(--color-surface-variant-subtle)" }}>
          <h4 style={{ fontSize: 14, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>💡 Live Insight Panel</h4>
          <p style={{ fontSize: 13, lineHeight: 1.5, color: "var(--color-on-surface)" }}>{selectedInsight}</p>
          <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "var(--color-on-surface-variant)" }}>Summary Averages:</span>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span>Avg Urgency Score:</span>
              <strong>{summary.avg_urgency ?? "—"}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span>Human Review Count:</span>
              <strong>{summary.human_review_count}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Driver Table & Samples Queue */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
        <div className="card">
          <div className="card-header">
            <span style={{ fontWeight: 600 }}>Driver Breakdown Table</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Driver Group</th>
                  <th>Count</th>
                  <th>Avg Urgency</th>
                  <th>High Urgency</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => (
                  <tr key={g.group}>
                    <td style={{ fontWeight: 500 }}>{g.group}</td>
                    <td style={{ fontWeight: 700 }}>{g.count}</td>
                    <td>{g.avg_urgency ?? "—"}</td>
                    <td style={{ color: g.high_urgency > 0 ? "var(--color-breach)" : "inherit" }}>{g.high_urgency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span style={{ fontWeight: 600 }}>Complaints To Inspect</span>
            <Badge variant="neutral">{samples.length} items</Badge>
          </div>
          <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10, maxHeight: 350, overflowY: "auto" }}>
            {samples.map((s) => (
              <div
                key={s.complaint_id}
                onClick={() => window.location.assign(`/queue/${s.complaint_id}`)}
                style={{
                  padding: 10,
                  borderRadius: 6,
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>{s.complaint_id.slice(0, 14)}…</span>
                  <Badge variant={s.urgency_score && s.urgency_score >= 70 ? "danger" : "neutral"}>Urg: {s.urgency_score ?? "—"}</Badge>
                </div>
                <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                  {s.narrative}
                </p>
                <div style={{ display: "flex", gap: 8, fontSize: 10, color: "var(--color-on-surface-variant)" }}>
                  <span>{s.product ?? "General"}</span>•<span>{s.channel ?? "Web"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
