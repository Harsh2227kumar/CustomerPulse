import { request } from "./client";
import type {
  ComplaintVolumeInsightsResponse,
  HighUrgencyResponse,
  ProductSummaryResponse,
  TrendResponse,
} from "./types";

type Granularity = "day" | "week" | "month";

export type ComplaintVolumeGroupBy =
  | "product"
  | "channel"
  | "category"
  | "sentiment"
  | "churn_risk"
  | "ai_status";

interface ComplaintVolumeInsightsParams {
  granularity?: Granularity;
  group_by?: ComplaintVolumeGroupBy;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

function buildQuery(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const suffix = search.toString();
  return suffix ? `?${suffix}` : "";
}

export function getComplaintVolumeInsights(
  params: ComplaintVolumeInsightsParams = {}
): Promise<ComplaintVolumeInsightsResponse> {
  return request<ComplaintVolumeInsightsResponse>(
    `/api/analytics/complaint-volume-insights${buildQuery(params)}`
  );
}


interface HighUrgencyParams {
  threshold?: number;
  limit?: number;
  offset?: number;
}

export function getComplaintTrends(
  granularity: Granularity = "week"
): Promise<TrendResponse> {
  return request<TrendResponse>(
    `/api/analytics/complaint-trends?granularity=${granularity}`
  );
}

export function getProductSummary(): Promise<ProductSummaryResponse> {
  return request<ProductSummaryResponse>("/api/analytics/product-summary");
}

export function getHumanReviewTrends(
  granularity: Granularity = "week"
): Promise<TrendResponse> {
  return request<TrendResponse>(
    `/api/analytics/human-review-trends?granularity=${granularity}`
  );
}

export function getHighUrgency(
  params: HighUrgencyParams | number = {}
): Promise<HighUrgencyResponse> {
  const normalized = typeof params === "number" ? { limit: params } : params;
  const search = new URLSearchParams();
  if (normalized.threshold !== undefined) search.set("threshold", String(normalized.threshold));
  if (normalized.limit !== undefined) search.set("limit", String(normalized.limit));
  if (normalized.offset !== undefined) search.set("offset", String(normalized.offset));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<HighUrgencyResponse>(`/api/analytics/high-urgency${suffix}`);
}
