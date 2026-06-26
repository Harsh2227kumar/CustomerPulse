import { download, request } from "./client";
import type {
  ApproveReviewRequest,
  ComplaintDetail,
  ComplaintFilters,
  ComplaintListResponse,
  ComplaintProcessRequest,
  HealthResponse,
  ProcessedComplaintResponse,
  ResolveReviewRequest,
} from "./types";

// ── Health ───────────────────────────────────────────────────────────────────

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

// ── Complaint list ───────────────────────────────────────────────────────────

export function getComplaints(
  filters: ComplaintFilters,
  limit = 50,
  offset = 0
): Promise<ComplaintListResponse> {
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
  if (filters.date_received_min)
    params.set("date_received_min", filters.date_received_min);
  if (filters.date_received_max)
    params.set("date_received_max", filters.date_received_max);
  if (filters.timely_response)
    params.set("timely_response", filters.timely_response);
  if (filters.ai_status) params.set("ai_status", filters.ai_status);
  if (filters.human_review_reason.trim())
    params.set("human_review_reason", filters.human_review_reason.trim());

  return request<ComplaintListResponse>(`/api/complaints?${params.toString()}`);
}

// ── Complaint detail ─────────────────────────────────────────────────────────

export function getComplaintDetail(
  complaintId: string
): Promise<ComplaintDetail> {
  return request<ComplaintDetail>(
    `/api/complaints/${encodeURIComponent(complaintId)}`
  );
}

// ── Complaint processing ─────────────────────────────────────────────────────

/** Create and immediately process a new complaint (ticket). */
export function processComplaint(
  payload: ComplaintProcessRequest
): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>("/api/process", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Re-process an already-imported complaint by ID. */
export function processImportedComplaint(
  complaintId: string
): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>(
    `/api/process/${encodeURIComponent(complaintId)}`,
    { method: "POST" }
  );
}

// ── Review actions ───────────────────────────────────────────────────────────

export function approveReview(
  complaintId: string,
  payload: ApproveReviewRequest
): Promise<ComplaintDetail> {
  return request<ComplaintDetail>(
    `/api/complaints/${encodeURIComponent(complaintId)}/review/approve`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export function resolveReview(
  complaintId: string,
  payload: ResolveReviewRequest
): Promise<ComplaintDetail> {
  return request<ComplaintDetail>(
    `/api/complaints/${encodeURIComponent(complaintId)}/review/resolve`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export function rerunReview(
  complaintId: string
): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>(
    `/api/complaints/${encodeURIComponent(complaintId)}/review/rerun`,
    { method: "POST" }
  );
}

// ── Exports ──────────────────────────────────────────────────────────────────

export type ExportPath =
  | "complaints/csv"
  | "complaints/pdf"
  | "analytics/csv"
  | "feedback/csv";

export function downloadExport(path: ExportPath): Promise<Blob> {
  return download(`/api/exports/${path}`);
}
