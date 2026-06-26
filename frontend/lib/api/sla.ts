import { request } from "./client";
import type {
  SLABreachRiskResponse,
  SLAGroupedResponse,
  SLASummaryResponse,
  SLATrendResponse,
} from "./types";

export function getSlaSummary(): Promise<SLASummaryResponse> {
  return request<SLASummaryResponse>("/api/sla/summary");
}

export function getSlaByProduct(): Promise<SLAGroupedResponse> {
  return request<SLAGroupedResponse>("/api/sla/by-product");
}

export function getSlaByChannel(): Promise<SLAGroupedResponse> {
  return request<SLAGroupedResponse>("/api/sla/by-channel");
}

export function getSlaBreachRisk(limit = 20): Promise<SLABreachRiskResponse> {
  return request<SLABreachRiskResponse>(`/api/sla/breach-risk?limit=${limit}`);
}

export function getSlaTrend(
  granularity: "weekly" | "monthly" = "weekly"
): Promise<SLATrendResponse> {
  return request<SLATrendResponse>(
    `/api/sla/trend?granularity=${granularity}`
  );
}
