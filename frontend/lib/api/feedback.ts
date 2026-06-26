import { request } from "./client";
import type {
  AgentFeedbackUpsertRequest,
  FeedbackListResponse,
  FeedbackRead,
} from "./types";

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

export function listFeedback(limit = 20): Promise<FeedbackListResponse> {
  return request<FeedbackListResponse>(`/api/feedback?limit=${limit}`);
}
