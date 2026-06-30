"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  Lock,
  Play,
  Search,
  Upload,
  Zap,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  embedRegulatoryDocumentChunks,
  processRegulatoryDocument,
  searchRegulatoryKnowledge,
  uploadRegulatoryDocument,
} from "@/lib/api/regulatoryRag";
import type {
  ComplianceRegulator,
  RegulatoryDocumentRead,
  RegulatoryKnowledgeSearchResult,
} from "@/lib/api/types";

const REGULATORS: ComplianceRegulator[] = ["RBI", "NPCI", "SEBI", "IRDAI", "BANK_INTERNAL"];

export default function RegulatoryRagPage() {
  const { user, isLoading } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [regulator, setRegulator] = useState<ComplianceRegulator>("RBI");
  const [documentTitle, setDocumentTitle] = useState("");
  const [version, setVersion] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [document, setDocument] = useState<RegulatoryDocumentRead | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [embedding, setEmbedding] = useState(false);
  const [searching, setSearching] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RegulatoryKnowledgeSearchResult[]>([]);

  const canUpload = useMemo(
    () => Boolean(file && documentTitle.trim() && version.trim() && !uploading),
    [documentTitle, file, uploading, version]
  );

  if (isLoading) {
    return <div className="card card-body">Loading regulatory workspace...</div>;
  }

  if (user?.role !== "admin") {
    return (
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div className="card">
          <div className="card-body" style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Lock size={22} style={{ color: "var(--color-error)" }} />
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>403 Unauthorized</h1>
              <p style={{ color: "var(--color-on-surface-variant)", fontSize: 13 }}>
                Regulatory RAG administration is available only to admin users.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  async function handleUpload() {
    if (!file || !documentTitle.trim() || !version.trim()) return;
    setUploading(true);
    setError(null);
    setStatusMessage(null);
    try {
      const uploaded = await uploadRegulatoryDocument({
        file,
        regulator,
        documentTitle: documentTitle.trim(),
        version: version.trim(),
        effectiveFrom: effectiveFrom || undefined,
        effectiveTo: effectiveTo || undefined,
      });
      setDocument(uploaded);
      setStatusMessage("Uploaded " + uploaded.document_title + ".");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleProcess() {
    if (!document) return;
    setProcessing(true);
    setError(null);
    try {
      const processed = await processRegulatoryDocument(document.id);
      setDocument(processed.document);
      setStatusMessage("Processed " + processed.pages_created + " page(s) and " + processed.chunks_created + " chunk(s).");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Processing failed");
    } finally {
      setProcessing(false);
    }
  }

  async function handleEmbed() {
    if (!document) return;
    setEmbedding(true);
    setError(null);
    try {
      const result = await embedRegulatoryDocumentChunks(document.id);
      setStatusMessage("Embedded " + result.embedded_count + " chunk(s); skipped " + result.skipped_count + ".");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Embedding backfill failed");
    } finally {
      setEmbedding(false);
    }
  }

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const response = await searchRegulatoryKnowledge(query.trim());
      setResults(response.results);
      setStatusMessage("Found " + response.results.length + " regulatory chunk(s).");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Regulatory RAG</h1>
          <p className="page-subtitle">Upload RBI guideline documents, process regulatory chunks, and test semantic retrieval.</p>
        </div>
      </div>

      {error && (
        <div className="alert-error">
          <AlertTriangle size={14} />
          {error}
        </div>
      )}
      {statusMessage && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", border: "1px solid var(--color-resolved)", borderRadius: 8, color: "var(--color-resolved)", background: "color-mix(in oklch, var(--color-resolved) 8%, transparent)" }}>
          <CheckCircle2 size={14} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>{statusMessage}</span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(320px, 420px) minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
        <div className="card">
          <div className="card-header">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Upload size={16} style={{ color: "var(--color-primary)" }} />
              <span style={{ fontWeight: 700 }}>Guideline Upload</span>
            </div>
          </div>
          <div className="card-body" style={{ display: "grid", gap: 12 }}>
            <div>
              <label className="form-label">File</label>
              <input
                className="form-input"
                type="file"
                accept=".pdf,.doc,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                style={{ height: 38, paddingTop: 7 }}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 12 }}>
              <div>
                <label className="form-label">Regulator</label>
                <select className="form-select" value={regulator} onChange={(e) => setRegulator(e.target.value as ComplianceRegulator)}>
                  {REGULATORS.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>
              <div>
                <label className="form-label">Version</label>
                <input className="form-input" value={version} onChange={(e) => setVersion(e.target.value)} placeholder="2026.1" />
              </div>
            </div>
            <div>
              <label className="form-label">Document Title</label>
              <input className="form-input" value={documentTitle} onChange={(e) => setDocumentTitle(e.target.value)} placeholder="RBI Master Direction" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label className="form-label">Effective From</label>
                <input className="form-input" type="datetime-local" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
              </div>
              <div>
                <label className="form-label">Effective To</label>
                <input className="form-input" type="datetime-local" value={effectiveTo} onChange={(e) => setEffectiveTo(e.target.value)} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleUpload} disabled={!canUpload}>
              {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
              Upload Document
            </button>
          </div>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <FileText size={16} style={{ color: "var(--color-primary)" }} />
                <span style={{ fontWeight: 700 }}>Processing</span>
              </div>
              {document && <span style={{ fontSize: 12, color: "var(--color-on-surface-variant)", fontWeight: 700 }}>{document.status}</span>}
            </div>
            <div className="card-body" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto auto", gap: 12, alignItems: "center" }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {document?.document_title ?? "No document uploaded yet"}
                </p>
                <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", marginTop: 3 }}>
                  {document ? document.source_filename + " / " + document.version : "Upload a guideline to enable processing and embedding."}
                </p>
              </div>
              <button className="btn-secondary" onClick={handleProcess} disabled={!document || processing}>
                {processing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                Process
              </button>
              <button className="btn-secondary" onClick={handleEmbed} disabled={!document || embedding}>
                {embedding ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                Backfill
              </button>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Search size={16} style={{ color: "var(--color-primary)" }} />
                <span style={{ fontWeight: 700 }}>Retrieval Test</span>
              </div>
            </div>
            <div className="card-body" style={{ display: "grid", gap: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 10 }}>
                <input
                  className="form-input"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") void handleSearch(); }}
                  placeholder="Search RBI complaint handling guidance"
                />
                <button className="btn-primary" onClick={handleSearch} disabled={!query.trim() || searching}>
                  {searching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                  Search
                </button>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                {results.map((result) => (
                  <div key={result.chunk_id} className="stat-card" style={{ gap: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                      <div style={{ minWidth: 0 }}>
                        <p style={{ fontWeight: 700, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {result.document_title ?? "Untitled regulatory document"}
                        </p>
                        <p style={{ color: "var(--color-on-surface-variant)", fontSize: 12, marginTop: 2 }}>
                          {result.section_reference ?? "Unsectioned"} / pages {formatPageRange(result.page_start, result.page_end)}
                        </p>
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 800, color: "var(--color-primary)" }}>
                        {(result.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p style={{ color: "var(--color-on-surface)", fontSize: 13, lineHeight: 1.55 }}>
                      {truncateText(result.chunk_text, 420)}
                    </p>
                  </div>
                ))}
                {!searching && results.length === 0 && (
                  <div style={{ color: "var(--color-on-surface-variant)", fontSize: 13, padding: "8px 0" }}>
                    Run a search after processing and embedding a guideline.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatPageRange(start: number | null, end: number | null): string {
  if (start == null && end == null) return "-";
  if (start === end || end == null) return String(start ?? end);
  return String(start) + "-" + String(end);
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return value.slice(0, maxLength - 3) + "...";
}
