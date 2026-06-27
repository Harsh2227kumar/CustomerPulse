import { request } from "./client";
import type {
  ChannelComparisonResponse,
  DuplicateDetectRequest,
  DuplicateDetectResponse,
  DuplicateDetectionType,
  DuplicateGroupListResponse,
  DuplicateGroupRead,
  DuplicateStatus,
} from "./types";

export interface DuplicateListParams {
  limit?: number;
  offset?: number;
  detection_type?: DuplicateDetectionType | "";
  status?: DuplicateStatus | "";
}

function queryString(params: DuplicateListParams): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export function detectDuplicates(
  payload: DuplicateDetectRequest
): Promise<DuplicateDetectResponse> {
  return request<DuplicateDetectResponse>("/api/duplicates/detect", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listDuplicates(params: DuplicateListParams = {}): Promise<DuplicateGroupListResponse> {
  return request<DuplicateGroupListResponse>(`/api/duplicates${queryString(params)}`);
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
    {
      method: "POST",
      body: JSON.stringify({ canonical_complaint_id: canonicalComplaintId, notes }),
    }
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
