/** All shared TypeScript types for the CustomerPulse API. */

// ── Primitives ──────────────────────────────────────────────────────────────

export type Sentiment = "Positive" | "Neutral" | "Negative";
export type ChurnRisk = "Low" | "Medium" | "High";
export type SortDirection = "asc" | "desc";
export type ProcessingStatus =
  | "pending"
  | "processing"
  | "completed"
  | "human_review"
  | "failed";
export type FeedbackAction = "accepted" | "edited" | "rejected" | "escalated";
export type HumanReviewOutcome =
  | "resolved"
  | "pending"
  | "escalated_tier2"
  | "closed";
export type DuplicateStatus = "detected" | "merged" | "rejected";
export type DuplicateDetectionType = "exact" | "near";

// ── Auth ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  username: string;
  actor: string;
  role: string;
  display_name: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  api_key: string;
  user: UserProfile;
}

// ── Health ──────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  s3_import_configured: boolean;
}

// ── Complaints ──────────────────────────────────────────────────────────────

export interface ConfidenceScores {
  sentiment: number;
  category: number;
  urgency: number;
  churn_risk?: number | null;
  draft_response?: number | null;
}

export interface SimilarCaseDetail {
  complaint_id: string;
  similarity_score?: number | null;
  category?: string | null;
  next_action?: string | null;
  approved_response?: string | null;
  ai_status: string;
}

export interface ProcessingRunItem {
  id: string;
  attempt_number: number;
  status_outcome: string;
  trigger_reason: string | null;
  initiated_by: string | null;
  error_category: string | null;
  created_at: string;
  finished_at: string | null;
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
  similar_cases?: SimilarCaseDetail[] | null;
  confidence_scores: ConfidenceScores | null;
  ai_confidence?: number | null;
  ai_reasoning?: string | null;
  grounded_response?: boolean | null;
  retrieval_warning?: string | null;
  human_review_required?: boolean | null;
  review_reason?: string | null;
  human_review_reason?: string | null;
  human_review_created_at?: string | null;
  processed_at: string | null;
  ai_status: ProcessingStatus;
  retry_count?: number | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ComplaintDetail extends ComplaintListItem {
  reviewed_at: string | null;
  reviewer: string | null;
  review_resolution: string | null;
  approved_response: string | null;
  review_notes: string | null;
  embedding_model: string | null;
  embedded_at: string | null;
  processing_runs: ProcessingRunItem[];
}

export interface ComplaintListResponse {
  items: ComplaintListItem[];
  limit: number;
  offset: number;
  count: number;
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
  ai_status: ProcessingStatus | "";
  human_review_reason: string;
  sort_by:
    | "created_at"
    | "date_received"
    | "processed_at"
    | "urgency_score"
    | "sentiment"
    | "churn_risk"
    | "ai_confidence"
    | "ai_status"
    | "relevance";
  sort_direction: SortDirection;
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
  similar_cases: SimilarCaseDetail[];
  confidence_scores: ConfidenceScores;
  ai_confidence: number;
  ai_reasoning: string | null;
  processed_at: string;
  ai_status: ProcessingStatus;
  human_review_reason: string | null;
  human_review_created_at: string | null;
}

export interface ApproveReviewRequest {
  approved_response?: string | null;
  notes?: string | null;
}

export interface ResolveReviewRequest {
  resolution: string;
  notes?: string | null;
}

// ── Jobs ────────────────────────────────────────────────────────────────────

export interface JobCounts {
  queued: number;
  running: number;
  completed: number;
  human_review: number;
  failed: number;
}

export interface JobItemResponse {
  complaint_id: string;
  status: string;
  attempt_count: number;
  error_message: string | null;
  attempt_history: Record<string, unknown>[];
}

export interface ProcessingJobResponse {
  job_id: string;
  job_type: string;
  status: string;
  total_items: number;
  counts: JobCounts;
  created_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  items: JobItemResponse[];
}

// ── Analytics ───────────────────────────────────────────────────────────────

export interface TrendPoint {
  period: string;
  count: number;
}

export interface TrendResponse {
  items: TrendPoint[];
  granularity: string;
}

export interface ProductSummaryRow {
  product: string | null;
  category: string | null;
  count: number;
  avg_urgency: number | null;
}

export interface ProductSummaryResponse {
  items: ProductSummaryRow[];
}

export interface HighUrgencyItem {
  complaint_id: string;
  narrative: string;
  product: string | null;
  channel: string | null;
  urgency_score: number;
  sentiment: string | null;
  created_at: string;
}

export interface HighUrgencyResponse {
  items: HighUrgencyItem[];
  count: number;
  limit: number;
  offset: number;
}

// ── SLA ─────────────────────────────────────────────────────────────────────

export interface SLASummaryResponse {
  total_complaints: number;
  timely_count: number;
  untimely_count: number;
  timely_rate_pct: number;
  avg_urgency_score: number | null;
  high_urgency_untimely_count: number;
  period_from: string | null;
  period_to: string | null;
}

export interface SLAGroupedItem {
  product?: string | null;
  channel?: string | null;
  total: number;
  timely: number;
  untimely: number;
  timely_rate_pct: number;
  avg_urgency_score: number | null;
}

export interface SLAGroupedResponse {
  items: SLAGroupedItem[];
  count: number;
}

export interface SLABreachRiskItem {
  complaint_id: string;
  source_complaint_id: string | null;
  channel: string | null;
  product: string | null;
  timely_response: boolean | null;
  date_received: string | null;
  urgency_score: number | null;
  churn_risk: ChurnRisk | null;
  processed_at: string | null;
  created_at: string;
}

export interface SLABreachRiskResponse {
  items: SLABreachRiskItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface SLATrendItem {
  period: string;
  total: number;
  timely: number;
  untimely: number;
  timely_rate_pct: number;
}

export interface SLATrendResponse {
  granularity: "weekly" | "monthly";
  items: SLATrendItem[];
}

// ── Feedback ─────────────────────────────────────────────────────────────────

export interface AgentFeedbackUpsertRequest {
  agent_id: string;
  feedback_action: FeedbackAction;
  final_response?: string | null;
  action_used?: boolean | null;
  human_review_outcome: HumanReviewOutcome;
  similar_cases_useful?: boolean | null;
  notes?: string | null;
}

export interface FeedbackRead extends AgentFeedbackUpsertRequest {
  complaint_id: string;
  revision_count: number;
  submitted_at: string;
  updated_at: string;
}

export interface FeedbackListResponse {
  items: FeedbackRead[];
  limit: number;
  offset: number;
  count: number;
}

// ── Duplicates ───────────────────────────────────────────────────────────────

export interface DuplicateDetectRequest {
  exact_enabled: boolean;
  near_enabled: boolean;
  near_threshold: number;
}

export interface DuplicateDetectResponse {
  exact_groups_created: number;
  near_groups_created: number;
  total_groups_created: number;
}

export interface DuplicateGroupSummary {
  group_id: string;
  detection_type: DuplicateDetectionType;
  status: DuplicateStatus;
  exact_hash: string | null;
  similarity_threshold: number | null;
  canonical_complaint_id: string | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface DuplicateMemberRead {
  complaint_id: string;
  complaint_pk: string;
  channel: string | null;
  product: string | null;
  issue: string | null;
  company: string | null;
  narrative: string;
  similarity_score: number | null;
  is_primary: boolean;
}

export interface DuplicateGroupRead extends DuplicateGroupSummary {
  merged_at: string | null;
  rejected_at: string | null;
  notes: string | null;
  members: DuplicateMemberRead[];
}

export interface DuplicateGroupListResponse {
  items: DuplicateGroupSummary[];
  limit: number;
  offset: number;
  count: number;
}

export interface ChannelComparisonItem {
  channel_a: string;
  channel_b: string;
  group_count: number;
  complaint_count: number;
}

export interface ChannelComparisonResponse {
  items: ChannelComparisonItem[];
}

// ── Ingestion / S3 ───────────────────────────────────────────────────────────

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
  available: boolean;
  unavailable_reason: string | null;
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

// ── WebSocket ────────────────────────────────────────────────────────────────

export interface WebSocketMessage {
  event: string;
  complaint_id: string | null;
  payload: Record<string, unknown>;
  timestamp: string;
}
