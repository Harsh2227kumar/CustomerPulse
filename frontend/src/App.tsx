import {
  Activity,
  BarChart3,
  Bell,
  Bot,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
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
import { type CSSProperties, type FormEvent, useEffect, useMemo, useState } from "react";
import { getComplaints, getHealth, processComplaint, websocketUrl } from "./api/client";
import { S3ImportPage } from "./S3ImportPage";
import type {
  ChurnRisk,
  ComplaintFilters,
  ComplaintListItem,
  HealthResponse,
  ProcessedComplaintResponse,
  Sentiment,
  WebSocketMessage,
} from "./types";

const initialFilters: ComplaintFilters = {
  search: "",
  sentiment: "",
  churn_risk: "",
  urgency_min: "",
  urgency_max: "",
  timely_response: "",
  sort_by: "created_at",
  sort_direction: "desc",
};

const eventLabels: Record<string, string> = {
  received: "Received",
  preprocessing: "Preprocessing",
  local_ml: "Local scoring",
  bedrock_processing: "Bedrock analysis",
  validating: "Validation",
  saved: "Saved",
  failed: "Failed",
};

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
  const [activeView, setActiveView] = useState<"dashboard" | "import">("dashboard");
  const [filters, setFilters] = useState<ComplaintFilters>(initialFilters);
  const [complaints, setComplaints] = useState<ComplaintListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "live" | "offline">("connecting");
  const [events, setEvents] = useState<WebSocketMessage[]>([]);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<ProcessedComplaintResponse | null>(null);
  const [processError, setProcessError] = useState<string | null>(null);
  const [form, setForm] = useState({
    narrative: "",
    channel: "",
    product: "",
    issue: "",
    company: "",
  });

  async function loadComplaints() {
    setLoading(true);
    setError(null);
    try {
      const [complaintResponse, healthResponse] = await Promise.all([
        getComplaints(filters),
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
  }, [filters.sort_by, filters.sort_direction]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      loadComplaints();
    }, 350);
    return () => window.clearTimeout(timeout);
  }, [filters.search, filters.sentiment, filters.churn_risk, filters.urgency_min, filters.urgency_max, filters.timely_response]);

  useEffect(() => {
    const socket = new WebSocket(websocketUrl());
    socket.onopen = () => setWsStatus("live");
    socket.onclose = () => setWsStatus("offline");
    socket.onerror = () => setWsStatus("offline");
    socket.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as WebSocketMessage;
        setEvents((current) => [parsed, ...current].slice(0, 8));
        if (parsed.event === "saved") {
          loadComplaints();
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
    return {
      avgUrgency,
      highRisk,
      completed,
      timelyRate: complaints.length ? (timely / complaints.length) * 100 : 0,
      products: uniqueCount(complaints, "product"),
    };
  }, [complaints]);

  const sparkline = useMemo(() => buildSparkline(complaints), [complaints]);
  const bars = useMemo(() => weeklyBars(complaints), [complaints]);
  const maxBar = Math.max(...bars, 1);

  async function submitComplaint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
          <a href="#analytics"><BarChart3 size={16} />Analytics</a>
          <a href="#activity"><Activity size={16} />Activity</a>
          <a href="#settings"><Settings size={16} />Settings</a>
        </nav>
        <section className="upgrade-card">
          <strong>Real Data Mode</strong>
          <span>Dashboard panels render only backend and database responses.</span>
          <button type="button" onClick={loadComplaints}>Refresh API</button>
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
            <button className="icon-button" type="button" onClick={loadComplaints} aria-label="Refresh"><RefreshCcw size={17} /></button>
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
                <div className="info-list">
                  <span>Channel <strong>{selectedComplaint.channel ?? "Unknown"}</strong></span>
                  <span>Date received <strong>{formatDate(selectedComplaint.date_received)}</strong></span>
                  <span>Processed <strong>{formatDateTime(selectedComplaint.processed_at)}</strong></span>
                  <span>Timely response <strong>{selectedComplaint.timely_response ?? "Unknown"}</strong></span>
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

            <article className="panel chart-panel" id="analytics">
              <div className="panel-heading">
                <div>
                  <h2>Complaint Trend</h2>
                  <p>{metrics.products} product groups in the current backend result window</p>
                </div>
                <select
                  value={filters.sort_by}
                  onChange={(event) => setFilters((current) => ({ ...current, sort_by: event.target.value as ComplaintFilters["sort_by"] }))}
                >
                  <option value="created_at">Created</option>
                  <option value="processed_at">Processed</option>
                  <option value="urgency_score">Urgency</option>
                  <option value="sentiment">Sentiment</option>
                  <option value="churn_risk">Churn risk</option>
                </select>
              </div>
              {sparkline ? (
                <svg viewBox="0 0 200 96" role="img" aria-label="Complaint volume trend">
                  <defs>
                    <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#2ec6a6" stopOpacity="0.32" />
                      <stop offset="100%" stopColor="#2ec6a6" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <polyline points={sparkline} fill="none" stroke="#164f47" strokeWidth="3" strokeLinecap="round" />
                  <polyline points={`8,88 ${sparkline} 192,88`} fill="url(#trendFill)" stroke="none" />
                </svg>
              ) : (
                <EmptyPanel title="No dated records" body="Trend appears after real complaints include date fields." />
              )}
            </article>

            <article className="panel table-panel" id="complaints">
              <div className="panel-heading">
                <div>
                  <h2>Complaint Queue</h2>
                  <p>{loading ? "Loading backend rows" : `${complaints.length} of ${totalCount} records shown`}</p>
                </div>
                <div className="filter-row">
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
                </div>
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
                            <span>{complaint.narrative}</span>
                          </td>
                          <td><span className={`badge ${sentimentClass(complaint.sentiment)}`}>{complaint.sentiment ?? "Unknown"}</span></td>
                          <td>
                            <div className="bar-cell"><span style={{ width: `${complaint.urgency_score ?? 0}%` }} />{complaint.urgency_score ?? 0}</div>
                          </td>
                          <td><span className={`badge ${riskClass(complaint.churn_risk)}`}>{complaint.churn_risk ?? "Unknown"}</span></td>
                          <td>{percent(complaint.confidence_scores?.sentiment)}</td>
                          <td><span className={`status-pill ${complaint.ai_status}`}>{complaint.ai_status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyPanel title="No real complaints returned" body="The frontend has no fallback rows. Run real ingestion or submit a live complaint." />
              )}
            </article>

            <section className="lower-grid">
              <article className="panel bars-panel">
                <div className="panel-heading">
                  <h2>Weekly Activity</h2>
                  <span>This result window</span>
                </div>
                <div className="bars">
                  {bars.map((value, index) => (
                    <div key={index} className="bar-wrap">
                      <span style={{ height: `${Math.max(8, (value / maxBar) * 100)}%` }} />
                      <small>{["S", "M", "T", "W", "T", "F", "S"][index]}</small>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel detail-panel">
                <div className="panel-heading">
                  <h2>AI Detail</h2>
                  <Bot size={18} />
                </div>
                {selectedComplaint ? (
                  <div className="detail-copy">
                    <span>Category</span>
                    <strong>{selectedComplaint.category ?? "Not classified"}</strong>
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
                <button type="submit" disabled={processing}>
                  {processing ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
                  Process complaint
                </button>
              </form>
              {processError && <p className="form-error">{processError}</p>}
              {processResult && (
                <div className="result-card">
                  <strong>{processResult.category}</strong>
                  <span>{processResult.sentiment} / {processResult.churn_risk}</span>
                  <p>{processResult.next_action}</p>
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
