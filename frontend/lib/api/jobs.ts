import { request } from "./client";
import type { ProcessingJobResponse } from "./types";

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
