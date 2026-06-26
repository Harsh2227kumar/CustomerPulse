import type {
  AgentFeedbackUpsertRequest,
  ApproveReviewRequest,
  ChannelComparisonResponse,
  ComplaintFilters,
  ComplaintDetail,
  ComplaintListResponse,
  ComplaintProcessRequest,
  DuplicateDetectRequest,
  DuplicateDetectResponse,
  DuplicateGroupListResponse,
  DuplicateGroupRead,
  FeedbackListResponse,
  FeedbackRead,
  HealthResponse,
  HighUrgencyResponse,
  ProcessedComplaintResponse,
  ProcessingJobResponse,
  ProductSummaryResponse,
  ResolveReviewRequest,
  S3ImportFilters,
  S3ImportOptionsResponse,
  S3ImportPreviewResponse,
  S3ImportResponse,
  SLAGroupedResponse,
  SLABreachRiskResponse,
  SLASummaryResponse,
  SLATrendResponse,
  TrendResponse,
  Complaint360Response,
  CommunicationEntryRead,
} from "../types";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const authStorageKey = "customerpulse_api_key";

export const apiBaseUrl = configuredBaseUrl;

export function getApiKey(): string {
  return window.localStorage.getItem(authStorageKey) ?? import.meta.env.VITE_API_KEY ?? "";
}

export function setApiKey(value: string): void {
  if (value.trim()) {
    window.localStorage.setItem(authStorageKey, value.trim());
  } else {
    window.localStorage.removeItem(authStorageKey);
  }
}

export function websocketUrl(): string {
  const explicit = import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, "");
  if (explicit) {
    return `${explicit}/ws`;
  }

  if (configuredBaseUrl) {
    const url = new URL(configuredBaseUrl);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws";
    return url.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = getApiKey();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    let detail: string | undefined;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      detail = parsed.detail;
    } catch {
      detail = undefined;
    }
    throw new Error(detail || body || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function download(path: string): Promise<Blob> {
  const apiKey = getApiKey();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
  });

  if (!response.ok) {
    throw new Error((await response.text()) || `Download failed with ${response.status}`);
  }

  return response.blob();
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function getComplaints(filters: ComplaintFilters, limit = 50, offset = 0): Promise<ComplaintListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort_by: filters.sort_by,
    sort_direction: filters.sort_direction,
  });

  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.channel.trim()) params.set("channel", filters.channel.trim());
  if (filters.product.trim()) params.set("product", filters.product.trim());
  if (filters.churn_risk) params.set("churn_risk", filters.churn_risk);
  if (filters.urgency_min) params.set("urgency_min", filters.urgency_min);
  if (filters.urgency_max) params.set("urgency_max", filters.urgency_max);
  if (filters.date_received_min) params.set("date_received_min", filters.date_received_min);
  if (filters.date_received_max) params.set("date_received_max", filters.date_received_max);
  if (filters.timely_response) params.set("timely_response", filters.timely_response);
  if (filters.ai_status) params.set("ai_status", filters.ai_status);
  if (filters.human_review_reason.trim()) params.set("human_review_reason", filters.human_review_reason.trim());

  return request<ComplaintListResponse>(`/api/complaints?${params.toString()}`);
}

export function getComplaintDetail(complaintId: string): Promise<ComplaintDetail> {
  return request<ComplaintDetail>(`/api/complaints/${encodeURIComponent(complaintId)}`);
}

export function processComplaint(payload: ComplaintProcessRequest): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>("/api/process", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function processImportedComplaint(complaintId: string): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>(`/api/process/${encodeURIComponent(complaintId)}`, {
    method: "POST",
  });
}

export function approveReview(complaintId: string, payload: ApproveReviewRequest): Promise<ComplaintDetail> {
  return request<ComplaintDetail>(`/api/complaints/${encodeURIComponent(complaintId)}/review/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resolveReview(complaintId: string, payload: ResolveReviewRequest): Promise<ComplaintDetail> {
  return request<ComplaintDetail>(`/api/complaints/${encodeURIComponent(complaintId)}/review/resolve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rerunReview(complaintId: string): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>(`/api/complaints/${encodeURIComponent(complaintId)}/review/rerun`, {
    method: "POST",
  });
}

export function getS3ImportOptions(): Promise<S3ImportOptionsResponse> {
  return request<S3ImportOptionsResponse>("/api/ingestion/s3/options");
}

export function previewS3Import(payload: S3ImportFilters): Promise<S3ImportPreviewResponse> {
  return request<S3ImportPreviewResponse>("/api/ingestion/s3/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function importS3Complaints(payload: S3ImportFilters): Promise<S3ImportResponse> {
  return request<S3ImportResponse>("/api/ingestion/s3/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createProcessingJob(complaintIds: string[]): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>("/api/jobs/process", {
    method: "POST",
    body: JSON.stringify({ complaint_ids: complaintIds }),
  });
}

export function createEmbeddingBackfillJob(): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>("/api/jobs/embedding-backfill", { method: "POST" });
}

export function getJob(jobId: string): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function retryJob(jobId: string): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>(`/api/jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST" });
}

export function getComplaintTrends(): Promise<TrendResponse> {
  return request<TrendResponse>("/api/analytics/complaint-trends");
}

export function getProductSummary(): Promise<ProductSummaryResponse> {
  return request<ProductSummaryResponse>("/api/analytics/product-summary");
}

export function getHumanReviewTrends(): Promise<TrendResponse> {
  return request<TrendResponse>("/api/analytics/human-review-trends");
}

export function getHighUrgency(limit = 10): Promise<HighUrgencyResponse> {
  return request<HighUrgencyResponse>(`/api/analytics/high-urgency?limit=${limit}`);
}

export function getSlaSummary(): Promise<SLASummaryResponse> {
  return request<SLASummaryResponse>("/api/sla/summary");
}

export function getSlaByProduct(): Promise<SLAGroupedResponse> {
  return request<SLAGroupedResponse>("/api/sla/by-product");
}

export function getSlaByChannel(): Promise<SLAGroupedResponse> {
  return request<SLAGroupedResponse>("/api/sla/by-channel");
}

export function getSlaBreachRisk(): Promise<SLABreachRiskResponse> {
  return request<SLABreachRiskResponse>("/api/sla/breach-risk");
}

export function getSlaTrend(): Promise<SLATrendResponse> {
  return request<SLATrendResponse>("/api/sla/trend");
}

export function submitFeedback(complaintId: string, payload: AgentFeedbackUpsertRequest): Promise<FeedbackRead> {
  return request<FeedbackRead>(`/api/feedback/${encodeURIComponent(complaintId)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFeedback(complaintId: string): Promise<FeedbackRead> {
  return request<FeedbackRead>(`/api/feedback/${encodeURIComponent(complaintId)}`);
}

export function listFeedback(limit = 20): Promise<FeedbackListResponse> {
  return request<FeedbackListResponse>(`/api/feedback?limit=${limit}`);
}

export function detectDuplicates(payload: DuplicateDetectRequest): Promise<DuplicateDetectResponse> {
  return request<DuplicateDetectResponse>("/api/duplicates/detect", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listDuplicates(): Promise<DuplicateGroupListResponse> {
  return request<DuplicateGroupListResponse>("/api/duplicates");
}

export function getDuplicateGroup(groupId: string): Promise<DuplicateGroupRead> {
  return request<DuplicateGroupRead>(`/api/duplicates/${encodeURIComponent(groupId)}`);
}

export function mergeDuplicate(groupId: string, canonicalComplaintId: string, notes?: string): Promise<DuplicateGroupRead> {
  return request<DuplicateGroupRead>(`/api/duplicates/${encodeURIComponent(groupId)}/merge`, {
    method: "POST",
    body: JSON.stringify({ canonical_complaint_id: canonicalComplaintId, notes }),
  });
}

export function rejectDuplicate(groupId: string, notes?: string): Promise<DuplicateGroupRead> {
  return request<DuplicateGroupRead>(`/api/duplicates/${encodeURIComponent(groupId)}/reject`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export function getDuplicateChannelComparison(): Promise<ChannelComparisonResponse> {
  return request<ChannelComparisonResponse>("/api/duplicates/channel-comparison");
}

export function downloadBackendExport(path: "complaints/csv" | "complaints/pdf" | "analytics/csv" | "feedback/csv"): Promise<Blob> {
  return download(`/api/exports/${path}`);
}

export function getComplaint360(complaintId: string): Promise<Complaint360Response> {
  return request<Complaint360Response>(`/api/complaints/${encodeURIComponent(complaintId)}/360`);
}

export function addTimelineNote(complaintId: string, message: string): Promise<CommunicationEntryRead> {
  return request<CommunicationEntryRead>(`/api/complaints/${encodeURIComponent(complaintId)}/timeline`, {
    method: "POST",
    body: JSON.stringify({ entry_type: "note", message }),
  });
}

