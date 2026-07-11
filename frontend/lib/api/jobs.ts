import { request } from "./client";
import type { ContinuousProcessingStatus, JobListResponse, ProcessingJobResponse } from "./types";

export interface JobListParams {
  limit?: number;
  offset?: number;
  job_type?: "process_complaints" | "embedding_backfill" | "";
  status?: "queued" | "running" | "completed" | "completed_with_errors" | "failed" | "";
}

function queryString(params: JobListParams): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export function listJobs(params: JobListParams = {}): Promise<JobListResponse> {
  return request<JobListResponse>(`/api/jobs${queryString(params)}`);
}

export function createProcessingJob(
  complaintIds: string[]
): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>("/api/jobs/process", {
    method: "POST",
    body: JSON.stringify({ complaint_ids: complaintIds }),
  });
}

export function createEmbeddingBackfillJob(): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>("/api/jobs/embedding-backfill", {
    method: "POST",
  });
}

export function getJob(jobId: string): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>(
    `/api/jobs/${encodeURIComponent(jobId)}`
  );
}

export function retryJob(jobId: string): Promise<ProcessingJobResponse> {
  return request<ProcessingJobResponse>(
    `/api/jobs/${encodeURIComponent(jobId)}/retry`,
    { method: "POST" }
  );
}



export function getContinuousProcessingStatus(): Promise<ContinuousProcessingStatus> {
  return request<ContinuousProcessingStatus>("/api/jobs/continuous/status");
}

export function startContinuousProcessing(): Promise<ContinuousProcessingStatus> {
  return request<ContinuousProcessingStatus>("/api/jobs/continuous/start", {
    method: "POST",
  });
}

export function stopContinuousProcessing(): Promise<ContinuousProcessingStatus> {
  return request<ContinuousProcessingStatus>("/api/jobs/continuous/stop", {
    method: "POST",
  });
}
