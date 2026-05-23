export type Sentiment = "Positive" | "Neutral" | "Negative";
export type ChurnRisk = "Low" | "Medium" | "High";
export type SortDirection = "asc" | "desc";

export interface ConfidenceScores {
  sentiment: number;
  category: number;
  urgency: number;
  churn_risk?: number | null;
  draft_response?: number | null;
}

export interface ComplaintListItem {
  complaint_id: string;
  narrative: string;
  channel: string | null;
  product: string | null;
  issue: string | null;
  date_received: string | null;
  timely_response: "Yes" | "No" | null;
  sentiment: Sentiment | null;
  category: string | null;
  urgency_score: number | null;
  churn_risk: ChurnRisk | null;
  confidence_scores: ConfidenceScores | null;
  processed_at: string | null;
  ai_status: string;
}

export interface ComplaintListResponse {
  items: ComplaintListItem[];
  limit: number;
  offset: number;
  count: number;
}

export interface ComplaintProcessRequest {
  complaint_id: string;
  narrative: string;
  channel?: string | null;
  product?: string | null;
  issue?: string | null;
  company?: string | null;
}

export interface ProcessedComplaintResponse {
  complaint_id: string;
  narrative: string;
  channel: string | null;
  sentiment: Sentiment;
  category: string;
  urgency_score: number;
  churn_risk: ChurnRisk;
  draft_response: string;
  next_action: string;
  similar_cases: string[];
  confidence_scores: ConfidenceScores;
  ai_confidence: number;
  ai_reasoning: string | null;
  processed_at: string;
}

export interface ComplaintFilters {
  search: string;
  sentiment: Sentiment | "";
  churn_risk: ChurnRisk | "";
  urgency_min: string;
  urgency_max: string;
  timely_response: "" | "true" | "false";
  sort_by: "created_at" | "processed_at" | "urgency_score" | "sentiment" | "churn_risk";
  sort_direction: SortDirection;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export interface WebSocketMessage {
  event: string;
  complaint_id: string | null;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface S3ImportFilters {
  product: string | null;
  sub_product: string | null;
  issue: string | null;
  company: string | null;
  channel: string | null;
  timely_response: boolean | null;
  date_received_min: string | null;
  date_received_max: string | null;
  max_records: number;
}

export interface S3SourceSummary {
  bucket: string;
  key: string;
}

export interface S3ImportOptionsResponse {
  source: S3SourceSummary;
  scanned_rows: number;
  eligible_rows: number;
  products: string[];
  sub_products: string[];
  issues: string[];
  companies: string[];
  channels: string[];
}

export interface S3PreviewItem {
  complaint_id: string;
  narrative: string;
  product: string | null;
  sub_product: string | null;
  issue: string | null;
  company: string | null;
  channel: string | null;
  timely_response: boolean | null;
  date_received: string | null;
}

export interface S3ImportPreviewResponse {
  source: S3SourceSummary;
  scanned_rows: number;
  matched_rows: number;
  selected_rows: number;
  items: S3PreviewItem[];
}

export interface S3ImportLog {
  level: "info" | "success" | "error";
  message: string;
}

export interface S3ImportResponse {
  status: "success";
  source: S3SourceSummary;
  scanned_rows: number;
  matched_rows: number;
  imported_rows: number;
  skipped_rows: number;
  logs: S3ImportLog[];
}
