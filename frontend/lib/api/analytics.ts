import { request } from "./client";
import type {
  HighUrgencyResponse,
  ProductSummaryResponse,
  TrendResponse,
} from "./types";

type Granularity = "day" | "week" | "month";

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

export function getHighUrgency(limit = 10): Promise<HighUrgencyResponse> {
  return request<HighUrgencyResponse>(
    `/api/analytics/high-urgency?limit=${limit}`
  );
}
