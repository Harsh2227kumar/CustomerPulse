import { ArrowLeft, BarChart3, Gauge, Loader2, RefreshCcw, ShieldAlert, TrendingUp } from "lucide-react";
import { type CSSProperties, useEffect, useMemo, useState } from "react";
import {
  getComplaintTrends,
  getHighUrgency,
  getHumanReviewTrends,
  getProductSummary,
  getSlaBreachRisk,
  getSlaByChannel,
  getSlaByProduct,
  getSlaSummary,
  getSlaTrend,
} from "./api/client";
import type {
  HighUrgencyResponse,
  ProductSummaryResponse,
  SLAGroupedResponse,
  SLABreachRiskResponse,
  SLASummaryResponse,
  SLATrendResponse,
  TrendResponse,
} from "./types";

interface AnalyticsPageProps {
  onBack: () => void;
}

interface AnalyticsState {
  complaintTrend: TrendResponse | null;
  humanReviewTrend: TrendResponse | null;
  productSummary: ProductSummaryResponse | null;
  highUrgency: HighUrgencyResponse | null;
  slaSummary: SLASummaryResponse | null;
  slaByProduct: SLAGroupedResponse | null;
  slaByChannel: SLAGroupedResponse | null;
  slaBreachRisk: SLABreachRiskResponse | null;
  slaTrend: SLATrendResponse | null;
}

const emptyAnalytics: AnalyticsState = {
  complaintTrend: null,
  humanReviewTrend: null,
  productSummary: null,
  highUrgency: null,
  slaSummary: null,
  slaByProduct: null,
  slaByChannel: null,
  slaBreachRisk: null,
  slaTrend: null,
};

function percent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "0%";
  return `${Math.round(value)}%`;
}

function compactNumber(value: number | null | undefined): string {
  return new Intl.NumberFormat(undefined, { notation: "compact" }).format(value ?? 0);
}

function polylinePoints(values: number[], width = 260, height = 96): string {
  if (!values.length) return "";
  const max = Math.max(...values, 1);
  return values
    .map((value, index) => {
      const x = values.length === 1 ? 10 : 10 + (index * (width - 20)) / (values.length - 1);
      const y = height - 10 - (value / max) * (height - 24);
      return `${x},${y}`;
    })
    .join(" ");
}

function DonutMetric({ value, label, detail }: { value: number; label: string; detail: string }) {
  const safe = Math.max(0, Math.min(100, value));
  return (
    <div className="analytics-donut" style={{ "--donut": `${safe}%` } as CSSProperties}>
      <strong>{Math.round(safe)}%</strong>
      <span>{label}</span>
      <small>{detail}</small>
    </div>
  );
}

function TrendCard({ title, subtitle, values, labels }: { title: string; subtitle: string; values: number[]; labels: string[] }) {
  const points = polylinePoints(values);
  return (
    <article className="panel analytics-card trend-card">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <TrendingUp size={18} />
      </div>
      {points ? (
        <>
          <svg viewBox="0 0 260 96" role="img" aria-label={title}>
            <polyline points={`10,86 ${points} 250,86`} fill="rgba(46, 198, 166, 0.14)" stroke="none" />
            <polyline points={points} fill="none" stroke="#164f47" strokeWidth="3" strokeLinecap="round" />
          </svg>
          <div className="trend-labels">
            <span>{labels[0] ?? "Start"}</span>
            <strong>{compactNumber(values.reduce((sum, item) => sum + item, 0))} total</strong>
            <span>{labels[labels.length - 1] ?? "Latest"}</span>
          </div>
        </>
      ) : (
        <p className="analytics-empty">No trend data yet.</p>
      )}
    </article>
  );
}

function RankedBars({
  title,
  subtitle,
  rows,
  labelFor,
  valueFor,
  suffix = "",
}: {
  title: string;
  subtitle: string;
  rows: unknown[];
  labelFor: (row: unknown) => string;
  valueFor: (row: unknown) => number;
  suffix?: string;
}) {
  const max = Math.max(...rows.map(valueFor), 1);
  return (
    <article className="panel analytics-card ranked-card">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <BarChart3 size={18} />
      </div>
      <div className="ranked-bars">
        {rows.length ? rows.map((row, index) => {
          const value = valueFor(row);
          return (
            <div key={`${labelFor(row)}-${index}`} className="ranked-row">
              <span>{labelFor(row)}</span>
              <div><i style={{ width: `${Math.max(4, (value / max) * 100)}%` }} /></div>
              <strong>{compactNumber(value)}{suffix}</strong>
            </div>
          );
        }) : <p className="analytics-empty">No grouped data returned.</p>}
      </div>
    </article>
  );
}

export function AnalyticsPage({ onBack }: AnalyticsPageProps) {
  const [data, setData] = useState<AnalyticsState>(emptyAnalytics);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadAnalytics() {
    setLoading(true);
    setError(null);
    try {
      const [
        complaintTrend,
        humanReviewTrend,
        productSummary,
        highUrgency,
        slaSummary,
        slaByProduct,
        slaByChannel,
        slaBreachRisk,
        slaTrend,
      ] = await Promise.all([
        getComplaintTrends(),
        getHumanReviewTrends(),
        getProductSummary(),
        getHighUrgency(12),
        getSlaSummary(),
        getSlaByProduct(),
        getSlaByChannel(),
        getSlaBreachRisk(),
        getSlaTrend(),
      ]);
      setData({
        complaintTrend,
        humanReviewTrend,
        productSummary,
        highUrgency,
        slaSummary,
        slaByProduct,
        slaByChannel,
        slaBreachRisk,
        slaTrend,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load analytics");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, []);

  const complaintValues = useMemo(() => data.complaintTrend?.items.map((item) => item.count) ?? [], [data.complaintTrend]);
  const complaintLabels = useMemo(() => data.complaintTrend?.items.map((item) => item.period) ?? [], [data.complaintTrend]);
  const reviewValues = useMemo(() => data.humanReviewTrend?.items.map((item) => item.count) ?? [], [data.humanReviewTrend]);
  const reviewLabels = useMemo(() => data.humanReviewTrend?.items.map((item) => item.period) ?? [], [data.humanReviewTrend]);
  const slaTrendValues = useMemo(() => data.slaTrend?.items.map((item) => item.untimely) ?? [], [data.slaTrend]);
  const slaTrendLabels = useMemo(() => data.slaTrend?.items.map((item) => item.period) ?? [], [data.slaTrend]);

  const totalProductRows = data.productSummary?.items.reduce((sum, row) => sum + row.count, 0) ?? 0;
  const highUrgencyAverage = data.highUrgency?.items.length
    ? data.highUrgency.items.reduce((sum, row) => sum + row.urgency_score, 0) / data.highUrgency.items.length
    : 0;

  return (
    <main className="analytics-page">
      <header className="queue-page-header analytics-header">
        <div>
          <button className="icon-button" type="button" onClick={onBack} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>Analytics Command Center</h1>
            <p>Backend-powered complaint trends, SLA health, urgency risk, products, and channels</p>
          </div>
        </div>
        <button className="primary-action compact-action" type="button" onClick={loadAnalytics} disabled={loading}>
          {loading ? <Loader2 className="spin" size={15} /> : <RefreshCcw size={15} />} Refresh analytics
        </button>
      </header>

      {error ? <div className="ops-banner error">{error}</div> : null}

      <section className="analytics-kpis">
        <article className="metric-card">
          <span>Total SLA Cases</span>
          <Gauge size={24} />
          <strong>{compactNumber(data.slaSummary?.total_complaints)}</strong>
        </article>
        <article className="metric-card">
          <span>Timely Response Rate</span>
          <Gauge size={24} />
          <strong>{percent(data.slaSummary?.timely_rate_pct)}</strong>
        </article>
        <article className="metric-card">
          <span>High Urgency Queue</span>
          <ShieldAlert size={24} />
          <strong>{compactNumber(data.highUrgency?.count)}</strong>
        </article>
        <article className="metric-card">
          <span>Product Groups</span>
          <BarChart3 size={24} />
          <strong>{compactNumber(data.productSummary?.items.length)}</strong>
        </article>
      </section>

      {loading ? (
        <div className="loading-row"><Loader2 className="spin" size={18} />Loading backend analytics</div>
      ) : (
        <>
          <section className="analytics-grid">
            <TrendCard
              title="Complaint Volume Trend"
              subtitle={`${data.complaintTrend?.granularity ?? "monthly"} backend aggregation`}
              values={complaintValues}
              labels={complaintLabels}
            />
            <TrendCard
              title="Human Review Trend"
              subtitle="Cases routed to human review over time"
              values={reviewValues}
              labels={reviewLabels}
            />
            <TrendCard
              title="Untimely SLA Trend"
              subtitle={`${data.slaTrend?.granularity ?? "monthly"} untimely response movement`}
              values={slaTrendValues}
              labels={slaTrendLabels}
            />
          </section>

          <section className="analytics-mixed-grid">
            <article className="panel analytics-card donut-panel">
              <div className="panel-heading">
                <div>
                  <h2>SLA Health</h2>
                  <p>Timely, untimely, and urgent untimely response split</p>
                </div>
                <Gauge size={18} />
              </div>
              <div className="donut-row">
                <DonutMetric
                  value={data.slaSummary?.timely_rate_pct ?? 0}
                  label="Timely"
                  detail={`${compactNumber(data.slaSummary?.timely_count)} on time`}
                />
                <DonutMetric
                  value={data.slaSummary?.total_complaints ? ((data.slaSummary.untimely_count / data.slaSummary.total_complaints) * 100) : 0}
                  label="Untimely"
                  detail={`${compactNumber(data.slaSummary?.untimely_count)} delayed`}
                />
                <DonutMetric
                  value={data.slaSummary?.total_complaints ? ((data.slaSummary.high_urgency_untimely_count / data.slaSummary.total_complaints) * 100) : 0}
                  label="Urgent Late"
                  detail={`${compactNumber(data.slaSummary?.high_urgency_untimely_count)} cases`}
                />
              </div>
            </article>

            <RankedBars
              title="Product Complaint Mix"
              subtitle={`${compactNumber(totalProductRows)} completed complaints grouped by product/category`}
              rows={data.productSummary?.items.slice(0, 10) ?? []}
              labelFor={(row) => {
                const item = row as ProductSummaryResponse["items"][number];
                return [item.product ?? "Unknown product", item.category].filter(Boolean).join(" / ");
              }}
              valueFor={(row) => (row as ProductSummaryResponse["items"][number]).count}
            />

            <RankedBars
              title="SLA By Product"
              subtitle="Lowest or highest product performance depending backend sort"
              rows={data.slaByProduct?.items.slice(0, 10) ?? []}
              labelFor={(row) => (row as SLAGroupedResponse["items"][number]).product ?? "Unknown product"}
              valueFor={(row) => Math.round((row as SLAGroupedResponse["items"][number]).timely_rate_pct)}
              suffix="%"
            />

            <RankedBars
              title="SLA By Channel"
              subtitle="Response timeliness across intake channels"
              rows={data.slaByChannel?.items.slice(0, 10) ?? []}
              labelFor={(row) => (row as SLAGroupedResponse["items"][number]).channel ?? "Unknown channel"}
              valueFor={(row) => Math.round((row as SLAGroupedResponse["items"][number]).timely_rate_pct)}
              suffix="%"
            />
          </section>

          <section className="analytics-table-grid">
            <article className="panel analytics-card">
              <div className="panel-heading">
                <div>
                  <h2>High Urgency Watchlist</h2>
                  <p>Complaints needing faster operational attention</p>
                </div>
                <ShieldAlert size={18} />
              </div>
              <div className="risk-table">
                <div className="risk-table-head"><span>Complaint</span><span>Product</span><span>Channel</span><span>Urgency</span></div>
                {data.highUrgency?.items.slice(0, 10).map((item) => (
                  <div key={item.complaint_id}>
                    <span>{item.complaint_id}</span>
                    <span>{item.product ?? "Unknown"}</span>
                    <span>{item.channel ?? "Unknown"}</span>
                    <strong>{item.urgency_score}</strong>
                  </div>
                ))}
                {!data.highUrgency?.items.length ? <p className="analytics-empty">No high-urgency cases returned.</p> : null}
              </div>
            </article>

            <article className="panel analytics-card">
              <div className="panel-heading">
                <div>
                  <h2>SLA Breach Risk</h2>
                  <p>Urgent or high-risk complaints that may miss response expectations</p>
                </div>
                <ShieldAlert size={18} />
              </div>
              <div className="risk-table">
                <div className="risk-table-head"><span>Complaint</span><span>Product</span><span>Timely</span><span>Risk</span></div>
                {data.slaBreachRisk?.items.slice(0, 10).map((item) => (
                  <div key={item.complaint_id}>
                    <span>{item.source_complaint_id ?? item.complaint_id}</span>
                    <span>{item.product ?? "Unknown"}</span>
                    <span>{item.timely_response === true ? "Yes" : item.timely_response === false ? "No" : "Unknown"}</span>
                    <strong>{item.churn_risk ?? "Unknown"}</strong>
                  </div>
                ))}
                {!data.slaBreachRisk?.items.length ? <p className="analytics-empty">No SLA breach-risk cases returned.</p> : null}
              </div>
            </article>
          </section>

          <section className="analytics-insights panel">
            <div className="panel-heading">
              <div>
                <h2>Quick Read</h2>
                <p>Plain-English summary from the currently loaded backend metrics</p>
              </div>
            </div>
            <div>
              <p><strong>SLA:</strong> {percent(data.slaSummary?.timely_rate_pct)} of completed complaints have timely responses.</p>
              <p><strong>Urgency:</strong> The high urgency watchlist average is {Math.round(highUrgencyAverage)}/100.</p>
              <p><strong>Products:</strong> {data.productSummary?.items[0]?.product ?? "No product"} is currently the largest returned product group.</p>
              <p><strong>Reviews:</strong> Human review trend returned {compactNumber(data.humanReviewTrend?.items.reduce((sum, item) => sum + item.count, 0))} routed cases.</p>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
