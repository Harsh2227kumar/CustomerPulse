import type {
  ComplaintFilters,
  ComplaintListResponse,
  ComplaintProcessRequest,
  HealthResponse,
  ProcessedComplaintResponse,
  S3ImportFilters,
  S3ImportOptionsResponse,
  S3ImportPreviewResponse,
  S3ImportResponse,
} from "../types";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export const apiBaseUrl = configuredBaseUrl;

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
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
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

  return request<ComplaintListResponse>(`/api/complaints?${params.toString()}`);
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
