import { request } from "./client";
import type {
  S3ImportFilters,
  S3ImportOptionsResponse,
  S3ImportPreviewResponse,
  S3ImportResponse,
} from "./types";

export function getS3ImportOptions(): Promise<S3ImportOptionsResponse> {
  return request<S3ImportOptionsResponse>("/api/ingestion/s3/options");
}

export function previewS3Import(
  payload: S3ImportFilters
): Promise<S3ImportPreviewResponse> {
  return request<S3ImportPreviewResponse>("/api/ingestion/s3/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function importS3Complaints(
  payload: S3ImportFilters
): Promise<S3ImportResponse> {
  return request<S3ImportResponse>("/api/ingestion/s3/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
