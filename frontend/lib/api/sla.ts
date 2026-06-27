import { request } from "./client";
import type {
  ChurnRisk,
  SLABreachRiskResponse,
  SLAGroupedResponse,
  SLASummaryResponse,
  SLATrendResponse,
} from "./types";

export type SLAGroupSortBy = "timely_rate" | "total" | "untimely_count";
export type SLATrendGranularity = "weekly" | "monthly";

export interface SLASummaryParams {
  date_from?: string;
  date_to?: string;
  product?: string;
  channel?: string;
}

export interface SLAGroupedParams {
  date_from?: string;
  date_to?: string;
  limit?: number;
  sort_by?: SLAGroupSortBy;
}

export interface SLABreachRiskParams {
  urgency_threshold?: number;
  churn_risk?: ChurnRisk;
  limit?: number;
  offset?: number;
}

export interface SLATrendParams {
  granularity?: SLATrendGranularity;
  date_from?: string;
  date_to?: string;
  product?: string;
}

function query(params: object): string {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, String(value));
    }
  });
  const value = qs.toString();
  return value ? `?${value}` : "";
}

export function getSlaSummary(params: SLASummaryParams = {}): Promise<SLASummaryResponse> {
  return request<SLASummaryResponse>(`/api/sla/summary${query(params)}`);
}

export function getSlaByProduct(params: SLAGroupedParams = {}): Promise<SLAGroupedResponse> {
  return request<SLAGroupedResponse>(`/api/sla/by-product${query(params)}`);
}

export function getSlaByChannel(params: SLAGroupedParams = {}): Promise<SLAGroupedResponse> {
  return request<SLAGroupedResponse>(`/api/sla/by-channel${query(params)}`);
}

export function getSlaBreachRisk(params: SLABreachRiskParams | number = {}): Promise<SLABreachRiskResponse> {
  const normalized = typeof params === "number" ? { limit: params } : params;
  return request<SLABreachRiskResponse>(`/api/sla/breach-risk${query(normalized)}`);
}

export function getSlaTrend(params: SLATrendParams | SLATrendGranularity = {}): Promise<SLATrendResponse> {
  const normalized = typeof params === "string" ? { granularity: params } : params;
  return request<SLATrendResponse>(`/api/sla/trend${query({ granularity: "weekly", ...normalized })}`);
}
