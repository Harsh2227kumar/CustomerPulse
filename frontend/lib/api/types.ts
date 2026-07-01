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
  api_key?: string | null;
  user?: UserProfile | null;
  access_token?: string | null;
  role?: string | null;
  employee_id?: string | null;
  must_change_password?: boolean | null;
}


// ── Admin / Employee Management ────────────────────────────────────────────

export type EmployeeRole = "agent" | "manager" | "admin" | "super_admin";
export type EmployeeStatus = "active" | "suspended" | "inactive";

export interface EmployeeRead {
  id: string;
  employee_id: string;
  name: string;
  email: string;
  role: EmployeeRole;
  department_id: string | null;
  reports_to: string | null;
  status: EmployeeStatus;
  must_change_password: boolean;
  created_at: string;
  created_by: string | null;
  updated_at: string;
}

export interface EmployeeListResponse {
  items: EmployeeRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface EmployeeCreateRequest {
  name: string;
  email: string;
  password: string;
  role: EmployeeRole;
  department_id?: string | null;
  reports_to?: string | null;
}

export interface EmployeeUpdateRequest {
  name?: string;
  email?: string;
  role?: EmployeeRole;
  department_id?: string | null;
  reports_to?: string | null;
}

export interface DepartmentRead {
  id: string;
  name: string;
  code: string;
  created_at: string;
  employee_count: number;
}

export interface DepartmentListResponse {
  items: DepartmentRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface DepartmentCreateRequest {
  name: string;
  code: string;
}

export interface ResetPasswordResponse {
  temporary_password: string;
}

export interface AdminDashboardResponse {
  employee_counts: { total: number; active: number; suspended: number; inactive: number };
  role_counts: Record<string, number>;
  department_count: number;
  recently_active_employees: number;
  complaints_today: number;
  open_complaints: number;
  escalated_complaints: number;
  sla_breaches_today: number;
  generated_at: string;
}

export interface AuditLogEntry {
  id: string;
  actor_employee_id: string | null;
  actor_name: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface LoginHistoryEntry {
  id: string;
  employee_id: string | null;
  actor_name: string | null;
  action: string;
  created_at: string;
  details: Record<string, unknown> | null;
}

export interface LoginHistoryListResponse {
  items: LoginHistoryEntry[];
  total: number;
  limit: number;
  offset: number;
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
  sla_deadline?: string | null;
  sla_status?: string | null;
  assigned_agent_id?: string | null;
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

export interface JobListResponse {
  items: ProcessingJobResponse[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface JobListResponse {
  items: ProcessingJobResponse[];
  total_count: number;
  limit: number;
  offset: number;
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

export interface ComplaintVolumeSummary {
  total_count: number;
  avg_per_period: number;
  peak_period: string | null;
  peak_count: number;
  high_urgency_count: number;
  human_review_count: number;
  negative_count: number;
  avg_urgency: number | null;
}

export interface ComplaintVolumeTimelineItem {
  period: string;
  total: number;
  high_urgency: number;
  human_review: number;
  negative: number;
  timely: number;
  untimely: number;
  avg_urgency: number | null;
}

export interface ComplaintVolumeGroupItem {
  group: string;
  count: number;
  avg_urgency: number | null;
  high_urgency: number;
  negative: number;
  human_review: number;
}

export interface ComplaintVolumeHeatmapItem {
  product: string;
  channel: string;
  count: number;
  avg_urgency: number | null;
}

export interface ComplaintVolumeMixItem {
  label: string;
  count: number;
}

export interface ComplaintVolumeSampleItem {
  complaint_id: string;
  product: string | null;
  channel: string | null;
  category: string | null;
  sentiment: string | null;
  ai_status: string;
  urgency_score: number | null;
  date_received: string | null;
  narrative: string;
}

export interface ComplaintVolumeInsightsResponse {
  granularity: string;
  group_by: string;
  summary: ComplaintVolumeSummary;
  timeline: ComplaintVolumeTimelineItem[];
  groups: ComplaintVolumeGroupItem[];
  heatmap: ComplaintVolumeHeatmapItem[];
  sentiment_mix: ComplaintVolumeMixItem[];
  status_mix: ComplaintVolumeMixItem[];
  samples: ComplaintVolumeSampleItem[];
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

// ── Regulatory RAG ─────────────────────────────────────────────────────────

export type ComplianceRegulator = "RBI" | "NPCI" | "SEBI" | "IRDAI" | "BANK_INTERNAL";
export type RegulatoryDocumentStatus = "uploaded" | "processing" | "indexed" | "review_required" | "active" | "archived" | "failed";

export interface RegulatoryDocumentRead {
  id: string;
  regulator: ComplianceRegulator;
  document_title: string;
  document_type: string;
  source_filename: string;
  source_url: string | null;
  storage_path: string;
  version: string;
  effective_from: string | null;
  effective_to: string | null;
  status: RegulatoryDocumentStatus;
  uploaded_by: string | null;
  uploaded_at: string;
  created_at: string;
  updated_at: string;
}

export interface RegulatoryDocumentListResponse {
  items: RegulatoryDocumentRead[];
  limit: number;
  offset: number;
  count: number;
}

export interface RegulatoryDocumentProcessResult {
  document: RegulatoryDocumentRead;
  markdown_file: { id: string; document_id: string; markdown_path: string; conversion_tool: string; conversion_status: string; conversion_warnings: string[]; created_at: string; updated_at: string; } | null;
  pages_created: number;
  chunks_created: number;
  warnings: string[];
}

export interface RegulatoryChunkEmbeddingBackfillResult {
  document_id: string | null;
  embedding_model: string;
  embedded_count: number;
  skipped_count: number;
}

export interface RegulatoryKnowledgeSearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string | null;
  regulator: ComplianceRegulator;
  domain: string;
  section_reference: string | null;
  page_start: number | null;
  page_end: number | null;
  similarity_score: number;
  chunk_text: string;
  keywords: string[];
  effective_from: string | null;
  effective_to: string | null;
}

export interface RegulatoryKnowledgeSearchResponse {
  query: string;
  embedding_model: string;
  results: RegulatoryKnowledgeSearchResult[];
}



