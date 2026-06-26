import { download, request } from "./client";
import type {
  AgentFeedbackUpsertRequest,
  FeedbackAction,
  FeedbackListResponse,
  FeedbackRead,
} from "./types";

export interface FeedbackListParams {
  limit?: number;
  offset?: number;
  agent_id?: string;
  feedback_action?: FeedbackAction | "";
}
export function submitFeedback(
  complaintId: string,
  payload: AgentFeedbackUpsertRequest
): Promise<FeedbackRead> {
  return request<FeedbackRead>(
    `/api/feedback/${encodeURIComponent(complaintId)}`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export function getFeedback(complaintId: string): Promise<FeedbackRead> {
  return request<FeedbackRead>(
    `/api/feedback/${encodeURIComponent(complaintId)}`
  );
}

export function listFeedback(
  limit = 50,
  offset = 0,
  agentId?: string,
  feedbackAction?: string
): Promise<FeedbackListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (agentId) params.set("agent_id", agentId);
  if (feedbackAction) params.set("feedback_action", feedbackAction);
  return request<FeedbackListResponse>(`/api/feedback?${params.toString()}`);
}

export function exportFeedbackNdjson(): Promise<Blob> {
  return download("/api/feedback/export");
}
