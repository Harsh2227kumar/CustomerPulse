import { formRequest, request } from "./client";
import type { ComplianceRegulator, RegulatoryChunkEmbeddingBackfillResult, RegulatoryDocumentProcessResult, RegulatoryDocumentRead, RegulatoryKnowledgeSearchResponse } from "./types";

interface UploadRegulatoryDocumentInput {
  file: File;
  regulator: ComplianceRegulator;
  documentTitle: string;
  version: string;
  effectiveFrom?: string;
  effectiveTo?: string;
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

export function embedRegulatoryDocumentChunks(documentId: string): Promise<RegulatoryChunkEmbeddingBackfillResult> {
  return request<RegulatoryChunkEmbeddingBackfillResult>(`/api/compliance/regulatory-documents/${documentId}/embedding-backfill`, { method: "POST" });
}

export function searchRegulatoryKnowledge(query: string): Promise<RegulatoryKnowledgeSearchResponse> {
  return request<RegulatoryKnowledgeSearchResponse>("/api/compliance/regulatory-search", {
    method: "POST",
    body: JSON.stringify({ query, regulator: "RBI", status: "draft", limit: 8 }),
  });
}
