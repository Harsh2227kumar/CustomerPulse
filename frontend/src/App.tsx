import {
  Activity,
  BarChart3,
  Bell,
  Bot,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Database,
  Gauge,
  Inbox,
  LayoutDashboard,
  Loader2,
  MessageSquareText,
  RefreshCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import { type CSSProperties, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { createProcessingJob, getApiKey, getComplaints, getHealth, getJob, processComplaint, websocketUrl } from "./api/client";
import { AnalyticsPage } from "./AnalyticsPage";
import { OperationsPage } from "./OperationsPage";
import { S3ImportPage } from "./S3ImportPage";
import type {
  ChurnRisk,
  ComplaintFilters,
  ComplaintListItem,
  HealthResponse,
  ProcessedComplaintResponse,
  ProcessingJobResponse,
  Sentiment,
  SimilarCaseDetail,
  WebSocketMessage,
} from "./types";

const initialFilters: ComplaintFilters = {
  search: "",
  sentiment: "",
  channel: "",
  product: "",
  churn_risk: "",
  urgency_min: "",
  urgency_max: "",
  date_received_min: "",
  date_received_max: "",
  timely_response: "",
  ai_status: "",
  human_review_reason: "",
  sort_by: "created_at",
  sort_direction: "desc",
};

const pageSizes = [25, 50, 100, 200];

const eventLabels: Record<string, string> = {
  received: "Received",
  preprocessing: "Preprocessing",
  local_ml: "Local scoring",
  bedrock_processing: "Bedrock analysis",
  validating: "Validation",
  saved: "Saved",
  failed: "Failed",
  human_review_required: "Human review",
};

function readInitialFilters(): ComplaintFilters {
  const params = new URLSearchParams(window.location.search);
  return {
    search: params.get("search") ?? initialFilters.search,
    sentiment: (params.get("sentiment") as ComplaintFilters["sentiment"]) ?? initialFilters.sentiment,
    channel: params.get("channel") ?? initialFilters.channel,
    product: params.get("product") ?? initialFilters.product,
    churn_risk: (params.get("churn_risk") as ComplaintFilters["churn_risk"]) ?? initialFilters.churn_risk,
    urgency_min: params.get("urgency_min") ?? initialFilters.urgency_min,
    urgency_max: params.get("urgency_max") ?? initialFilters.urgency_max,
    date_received_min: params.get("date_received_min") ?? initialFilters.date_received_min,
    date_received_max: params.get("date_received_max") ?? initialFilters.date_received_max,
    timely_response: (params.get("timely_response") as ComplaintFilters["timely_response"]) ?? initialFilters.timely_response,
    ai_status: (params.get("ai_status") as ComplaintFilters["ai_status"]) ?? initialFilters.ai_status,
    human_review_reason: params.get("human_review_reason") ?? initialFilters.human_review_reason,
    sort_by: (params.get("sort_by") as ComplaintFilters["sort_by"]) ?? initialFilters.sort_by,
    sort_direction: (params.get("sort_direction") as ComplaintFilters["sort_direction"]) ?? initialFilters.sort_direction,
  };
}

function readInitialNumber(name: string, fallback: number, allowed?: number[]): number {
  const parsed = Number(new URLSearchParams(window.location.search).get(name));
  if (!Number.isFinite(parsed) || parsed < 0) return fallback;
  if (allowed && !allowed.includes(parsed)) return fallback;
  return parsed;
}

function formatDate(value: string | null): string {
  if (!value) return "Not provided";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function formatDateTime(value: string | null): string {
  if (!value) return "Not processed";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function percent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "0%";
  return `${Math.round(value)}%`;
}

function aiConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Not scored";
  return value <= 1 ? percent(value * 100) : percent(value);
}

function normalizedScore(value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  return value <= 1 ? value * 100 : value;
}

function warningClass(value: number | null | undefined): string {
  const score = normalizedScore(value);
  if (score === null) return "neutral";
  if (score < 60) return "danger";
  if (score < 75) return "warning";
  return "success";
}

function confidenceEntries(scores: ComplaintListItem["confidence_scores"] | ProcessedComplaintResponse["confidence_scores"]) {
  if (!scores) return [];
  return Object.entries(scores).filter((entry): entry is [string, number] => typeof entry[1] === "number");
}

function hasWeakConfidence(scores: ComplaintListItem["confidence_scores"] | ProcessedComplaintResponse["confidence_scores"]): boolean {
  return confidenceEntries(scores).some(([, value]) => normalizedScore(value) !== null && Number(normalizedScore(value)) < 60);
}

function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

function similarCaseId(item: SimilarCaseDetail, index: number): string {
  return item.complaint_id ?? `Case ${index + 1}`;
}

function similarCaseScore(item: SimilarCaseDetail): number | null {
  return normalizedScore(item.similarity_score);
}

function similarCaseSummary(item: SimilarCaseDetail): string {
  return item.approved_response ?? item.next_action ?? "No evidence summary returned.";
}

function average(values: Array<number | null>): number {
  const usable = values.filter((value): value is number => typeof value === "number");
  if (!usable.length) return 0;
  return usable.reduce((sum, value) => sum + value, 0) / usable.length;
}

function riskClass(value: ChurnRisk | null): string {
  if (value === "High") return "danger";
  if (value === "Medium") return "warning";
  if (value === "Low") return "success";
  return "neutral";
}

function sentimentClass(value: Sentiment | null): string {
  if (value === "Negative") return "danger";
  if (value === "Positive") return "success";
  if (value === "Neutral") return "warning";
  return "neutral";
}

function uniqueCount(rows: ComplaintListItem[], field: keyof ComplaintListItem): number {
  return new Set(rows.map((row) => row[field]).filter(Boolean)).size;
}

function buildSparkline(rows: ComplaintListItem[]): string {
  const dated = rows.filter((row) => row.date_received);
  if (!dated.length) return "";

  const buckets = new Map<string, number>();
  for (const row of dated) {
    const date = new Date(row.date_received as string);
    const key = `${date.getFullYear()}-${date.getMonth()}`;
    buckets.set(key, (buckets.get(key) ?? 0) + 1);
  }

  const values = Array.from(buckets.values()).slice(-12);
  const max = Math.max(...values, 1);
  return values
    .map((value, index) => {
      const x = values.length === 1 ? 8 : 8 + (index * 184) / (values.length - 1);
      const y = 86 - (value / max) * 62;
      return `${x},${y}`;
    })
    .join(" ");
}

function weeklyBars(rows: ComplaintListItem[]): number[] {
  const bars = Array.from({ length: 7 }, () => 0);
  for (const row of rows) {
    if (!row.processed_at && !row.date_received) continue;
    const date = new Date(row.processed_at ?? (row.date_received as string));
    bars[date.getDay()] += 1;
  }
  return bars;
}

function CircleMeter({ value, label }: { value: number; label: string }) {
  const normalized = Math.max(0, Math.min(100, value));
  return (
    <div className="circle-meter" style={{ "--meter": `${normalized}%` } as CSSProperties}>
      <div>
        <strong>{Math.round(normalized)}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

function EmptyPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <FileText size={22} />
      <strong>{title}</strong>
      <span>{body}</span>
    </div>
  );
}

export function App() {
  const [activeView, setActiveView] = useState<"dashboard" | "import" | "queue" | "ops" | "analytics">(() => {
    const view = new URLSearchParams(window.location.search).get("view");
    return view === "queue" || view === "import" || view === "ops" || view === "analytics" ? view : "dashboard";
  });
  const [filters, setFilters] = useState<ComplaintFilters>(() => readInitialFilters());
  const [limit, setLimit] = useState(() => readInitialNumber("limit", 50, pageSizes));
  const [offset, setOffset] = useState(() => readInitialNumber("offset", 0));
  const [complaints, setComplaints] = useState<ComplaintListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "live" | "offline">("connecting");
  const [events, setEvents] = useState<WebSocketMessage[]>([]);
  const [processing, setProcessing] = useState(false);
  const [queueProcessing, setQueueProcessing] = useState(false);
  const [queueProcessLimit, setQueueProcessLimit] = useState(50);
  const [queueProcessJob, setQueueProcessJob] = useState<ProcessingJobResponse | null>(null);
  const [queueProcessError, setQueueProcessError] = useState<string | null>(null);
  const [processResult, setProcessResult] = useState<ProcessedComplaintResponse | null>(null);
  const [processError, setProcessError] = useState<string | null>(null);
  const hasApiKey = Boolean(getApiKey());
  const filterRef = useRef(filters);
  const limitRef = useRef(limit);
  const offsetRef = useRef(offset);
  const [form, setForm] = useState({
    narrative: "",
    channel: "",
    product: "",
    issue: "",
    company: "",
  });

  useEffect(() => {
    filterRef.current = filters;
    limitRef.current = limit;
    offsetRef.current = offset;
  }, [filters, limit, offset]);

  async function loadComplaints(
    activeFilters = filterRef.current,
    activeLimit = limitRef.current,
    activeOffset = offsetRef.current,
  ) {
    setLoading(true);
    setError(null);
    try {
      const [complaintResponse, healthResponse] = await Promise.all([
        getComplaints(activeFilters, activeLimit, activeOffset),
        getHealth().catch(() => null),
      ]);
      setComplaints(complaintResponse.items);
      setTotalCount(complaintResponse.count);
      setHealth(healthResponse);
      setSelectedId((current) => current ?? complaintResponse.items[0]?.complaint_id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load complaints");
      setComplaints([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadComplaints();
  }, [filters.sort_by, filters.sort_direction, limit, offset]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      if (offset !== 0) {
        setOffset(0);
      } else {
        loadComplaints();
      }
    }, 350);
    return () => window.clearTimeout(timeout);
  }, [
    filters.search,
    filters.sentiment,
    filters.channel,
    filters.product,
    filters.churn_risk,
    filters.urgency_min,
    filters.urgency_max,
    filters.date_received_min,
    filters.date_received_max,
    filters.timely_response,
    filters.ai_status,
    filters.human_review_reason,
    offset,
  ]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (activeView !== "dashboard") params.set("view", activeView);
    params.set("limit", String(limit));
    if (offset) params.set("offset", String(offset));
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const nextUrl = `${window.location.pathname}?${params.toString()}${window.location.hash}`;
    window.history.replaceState(null, "", nextUrl);
  }, [activeView, filters, limit, offset]);

  useEffect(() => {
    const socket = new WebSocket(websocketUrl());
    socket.onopen = () => setWsStatus("live");
    socket.onclose = () => setWsStatus("offline");
    socket.onerror = () => setWsStatus("offline");
    socket.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as WebSocketMessage;
        setEvents((current) => [parsed, ...current].slice(0, 8));
        if (parsed.event === "saved" || parsed.event === "human_review_required") {
          loadComplaints(filterRef.current, limitRef.current, offsetRef.current);
        }
      } catch {
        setWsStatus("offline");
      }
    };
    return () => socket.close();
  }, []);

  const selectedComplaint = useMemo(
    () => complaints.find((complaint) => complaint.complaint_id === selectedId) ?? complaints[0] ?? null,
    [complaints, selectedId],
  );

  const metrics = useMemo(() => {
    const avgUrgency = average(complaints.map((row) => row.urgency_score));
    const highRisk = complaints.filter((row) => row.churn_risk === "High").length;
    const completed = complaints.filter((row) => row.ai_status === "completed").length;
    const timely = complaints.filter((row) => row.timely_response === "Yes").length;
    const review = complaints.filter((row) => row.human_review_required || row.ai_status === "human_review" || row.human_review_reason).length;
    const failed = complaints.filter((row) => row.ai_status === "failed").length;
    return {
      avgUrgency,
      highRisk,
      completed,
      review,
      failed,
      timelyRate: complaints.length ? (timely / complaints.length) * 100 : 0,
      products: uniqueCount(complaints, "product"),
    };
  }, [complaints]);

  const currentPage = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(totalCount / limit));
  const canPageBack = offset > 0;
  const canPageForward = offset + limit < totalCount;
  const unprocessedComplaints = useMemo(
    () => complaints.filter((complaint) => !complaint.processed_at && complaint.ai_status !== "completed" && complaint.ai_status !== "human_review"),
    [complaints],
  );
  const queueProcessComplete = queueProcessJob
    ? queueProcessJob.counts.completed + queueProcessJob.counts.human_review + queueProcessJob.counts.failed
    : 0;

  function openQueueInNewTab() {
    const params = new URLSearchParams(window.location.search);
    params.set("view", "queue");
    window.open(`${window.location.origin}${window.location.pathname}?${params.toString()}`, "_blank", "noopener,noreferrer");
  }

  async function processQueuedComplaints() {
    if (!hasApiKey) {
      setQueueProcessError("Save a manager or admin API key in Operations before processing queue complaints.");
      return;
    }
    const selectedIds = unprocessedComplaints.slice(0, queueProcessLimit).map((complaint) => complaint.complaint_id);
    if (!selectedIds.length) {
      setQueueProcessError("No unprocessed complaints are available in the current queue page.");
      return;
    }

    setQueueProcessing(true);
    setQueueProcessError(null);
    setQueueProcessJob(null);
    try {
      let job = await createProcessingJob(selectedIds);
      setQueueProcessJob(job);
      while (!job.finished_at && ["queued", "running"].includes(job.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        job = await getJob(job.job_id);
        setQueueProcessJob(job);
      }
      await loadComplaints();
    } catch (err) {
      setQueueProcessError(err instanceof Error ? err.message : "Queue processing failed.");
    } finally {
      setQueueProcessing(false);
    }
  }

  const queuePanel = (mode: "dashboard" | "page" = "dashboard") => (
    <article className={`panel table-panel queue-panel ${mode === "page" ? "queue-panel-expanded" : ""}`} id="complaints">
      <div className="panel-heading queue-heading">
        <div>
          <h2>Complaint Queue</h2>
          <p>{loading ? "Loading backend rows" : `${complaints.length} of ${totalCount} records shown`}</p>
        </div>
        <div className="queue-actions">
          <button className="secondary-action compact-action" type="button" onClick={() => loadComplaints()} disabled={loading}>
            <RefreshCcw size={15} /> Refresh
          </button>
          {mode === "dashboard" ? (
            <button className="primary-action compact-action" type="button" onClick={openQueueInNewTab}>
              <ExternalLink size={15} /> Open full queue
            </button>
          ) : (
            <>
              <label className="queue-process-control">
                <span>Process</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={queueProcessLimit}
                  onChange={(event) => setQueueProcessLimit(Math.min(50, Math.max(1, Number(event.target.value) || 1)))}
                  aria-label="Number of unprocessed complaints to process"
                />
              </label>
              <button
                className="primary-action compact-action"
                type="button"
                onClick={processQueuedComplaints}
                disabled={queueProcessing || loading || !unprocessedComplaints.length}
              >
                {queueProcessing ? <Loader2 className="spin" size={15} /> : <Sparkles size={15} />}
                Process AI
              </button>
              <button className="secondary-action compact-action" type="button" onClick={() => setActiveView("dashboard")}>
                <ChevronLeft size={15} /> Dashboard
              </button>
            </>
          )}
        </div>
      </div>
      {mode === "page" && (queueProcessError || queueProcessJob) ? (
        <div className={`queue-job-banner ${queueProcessError ? "failure" : "success"}`}>
          {queueProcessError ? (
            <span>{queueProcessError}</span>
          ) : queueProcessJob ? (
            <span>
              AI job {queueProcessJob.status.replace(/_/g, " ")}: {queueProcessComplete.toLocaleString()} of {queueProcessJob.total_items.toLocaleString()} handled, {queueProcessJob.counts.failed.toLocaleString()} failed.
            </span>
          ) : null}
        </div>
      ) : null}
      {mode === "page" ? (
        <div className="filter-row queue-filter-row">
          <input
            value={filters.product}
            onChange={(event) => setFilters((current) => ({ ...current, product: event.target.value }))}
            placeholder="Product"
          />
          <input
            value={filters.channel}
            onChange={(event) => setFilters((current) => ({ ...current, channel: event.target.value }))}
            placeholder="Channel"
          />
          <select value={filters.sentiment} onChange={(event) => setFilters((current) => ({ ...current, sentiment: event.target.value as Sentiment | "" }))}>
            <option value="">Sentiment</option>
            <option value="Positive">Positive</option>
            <option value="Neutral">Neutral</option>
            <option value="Negative">Negative</option>
          </select>
          <select value={filters.churn_risk} onChange={(event) => setFilters((current) => ({ ...current, churn_risk: event.target.value as ChurnRisk | "" }))}>
            <option value="">Churn risk</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
          </select>
          <select value={filters.timely_response} onChange={(event) => setFilters((current) => ({ ...current, timely_response: event.target.value as ComplaintFilters["timely_response"] }))}>
            <option value="">Timely</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
          <select value={filters.ai_status} onChange={(event) => setFilters((current) => ({ ...current, ai_status: event.target.value as ComplaintFilters["ai_status"] }))}>
            <option value="">AI status</option>
            <option value="completed">Completed</option>
            <option value="human_review">Human review</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
          </select>
          <input
            value={filters.human_review_reason}
            onChange={(event) => setFilters((current) => ({ ...current, human_review_reason: event.target.value }))}
            placeholder="Review reason"
          />
          <input
            type="number"
            min={0}
            max={100}
            value={filters.urgency_min}
            onChange={(event) => setFilters((current) => ({ ...current, urgency_min: event.target.value }))}
            placeholder="Urgency min"
          />
          <input
            type="number"
            min={0}
            max={100}
            value={filters.urgency_max}
            onChange={(event) => setFilters((current) => ({ ...current, urgency_max: event.target.value }))}
            placeholder="Urgency max"
          />
          <input
            type="date"
            value={filters.date_received_min}
            onChange={(event) => setFilters((current) => ({ ...current, date_received_min: event.target.value }))}
            aria-label="Received after"
          />
          <input
            type="date"
            value={filters.date_received_max}
            onChange={(event) => setFilters((current) => ({ ...current, date_received_max: event.target.value }))}
            aria-label="Received before"
          />
        </div>
      ) : null}
      <div className="queue-summary" aria-label="Complaint status counters">
        <span><strong>{metrics.completed}</strong> Completed</span>
        <span><strong>{metrics.review}</strong> Review</span>
        <span><strong>{metrics.failed}</strong> Failed</span>
        <span><strong>{metrics.highRisk}</strong> High risk</span>
      </div>
      {error ? (
        <EmptyPanel title="Backend unavailable" body={error} />
      ) : loading ? (
        <div className="loading-row"><Loader2 className="spin" size={18} />Fetching real backend records</div>
      ) : complaints.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Complaint</th>
                <th>Sentiment</th>
                <th>Urgency</th>
                <th>Risk</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((complaint) => (
                <tr
                  key={complaint.complaint_id}
                  className={selectedComplaint?.complaint_id === complaint.complaint_id ? "selected" : ""}
                  onClick={() => setSelectedId(complaint.complaint_id)}
                >
                  <td>
                    <strong>{complaint.product ?? "Product missing"}</strong>
                    <em>{[complaint.company, complaint.sub_product, complaint.sub_issue].filter(Boolean).join(" / ") || "No company/subtype metadata"}</em>
                    <span>{complaint.narrative}</span>
                  </td>
                  <td><span className={`badge ${sentimentClass(complaint.sentiment)}`}>{complaint.sentiment ?? "Unknown"}</span></td>
                  <td>
                    <div className="bar-cell"><span style={{ width: `${complaint.urgency_score ?? 0}%` }} />{complaint.urgency_score ?? 0}</div>
                  </td>
                  <td><span className={`badge ${riskClass(complaint.churn_risk)}`}>{complaint.churn_risk ?? "Unknown"}</span></td>
                  <td><span className={`badge ${warningClass(complaint.confidence_scores?.sentiment)}`}>{percent(complaint.confidence_scores?.sentiment)}</span></td>
                  <td><span className={`status-pill ${complaint.ai_status}`}>{complaint.ai_status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyPanel title="No real complaints returned" body="The frontend has no fallback rows. Run real ingestion or submit a live complaint." />
      )}
      <div className="pagination-row" aria-label="Complaint pagination">
        <button type="button" disabled={!canPageBack || loading} onClick={() => setOffset((current) => Math.max(0, current - limit))}>
          <ChevronLeft size={15} /> Previous
        </button>
        <span>Page {currentPage} of {pageCount}</span>
        <select
          value={limit}
          onChange={(event) => {
            setLimit(Number(event.target.value));
            setOffset(0);
          }}
          aria-label="Rows per page"
        >
          {pageSizes.map((size) => <option key={size} value={size}>{size} rows</option>)}
        </select>
        <button type="button" disabled={!canPageForward || loading} onClick={() => setOffset((current) => current + limit)}>
          Next <ChevronRight size={15} />
        </button>
      </div>
    </article>
  );

  async function submitComplaint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasApiKey) {
      setProcessError("Save an agent, manager, or admin API key in Operations before using Live Intake.");
      return;
    }
    setProcessing(true);
    setProcessError(null);
    setProcessResult(null);
    try {
      const result = await processComplaint({
        complaint_id: crypto.randomUUID(),
        narrative: form.narrative.trim(),
        channel: form.channel.trim() || null,
        product: form.product.trim() || null,
        issue: form.issue.trim() || null,
        company: form.company.trim() || null,
      });
      setProcessResult(result);
      await loadComplaints();
      setForm({ narrative: "", channel: "", product: "", issue: "", company: "" });
    } catch (err) {
      setProcessError(err instanceof Error ? err.message : "Complaint processing failed");
    } finally {
      setProcessing(false);
    }
  }

  if (activeView === "import") {
    return <S3ImportPage onBack={() => setActiveView("dashboard")} />;
  }

  if (activeView === "ops") {
    return (
      <OperationsPage
        selectedComplaintId={selectedComplaint?.complaint_id ?? ""}
        onBack={() => setActiveView("dashboard")}
        onRefreshComplaints={() => loadComplaints()}
      />
    );
  }

  if (activeView === "analytics") {
    return <AnalyticsPage onBack={() => setActiveView("dashboard")} />;
  }

  if (activeView === "queue") {
    return (
      <main className="queue-page">
        <header className="queue-page-header">
          <div>
            <button className="icon-button" type="button" onClick={() => setActiveView("dashboard")} aria-label="Back to dashboard">
              <ChevronLeft size={18} />
            </button>
            <div>
              <h1>Complaint Queue</h1>
              <p>Focused review workspace for backend complaint records</p>
            </div>
          </div>
          <label className="searchbar">
            <Search size={17} />
            <input
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              placeholder="Search real complaints"
            />
          </label>
          <div className="top-actions">
            <button className="icon-button" type="button" onClick={() => loadComplaints()} aria-label="Refresh"><RefreshCcw size={17} /></button>
            <div className="user-chip"><UserRound size={18} /><span>Ops User</span></div>
          </div>
        </header>
        <section className="queue-page-grid">
          <div className="queue-page-main">{queuePanel("page")}</div>
          <aside className="queue-page-side">
            <article className="panel status-card">
              <div className="panel-heading">
                <h2>Backend Status</h2>
                <span className={`live-dot ${health ? "online" : "offline"}`} />
              </div>
              <div className="status-list">
                <span>API <strong>{health?.status ?? "Unavailable"}</strong></span>
                <span>Environment <strong>{health?.environment ?? "Unknown"}</strong></span>
                <span>WebSocket <strong>{wsStatus}</strong></span>
                <span>AI completed <strong>{metrics.completed}</strong></span>
              </div>
            </article>
            <article className="panel detail-panel">
              <div className="panel-heading">
                <h2>Selected Case</h2>
                <Bot size={18} />
              </div>
              {selectedComplaint ? (
                <div className="detail-copy">
                  <span>Product</span>
                  <strong>{selectedComplaint.product ?? "Unlabeled product"}</strong>
                  <span>Company</span>
                  <strong>{selectedComplaint.company ?? "Unknown"}</strong>
                  <span>Review</span>
                  <strong className={`badge ${selectedComplaint.human_review_required || selectedComplaint.ai_status === "human_review" ? "warning" : "success"}`}>
                    {selectedComplaint.human_review_required || selectedComplaint.ai_status === "human_review" ? "Review required" : "No review flag"}
                  </strong>
                  <span>Next action</span>
                  <p>{selectedComplaint.next_action ?? "No next action returned for this row."}</p>
                  <span>Narrative</span>
                  <p>{selectedComplaint.narrative}</p>
                </div>
              ) : (
                <EmptyPanel title="No complaint selected" body="Select a row once backend records are available." />
              )}
            </article>
          </aside>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={20} /></div>
          <span>CustomerPulse</span>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          <a className="active" href="#dashboard"><LayoutDashboard size={16} />Dashboard</a>
          <a href="#complaints"><Inbox size={16} />Complaints</a>
          <button type="button" onClick={() => setActiveView("import")}><Database size={16} />S3 Import</button>
          <a href="#intake"><MessageSquareText size={16} />Live Intake</a>
          <button type="button" onClick={() => setActiveView("analytics")}><BarChart3 size={16} />Analytics</button>
          <a href="#activity"><Activity size={16} />Activity</a>
          <button type="button" onClick={() => setActiveView("ops")}><Settings size={16} />Operations</button>
        </nav>
        <section className="upgrade-card">
          <strong>Real Data Mode</strong>
          <span>Dashboard panels render only backend and database responses.</span>
          <button type="button" onClick={() => loadComplaints()}>Refresh API</button>
        </section>
      </aside>

      <section className="workspace" id="dashboard">
        <header className="topbar">
          <div>
            <button className="icon-button" type="button" aria-label="Back"><ChevronLeft size={18} /></button>
            <div>
              <h1>Complaint Intelligence</h1>
              <p>Dashboard / Real-time complaint operations</p>
            </div>
          </div>
          <label className="searchbar">
            <Search size={17} />
            <input
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              placeholder="Search real complaints"
            />
          </label>
          <div className="top-actions">
            <button className="icon-button" type="button" onClick={() => loadComplaints()} aria-label="Refresh"><RefreshCcw size={17} /></button>
            <button className="icon-button" type="button" aria-label="Notifications"><Bell size={17} /></button>
            <div className="user-chip"><UserRound size={18} /><span>Ops User</span></div>
          </div>
        </header>

        <section className="dashboard-grid">
          <article className="profile-card panel">
            {selectedComplaint ? (
              <>
                <div className="avatar"><ShieldCheck size={42} /></div>
                <h2>{selectedComplaint.product ?? "Unlabeled product"}</h2>
                <p>{selectedComplaint.issue ?? "Issue not provided"}</p>
                <div className="id-pill">{selectedComplaint.complaint_id}</div>
                <span className={`status-pill ${selectedComplaint.ai_status}`}>{selectedComplaint.ai_status}</span>
                {selectedComplaint.human_review_required || selectedComplaint.ai_status === "human_review" ? <span className="status-pill review">Review required</span> : null}
                <div className="info-list">
                  <span>Channel <strong>{selectedComplaint.channel ?? "Unknown"}</strong></span>
                  <span>Company <strong>{selectedComplaint.company ?? "Unknown"}</strong></span>
                  <span>Sub-product <strong>{selectedComplaint.sub_product ?? "Unknown"}</strong></span>
                  <span>Date received <strong>{formatDate(selectedComplaint.date_received)}</strong></span>
                  <span>Processed <strong>{formatDateTime(selectedComplaint.processed_at)}</strong></span>
                  <span>Timely response <strong>{selectedComplaint.timely_response ?? "Unknown"}</strong></span>
                  <span>Retries <strong>{selectedComplaint.retry_count ?? 0}</strong></span>
                  <span>Review reason <strong>{selectedComplaint.human_review_reason ?? selectedComplaint.review_reason ?? "None"}</strong></span>
                </div>
              </>
            ) : (
              <EmptyPanel title="No complaint selected" body="Connect a populated backend database to inspect a real complaint." />
            )}
          </article>

          <section className="main-column">
            <div className="kpi-row">
              <article className="metric-card">
                <span>Total Cases</span>
                <CircleMeter value={Math.min(totalCount, 100)} label="rows" />
                <strong>{totalCount}</strong>
              </article>
              <article className="metric-card">
                <span>Avg Urgency</span>
                <CircleMeter value={metrics.avgUrgency} label="score" />
                <strong>{Math.round(metrics.avgUrgency)}/100</strong>
              </article>
              <article className="metric-card">
                <span>High Risk</span>
                <CircleMeter value={complaints.length ? (metrics.highRisk / complaints.length) * 100 : 0} label="share" />
                <strong>{metrics.highRisk}</strong>
              </article>
              <article className="metric-card">
                <span>Timely</span>
                <CircleMeter value={metrics.timelyRate} label="rate" />
                <strong>{percent(metrics.timelyRate)}</strong>
              </article>
            </div>

            {queuePanel()}

            <section className="lower-grid">
              <article className="panel detail-panel">
                <div className="panel-heading">
                  <h2>AI Detail</h2>
                  <Bot size={18} />
                </div>
                {selectedComplaint ? (
                  <div className="detail-copy">
                    <span>Category</span>
                    <strong>{selectedComplaint.category ?? "Not classified"}</strong>
                    <span>Grounding</span>
                    <strong className={`grounding-pill ${selectedComplaint.grounded_response === false ? "warning" : "success"}`}>
                      {selectedComplaint.grounded_response === false ? "Needs evidence review" : selectedComplaint.grounded_response === true ? "Grounded response" : "Grounding not returned"}
                    </strong>
                    <span>AI confidence</span>
                    <strong className={`badge ${warningClass(selectedComplaint.ai_confidence)}`}>{aiConfidence(selectedComplaint.ai_confidence)}</strong>
                    {hasWeakConfidence(selectedComplaint.confidence_scores) ? (
                      <div className="warning-note">Weak confidence detected. Review the draft before action.</div>
                    ) : null}
                    {selectedComplaint.retrieval_warning ? (
                      <div className="warning-note">{selectedComplaint.retrieval_warning}</div>
                    ) : null}
                    {confidenceEntries(selectedComplaint.confidence_scores).length ? (
                      <div className="confidence-grid">
                        {confidenceEntries(selectedComplaint.confidence_scores).map(([name, value]) => (
                          <span key={name} className={warningClass(value)}>
                            <strong>{percent(value)}</strong>
                            {humanize(name)}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <span>Next action</span>
                    <p>{selectedComplaint.next_action ?? "No next action returned for this row."}</p>
                    <span>Draft response</span>
                    <p>{selectedComplaint.draft_response ?? "No draft response returned for this row."}</p>
                    <span>AI reasoning</span>
                    <p>{selectedComplaint.ai_reasoning ?? "No reasoning returned for this row."}</p>
                    {selectedComplaint.similar_cases?.length ? (
                      <>
                        <span>Similar cases</span>
                        <div className="similar-cases">
                          {selectedComplaint.similar_cases.map((item, index) => (
                            <button type="button" key={`${similarCaseId(item, index)}-${index}`}>
                              <strong>{similarCaseId(item, index)}</strong>
                              <small>{similarCaseScore(item) === null ? "Score not returned" : `${Math.round(Number(similarCaseScore(item)))}% match`}</small>
                              <span>{similarCaseSummary(item)}</span>
                              {item.category ? <em>{item.category}</em> : null}
                            </button>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="warning-note neutral">No similar past cases returned.</div>
                    )}
                    {selectedComplaint.omitted_retrievals?.length ? (
                      <>
                        <span>Omitted retrievals</span>
                        <p>{selectedComplaint.omitted_retrievals.map((item, index) => similarCaseId(item, index)).join(", ")}</p>
                      </>
                    ) : null}
                    {selectedComplaint.error_message ? (
                      <>
                        <span>Processing error</span>
                        <p>{selectedComplaint.error_message}</p>
                      </>
                    ) : null}
                    {selectedComplaint.processing_history?.length ? (
                      <>
                        <span>Processing history</span>
                        <div className="history-list">
                          {selectedComplaint.processing_history.map((item, index) => (
                            <p key={`${item.id ?? item.attempt_number}-${index}`}>
                              <strong>Attempt {item.attempt_number}</strong> {item.status_outcome} via {item.trigger_reason ?? "unknown"} {item.created_at ? formatDateTime(item.created_at) : ""}
                            </p>
                          ))}
                        </div>
                      </>
                    ) : null}
                    <span>Narrative</span>
                    <p>{selectedComplaint.narrative}</p>
                  </div>
                ) : (
                  <EmptyPanel title="No AI detail" body="Select a real complaint once records are available." />
                )}
              </article>
            </section>
          </section>

          <aside className="right-column">
            <article className="panel status-card">
              <div className="panel-heading">
                <h2>Backend Status</h2>
                <span className={`live-dot ${health ? "online" : "offline"}`} />
              </div>
              <div className="status-list">
                <span>API <strong>{health?.status ?? "Unavailable"}</strong></span>
                <span>Environment <strong>{health?.environment ?? "Unknown"}</strong></span>
                <span>WebSocket <strong>{wsStatus}</strong></span>
                <span>AI completed <strong>{metrics.completed}</strong></span>
              </div>
            </article>

            <article className="panel calendar-card">
              <div className="panel-heading">
                <h2>Processing Dates</h2>
                <div><ChevronLeft size={14} /><ChevronRight size={14} /></div>
              </div>
              <div className="date-grid">
                {complaints.slice(0, 12).map((complaint) => (
                  <button key={complaint.complaint_id} type="button" onClick={() => setSelectedId(complaint.complaint_id)}>
                    {complaint.date_received ? new Date(complaint.date_received).getDate() : "?"}
                  </button>
                ))}
                {!complaints.length && <span>No dates from backend</span>}
              </div>
            </article>

            <article className="panel" id="intake">
              <div className="panel-heading">
                <h2>Live Intake</h2>
                <Send size={17} />
              </div>
              {!hasApiKey && (
                <div className="warning-note neutral">
                  Live Intake uses protected AI processing. Save an API key in Operations first.
                  <button type="button" className="inline-action" onClick={() => setActiveView("ops")}>Open Operations</button>
                </div>
              )}
              <form className="intake-form" onSubmit={submitComplaint}>
                <textarea
                  required
                  minLength={1}
                  value={form.narrative}
                  onChange={(event) => setForm((current) => ({ ...current, narrative: event.target.value }))}
                  placeholder="Paste or type the real complaint narrative"
                />
                <input value={form.channel} onChange={(event) => setForm((current) => ({ ...current, channel: event.target.value }))} placeholder="Channel" />
                <input value={form.product} onChange={(event) => setForm((current) => ({ ...current, product: event.target.value }))} placeholder="Product" />
                <input value={form.issue} onChange={(event) => setForm((current) => ({ ...current, issue: event.target.value }))} placeholder="Issue" />
                <input value={form.company} onChange={(event) => setForm((current) => ({ ...current, company: event.target.value }))} placeholder="Company" />
                <button type="submit" disabled={processing || !hasApiKey}>
                  {processing ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
                  Process complaint
                </button>
              </form>
              {processError && <p className="form-error">{processError}</p>}
              {processResult && (
                <div className="result-card">
                  <strong>{processResult.category}</strong>
                  <span>{processResult.sentiment} / {processResult.churn_risk} / {aiConfidence(processResult.ai_confidence)}</span>
                  <p>{processResult.next_action}</p>
                  <p>{processResult.draft_response}</p>
                  {hasWeakConfidence(processResult.confidence_scores) ? <span className="warning-text">Weak field confidence detected</span> : null}
                  {processResult.similar_cases.length ? (
                    <span>Similar: {processResult.similar_cases.map((item, index) => similarCaseId(item, index)).join(", ")}</span>
                  ) : null}
                  {processResult.ai_reasoning ? <span>Reasoning: {processResult.ai_reasoning}</span> : null}
                </div>
              )}
            </article>

            <article className="panel" id="activity">
              <div className="panel-heading">
                <h2>Live Activity</h2>
                <Gauge size={17} />
              </div>
              <div className="event-list">
                {events.length ? events.map((event) => (
                  <div key={`${event.timestamp}-${event.event}`}>
                    <CheckCircle2 size={15} />
                    <span>
                      <strong>{eventLabels[event.event] ?? event.event}</strong>
                      {event.complaint_id ?? "No complaint id"}
                    </span>
                  </div>
                )) : (
                  <EmptyPanel title="No WebSocket events" body="Events appear here when the backend broadcasts processing updates." />
                )}
              </div>
            </article>
          </aside>
        </section>
      </section>
    </main>
  );
}
