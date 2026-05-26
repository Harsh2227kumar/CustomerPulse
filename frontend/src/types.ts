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

export interface SimilarCaseDetail {
  case_id?: string | null;
  complaint_id?: string | null;
  similarity_score?: number | null;
  score?: number | null;
  category?: string | null;
  evidence_summary?: string | null;
  summary?: string | null;
  title?: string | null;
}

export interface ProcessingHistoryItem {
  event: string;
  status?: string | null;
  reason?: string | null;
  timestamp?: string | null;
}

export interface ComplaintListItem {
  complaint_id: string;
  narrative: string;
  channel: string | null;
  product: string | null;
  sub_product?: string | null;
  issue: string | null;
  sub_issue?: string | null;
  company?: string | null;
  company_response?: string | null;
  date_received: string | null;
  timely_response: "Yes" | "No" | null;
  sentiment: Sentiment | null;
  category: string | null;
  urgency_score: number | null;
  churn_risk: ChurnRisk | null;
  draft_response?: string | null;
  next_action?: string | null;
  similar_cases?: Array<string | SimilarCaseDetail> | null;
  confidence_scores: ConfidenceScores | null;
  ai_confidence?: number | null;
  ai_reasoning?: string | null;
  grounded_response?: boolean | null;
  retrieval_warning?: string | null;
  omitted_retrievals?: Array<string | SimilarCaseDetail> | null;
  human_review_required?: boolean | null;
  review_reason?: string | null;
  processing_history?: ProcessingHistoryItem[] | null;
  processed_at: string | null;
  ai_status: string;
  retry_count?: number | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
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
  similar_cases: Array<string | SimilarCaseDetail>;
  confidence_scores: ConfidenceScores;
  ai_confidence: number;
  ai_reasoning: string | null;
  processed_at: string;
}

export interface ComplaintFilters {
  search: string;
  sentiment: Sentiment | "";
  channel: string;
  product: string;
  churn_risk: ChurnRisk | "";
  urgency_min: string;
  urgency_max: string;
  date_received_min: string;
  date_received_max: string;
  timely_response: "" | "true" | "false";
  sort_by: "created_at" | "processed_at" | "urgency_score" | "sentiment" | "churn_risk";
  sort_direction: SortDirection;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  s3_import_configured: boolean;
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
  label: string;
}

export interface S3ImportOptionsResponse {
  source: S3SourceSummary;
  query_mode: "csv" | "athena";
  scanned_rows: number | null;
  eligible_rows: number | null;
  products: string[];
  sub_products: string[];
  issues: string[];
  companies: string[];
  channels: string[];
  timely_responses: boolean[];
  date_received_min: string | null;
  date_received_max: string | null;
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
  query_mode: "csv" | "athena";
  scanned_rows: number;
  matched_rows: number;
  selected_rows: number;
  result_limited: boolean;
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
