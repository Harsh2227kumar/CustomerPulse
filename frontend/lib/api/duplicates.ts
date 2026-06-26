import { request } from "./client";
import type {
  ChannelComparisonResponse,
  DuplicateDetectRequest,
  DuplicateDetectResponse,
  DuplicateGroupListResponse,
  DuplicateGroupRead,
} from "./types";

export function detectDuplicates(
  payload: DuplicateDetectRequest
): Promise<DuplicateDetectResponse> {
  return request<DuplicateDetectResponse>("/api/duplicates/detect", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listDuplicates(): Promise<DuplicateGroupListResponse> {
  return request<DuplicateGroupListResponse>("/api/duplicates");
}

export function getDuplicateGroup(groupId: string): Promise<DuplicateGroupRead> {
  return request<DuplicateGroupRead>(
    `/api/duplicates/${encodeURIComponent(groupId)}`
  );
}

export function mergeDuplicate(
  groupId: string,
  canonicalComplaintId: string,
  notes?: string
): Promise<DuplicateGroupRead> {
  return request<DuplicateGroupRead>(
    `/api/duplicates/${encodeURIComponent(groupId)}/merge`,
    { method: "POST", body: JSON.stringify({ canonical_complaint_id: canonicalComplaintId, notes }) }
  );
}

export function rejectDuplicate(
  groupId: string,
  notes?: string
): Promise<DuplicateGroupRead> {
  return request<DuplicateGroupRead>(
    `/api/duplicates/${encodeURIComponent(groupId)}/reject`,
    { method: "POST", body: JSON.stringify({ notes }) }
  );
}

export function getDuplicateChannelComparison(): Promise<ChannelComparisonResponse> {
  return request<ChannelComparisonResponse>("/api/duplicates/channel-comparison");
}
