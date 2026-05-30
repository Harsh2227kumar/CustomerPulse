import {
  ArrowLeft,
  BarChart3,
  BriefcaseBusiness,
  CheckCircle2,
  Download,
  FileCheck2,
  Loader2,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  approveReview,
  createEmbeddingBackfillJob,
  createProcessingJob,
  detectDuplicates,
  downloadBackendExport,
  getApiKey,
  getComplaintDetail,
  getDuplicateChannelComparison,
  getFeedback,
  getHighUrgency,
  getHumanReviewTrends,
  getJob,
  getProductSummary,
  getSlaBreachRisk,
  getSlaByChannel,
  getSlaByProduct,
  getSlaSummary,
  listDuplicates,
  listFeedback,
  rerunReview,
  resolveReview,
  retryJob,
  setApiKey,
  submitFeedback,
} from "./api/client";
import type {
  ComplaintDetail,
  DuplicateDetectResponse,
  DuplicateGroupListResponse,
  FeedbackListResponse,
  FeedbackRead,
  HighUrgencyResponse,
  ProcessingJobResponse,
  ProductSummaryResponse,
  SLAGroupedResponse,
  SLABreachRiskResponse,
  SLASummaryResponse,
  TrendResponse,
} from "./types";

interface OperationsPageProps {
  selectedComplaintId: string;
  onBack: () => void;
  onRefreshComplaints: () => void;
}

interface OpsSnapshot {
  productSummary: ProductSummaryResponse | null;
  highUrgency: HighUrgencyResponse | null;
  humanReviewTrends: TrendResponse | null;
  slaSummary: SLASummaryResponse | null;
  slaByProduct: SLAGroupedResponse | null;
  slaByChannel: SLAGroupedResponse | null;
  slaBreachRisk: SLABreachRiskResponse | null;
  duplicates: DuplicateGroupListResponse | null;
  feedback: FeedbackListResponse | null;
}

const emptySnapshot: OpsSnapshot = {
  productSummary: null,
  highUrgency: null,
  humanReviewTrends: null,
  slaSummary: null,
  slaByProduct: null,
  slaByChannel: null,
  slaBreachRisk: null,
  duplicates: null,
  feedback: null,
};

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function asPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "0%";
  return `${Math.round(value)}%`;
}

function formatMaybeDate(value: string | null | undefined): string {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function OperationsPage({ selectedComplaintId, onBack, onRefreshComplaints }: OperationsPageProps) {
  const [apiKey, setApiKeyInput] = useState(() => getApiKey());
  const [complaintId, setComplaintId] = useState(selectedComplaintId);
  const [detail, setDetail] = useState<ComplaintDetail | null>(null);
  const [snapshot, setSnapshot] = useState<OpsSnapshot>(emptySnapshot);
  const [job, setJob] = useState<ProcessingJobResponse | null>(null);
  const [duplicateResult, setDuplicateResult] = useState<DuplicateDetectResponse | null>(null);
  const [singleFeedback, setSingleFeedback] = useState<FeedbackRead | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editedResponse, setEditedResponse] = useState("");
  const [resolution, setResolution] = useState("resolved");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    setComplaintId((current) => current || selectedComplaintId);
  }, [selectedComplaintId]);

  const jobSummary = useMemo(() => {
    if (!job) return "No job loaded";
    const counts = job.counts;
    return `${job.status}: ${counts.completed} done, ${counts.human_review} review, ${counts.failed} failed, ${counts.running} running, ${counts.queued} queued`;
  }, [job]);

  function persistApiKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApiKey(apiKey);
    setMessage(apiKey.trim() ? "API key saved locally for protected backend actions." : "API key cleared.");
  }

  async function runAction(label: string, action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(label);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  }

  async function loadDetail() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    const loaded = await getComplaintDetail(complaintId.trim());
    setDetail(loaded);
    setEditedResponse(loaded.approved_response ?? loaded.draft_response ?? "");
  }

  async function loadOpsSnapshot() {
    const [
      productSummary,
      highUrgency,
      humanReviewTrends,
      slaSummary,
      slaByProduct,
      slaByChannel,
      slaBreachRisk,
      duplicates,
      feedback,
    ] = await Promise.all([
      getProductSummary(),
      getHighUrgency(8),
      getHumanReviewTrends(),
      getSlaSummary(),
      getSlaByProduct(),
      getSlaByChannel(),
      getSlaBreachRisk(),
      listDuplicates(),
      listFeedback(10),
    ]);

    setSnapshot({
      productSummary,
      highUrgency,
      humanReviewTrends,
      slaSummary,
      slaByProduct,
      slaByChannel,
      slaBreachRisk,
      duplicates,
      feedback,
    });
  }

  async function approveCurrentReview() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    const approved = await approveReview(complaintId.trim(), {
      approved_response: editedResponse.trim() || null,
      notes: notes.trim() || null,
    });
    setDetail(approved);
    onRefreshComplaints();
  }

  async function resolveCurrentReview() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    const resolved = await resolveReview(complaintId.trim(), {
      resolution: resolution.trim(),
      notes: notes.trim() || null,
    });
    setDetail(resolved);
    onRefreshComplaints();
  }

  async function rerunCurrentReview() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    await rerunReview(complaintId.trim());
    await loadDetail();
    onRefreshComplaints();
  }

  async function createSingleProcessJob() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    setJob(await createProcessingJob([complaintId.trim()]));
  }

  async function loadJobById() {
    if (!job?.job_id) throw new Error("Create or load a job first.");
    setJob(await getJob(job.job_id));
  }

  async function retryCurrentJob() {
    if (!job?.job_id) throw new Error("Create or load a job first.");
    setJob(await retryJob(job.job_id));
  }

  async function submitAgentFeedback() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    const saved = await submitFeedback(complaintId.trim(), {
      agent_id: "frontend-operator",
      feedback_action: "accepted",
      final_response: editedResponse.trim() || detail?.approved_response || detail?.draft_response || null,
      action_used: true,
      human_review_outcome: "resolved",
      similar_cases_useful: Boolean(detail?.similar_cases?.length),
      notes: notes.trim() || null,
    });
    setSingleFeedback(saved);
  }

  async function loadSingleFeedback() {
    if (!complaintId.trim()) throw new Error("Enter a complaint id first.");
    setSingleFeedback(await getFeedback(complaintId.trim()));
  }

  async function downloadExport(path: "complaints/csv" | "complaints/pdf" | "analytics/csv" | "feedback/csv") {
    const blob = await downloadBackendExport(path);
    saveBlob(blob, `customerpulse-${path.replace("/", "-")}`);
  }

  return (
    <main className="ops-page">
      <header className="queue-page-header ops-header">
        <div>
          <button className="icon-button" type="button" onClick={onBack} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>Backend Operations</h1>
            <p>Review, RAG jobs, analytics, SLA, feedback, duplicates, and export controls</p>
          </div>
        </div>
        <form className="ops-auth" onSubmit={persistApiKey}>
          <ShieldCheck size={16} />
          <input
            value={apiKey}
            onChange={(event) => setApiKeyInput(event.target.value)}
            placeholder="Bearer API key for protected actions"
            type="password"
          />
          <button className="secondary-action compact-action" type="submit">Save key</button>
        </form>
      </header>

      {message ? <div className="ops-banner success"><CheckCircle2 size={16} />{message}</div> : null}
      {error ? <div className="ops-banner error">{error}</div> : null}

      <section className="ops-grid">
        <article className="panel ops-card">
          <div className="panel-heading">
            <div>
              <h2>Complaint Detail And Review</h2>
              <p>Uses the Harsh review contract: detail, approve, resolve, rerun.</p>
            </div>
            <FileCheck2 size={18} />
          </div>
          <div className="ops-form-row">
            <input value={complaintId} onChange={(event) => setComplaintId(event.target.value)} placeholder="Complaint id" />
            <button className="primary-action compact-action" type="button" disabled={busy} onClick={() => runAction("Complaint detail loaded.", loadDetail)}>
              {busy ? <Loader2 className="spin" size={14} /> : <RefreshCcw size={14} />} Load
            </button>
          </div>
          {detail ? (
            <div className="ops-detail">
              <span>Status <strong>{detail.ai_status}</strong></span>
              <span>Review reason <strong>{detail.human_review_reason ?? "None"}</strong></span>
              <span>Reviewer <strong>{detail.reviewer ?? "Not reviewed"}</strong></span>
              <span>Embedding <strong>{detail.embedding_model ?? "Missing"}</strong></span>
              <p>{detail.narrative}</p>
              <textarea value={editedResponse} onChange={(event) => setEditedResponse(event.target.value)} placeholder="Approved or edited response" />
              <div className="ops-form-row">
                <input value={resolution} onChange={(event) => setResolution(event.target.value)} placeholder="Resolution" />
                <input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Review notes" />
              </div>
              <div className="ops-button-row">
                <button type="button" onClick={() => runAction("Review approved.", approveCurrentReview)}>Approve</button>
                <button type="button" onClick={() => runAction("Review resolved.", resolveCurrentReview)}>Resolve</button>
                <button type="button" onClick={() => runAction("Processing rerun completed or routed.", rerunCurrentReview)}>Rerun</button>
              </div>
              <div className="ops-mini-list">
                {(detail.similar_cases ?? []).map((item) => (
                  <span key={item.complaint_id}>
                    Similar {item.complaint_id}: {asPercent((item.similarity_score ?? 0) * 100)} {item.category ?? ""}
                  </span>
                ))}
              </div>
              <div className="ops-mini-list">
                {detail.processing_runs.map((run) => (
                  <span key={run.id}>Attempt {run.attempt_number}: {run.status_outcome} via {run.trigger_reason ?? "unknown"}</span>
                ))}
              </div>
            </div>
          ) : (
            <p className="ops-muted">Select a complaint from the dashboard or paste an ID here.</p>
          )}
        </article>

        <article className="panel ops-card">
          <div className="panel-heading">
            <div>
              <h2>Persisted Jobs</h2>
              <p>Runs process jobs and MiniLM embedding backfills through backend job records.</p>
            </div>
            <BriefcaseBusiness size={18} />
          </div>
          <div className="ops-button-row">
            <button type="button" onClick={() => runAction("Processing job created.", createSingleProcessJob)}>Process selected</button>
            <button type="button" onClick={() => runAction("Embedding backfill job created.", async () => setJob(await createEmbeddingBackfillJob()))}>Embedding backfill</button>
            <button type="button" onClick={() => runAction("Job refreshed.", loadJobById)}>Refresh job</button>
            <button type="button" onClick={() => runAction("Retry queued.", retryCurrentJob)}>Retry failed</button>
          </div>
          <div className="ops-job-card">
            <strong>{job?.job_id ?? "No job id yet"}</strong>
            <span>{jobSummary}</span>
            {job?.items.slice(0, 8).map((item) => (
              <p key={item.complaint_id}>{item.complaint_id}: {item.status} after {item.attempt_count} attempt(s)</p>
            ))}
          </div>
        </article>

        <article className="panel ops-card ops-wide">
          <div className="panel-heading">
            <div>
              <h2>Analytics And SLA</h2>
              <p>Reads backend analytics and SLA modules, not frontend-derived mock metrics.</p>
            </div>
            <BarChart3 size={18} />
          </div>
          <button className="primary-action compact-action" type="button" onClick={() => runAction("Analytics and SLA loaded.", loadOpsSnapshot)}>
            Load backend analytics
          </button>
          <div className="ops-stat-grid">
            <span>Total SLA complaints <strong>{snapshot.slaSummary?.total_complaints ?? 0}</strong></span>
            <span>Timely rate <strong>{asPercent(snapshot.slaSummary?.timely_rate_pct)}</strong></span>
            <span>High urgency untimely <strong>{snapshot.slaSummary?.high_urgency_untimely_count ?? 0}</strong></span>
            <span>Duplicate groups <strong>{snapshot.duplicates?.count ?? 0}</strong></span>
            <span>Feedback rows <strong>{snapshot.feedback?.count ?? 0}</strong></span>
            <span>Human review trend rows <strong>{snapshot.humanReviewTrends?.items.length ?? 0}</strong></span>
          </div>
          <div className="ops-columns">
            <div>
              <h3>Top Products</h3>
              {snapshot.productSummary?.items.slice(0, 6).map((row) => (
                <p key={`${row.product}-${row.category}`}>{row.product ?? "Unknown"}: {row.count} cases, avg urgency {Math.round(row.avg_urgency ?? 0)}</p>
              ))}
            </div>
            <div>
              <h3>SLA By Product</h3>
              {snapshot.slaByProduct?.items.slice(0, 6).map((row) => (
                <p key={`${row.product}-${row.total}`}>{row.product ?? "Unknown"}: {asPercent(row.timely_rate_pct)} timely across {row.total}</p>
              ))}
            </div>
            <div>
              <h3>SLA By Channel</h3>
              {snapshot.slaByChannel?.items.slice(0, 6).map((row) => (
                <p key={`${row.channel}-${row.total}`}>{row.channel ?? "Unknown"}: {asPercent(row.timely_rate_pct)} timely</p>
              ))}
            </div>
            <div>
              <h3>Risk Queue</h3>
              {snapshot.highUrgency?.items.slice(0, 6).map((row) => (
                <p key={row.complaint_id}>{row.complaint_id}: urgency {row.urgency_score}, {row.product ?? "Unknown"}</p>
              ))}
              {snapshot.slaBreachRisk?.items.slice(0, 4).map((row) => (
                <p key={row.complaint_id}>SLA risk {row.complaint_id}: {row.churn_risk ?? "risk unknown"}</p>
              ))}
            </div>
          </div>
        </article>

        <article className="panel ops-card">
          <div className="panel-heading">
            <div>
              <h2>Feedback Loop</h2>
              <p>Submits and reads Atharva feedback records against the selected complaint.</p>
            </div>
            <Sparkles size={18} />
          </div>
          <div className="ops-button-row">
            <button type="button" onClick={() => runAction("Feedback submitted.", submitAgentFeedback)}>Submit accepted feedback</button>
            <button type="button" onClick={() => runAction("Feedback loaded.", loadSingleFeedback)}>Load complaint feedback</button>
          </div>
          <div className="ops-job-card">
            <strong>{singleFeedback?.feedback_action ?? "No single feedback loaded"}</strong>
            <span>{singleFeedback ? `By ${singleFeedback.agent_id}, revision ${singleFeedback.revision_count}` : "Use the selected complaint id above."}</span>
            <p>{singleFeedback?.notes ?? ""}</p>
          </div>
        </article>

        <article className="panel ops-card">
          <div className="panel-heading">
            <div>
              <h2>Duplicate Detection</h2>
              <p>Triggers exact and near duplicate detection, then lists current groups.</p>
            </div>
            <RefreshCcw size={18} />
          </div>
          <div className="ops-button-row">
            <button type="button" onClick={() => runAction("Duplicate detection completed.", async () => setDuplicateResult(await detectDuplicates({ exact_enabled: true, near_enabled: true, near_threshold: 0.92 })))}>Detect</button>
            <button type="button" onClick={() => runAction("Duplicates loaded.", async () => {
              const duplicates = await listDuplicates();
              setSnapshot((current) => ({ ...current, duplicates }));
            })}>List groups</button>
            <button type="button" onClick={() => runAction("Channel comparison loaded.", async () => {
              const comparison = await getDuplicateChannelComparison();
              setMessage(`Channel comparison rows: ${comparison.items.length}`);
            })}>Channel comparison</button>
          </div>
          <div className="ops-job-card">
            <strong>{duplicateResult ? `${duplicateResult.total_groups_created} groups created` : `${snapshot.duplicates?.count ?? 0} groups loaded`}</strong>
            {snapshot.duplicates?.items.slice(0, 6).map((group) => (
              <p key={group.group_id}>{group.group_id}: {group.detection_type}, {group.status}, {group.member_count} members</p>
            ))}
          </div>
        </article>

        <article className="panel ops-card ops-wide">
          <div className="panel-heading">
            <div>
              <h2>Protected Exports</h2>
              <p>Downloads manager/admin export endpoints through the same saved bearer key.</p>
            </div>
            <Download size={18} />
          </div>
          <div className="ops-button-row">
            <button type="button" onClick={() => runAction("Complaint CSV downloaded.", () => downloadExport("complaints/csv"))}>Complaints CSV</button>
            <button type="button" onClick={() => runAction("Complaint PDF downloaded.", () => downloadExport("complaints/pdf"))}>Complaints PDF</button>
            <button type="button" onClick={() => runAction("Analytics CSV downloaded.", () => downloadExport("analytics/csv"))}>Analytics CSV</button>
            <button type="button" onClick={() => runAction("Feedback CSV downloaded.", () => downloadExport("feedback/csv"))}>Feedback CSV</button>
          </div>
          <p className="ops-muted">If an export says unauthorized, save a manager or admin API key at the top of this page.</p>
          <p className="ops-muted">Current complaint loaded at {formatMaybeDate(detail?.processed_at)}.</p>
        </article>
      </section>
    </main>
  );
}
