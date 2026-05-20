import type {
  ComplaintFilters,
  ComplaintListResponse,
  ComplaintProcessRequest,
  HealthResponse,
  ProcessedComplaintResponse,
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
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
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
  if (filters.churn_risk) params.set("churn_risk", filters.churn_risk);
  if (filters.urgency_min) params.set("urgency_min", filters.urgency_min);
  if (filters.urgency_max) params.set("urgency_max", filters.urgency_max);
  if (filters.timely_response) params.set("timely_response", filters.timely_response);

  return request<ComplaintListResponse>(`/api/complaints?${params.toString()}`);
}

export function processComplaint(payload: ComplaintProcessRequest): Promise<ProcessedComplaintResponse> {
  return request<ProcessedComplaintResponse>("/api/process", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
