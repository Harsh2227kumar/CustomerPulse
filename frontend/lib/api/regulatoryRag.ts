import { formRequest, request } from "./client";
import type {
  ComplianceRegulator,
  RegulatoryChunkEmbeddingBackfillResult,
  RegulatoryDocumentListResponse,
  RegulatoryDocumentProcessResult,
  RegulatoryDocumentRead,
  RegulatoryDocumentReviewResult,
  RegulatoryDocumentStatus,
  RegulatoryKnowledgeChunkListResponse,
  RegulatoryKnowledgeSearchResponse,
} from "./types";

interface UploadRegulatoryDocumentInput {
  file: File;
  regulator: ComplianceRegulator;
  documentTitle: string;
  version: string;
  effectiveFrom?: string;
  effectiveTo?: string;
}

export interface RegulatoryDocumentListParams {
  limit?: number;
  offset?: number;
  regulator?: ComplianceRegulator | "";
  status?: RegulatoryDocumentStatus | "";
  document_type?: "pdf" | "docx" | "txt" | "markdown" | "html" | "";
}

export interface RegulatorySearchInput {
  query: string;
  regulator?: ComplianceRegulator | "";
  domain?: string;
  status?: "draft" | "active" | "archived" | "";
  limit?: number;
  minSimilarity?: number;
}

function queryString(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params as Record<string, unknown>).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  const suffix = search.toString();
  return suffix ? `?${suffix}` : "";
}

export function listRegulatoryDocuments(params: RegulatoryDocumentListParams = {}): Promise<RegulatoryDocumentListResponse> {
  return request<RegulatoryDocumentListResponse>(`/api/compliance/regulatory-documents${queryString(params)}`);
}

export function uploadRegulatoryDocument(input: UploadRegulatoryDocumentInput): Promise<RegulatoryDocumentRead> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("regulator", input.regulator);
  formData.append("document_title", input.documentTitle);
  formData.append("version", input.version);
  if (input.effectiveFrom) formData.append("effective_from", input.effectiveFrom);
  if (input.effectiveTo) formData.append("effective_to", input.effectiveTo);
  return formRequest<RegulatoryDocumentRead>("/api/compliance/regulatory-documents/upload", formData);
}

export function processRegulatoryDocument(documentId: string): Promise<RegulatoryDocumentProcessResult> {
  return request<RegulatoryDocumentProcessResult>(`/api/compliance/regulatory-documents/${documentId}/process`, { method: "POST" });
}

export function listRegulatoryDocumentChunks(documentId: string, params: { limit?: number; offset?: number; status?: "draft" | "active" | "archived" | "" } = {}): Promise<RegulatoryKnowledgeChunkListResponse> {
  return request<RegulatoryKnowledgeChunkListResponse>(`/api/compliance/regulatory-documents/${documentId}/chunks${queryString(params)}`);
}

export function reviewRegulatoryDocument(documentId: string, input: { action: "activate" | "request_changes" | "archive"; notes?: string | null }): Promise<RegulatoryDocumentReviewResult> {
  return request<RegulatoryDocumentReviewResult>(`/api/compliance/regulatory-documents/${documentId}/review`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
export function embedRegulatoryDocumentChunks(documentId: string, limit = 100): Promise<RegulatoryChunkEmbeddingBackfillResult> {
  return request<RegulatoryChunkEmbeddingBackfillResult>(`/api/compliance/regulatory-documents/${documentId}/embedding-backfill?limit=${limit}`, { method: "POST" });
}

export function searchRegulatoryKnowledge(input: RegulatorySearchInput): Promise<RegulatoryKnowledgeSearchResponse> {
  return request<RegulatoryKnowledgeSearchResponse>("/api/compliance/regulatory-search", {
    method: "POST",
    body: JSON.stringify({
      query: input.query,
      regulator: input.regulator || null,
      domain: input.domain?.trim() || null,
      status: input.status || null,
      limit: input.limit ?? 8,
      min_similarity: input.minSimilarity ?? 0,
    }),
  });
}

