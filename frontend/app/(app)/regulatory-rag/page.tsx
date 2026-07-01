"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  DatabaseZap,
  Eye,
  FileSearch,
  FileText,
  Filter,
  Loader2,
  Lock,
  Play,
  RefreshCw,
  Search,
  Upload,
  Zap,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  embedRegulatoryDocumentChunks,
  listRegulatoryDocumentChunks,
  listRegulatoryDocuments,
  processRegulatoryDocument,
  reviewRegulatoryDocument,
  searchRegulatoryKnowledge,
  uploadRegulatoryDocument,
} from "@/lib/api/regulatoryRag";
import type {
  ComplianceRegulator,
  RegulatoryDocumentRead,
  RegulatoryDocumentStatus,
  RegulatoryKnowledgeChunkRead,
  RegulatoryKnowledgeSearchResult,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { formatDateTime, humanize, type BadgeVariant } from "@/lib/utils/format";

const REGULATORS: ComplianceRegulator[] = ["RBI", "NPCI", "SEBI", "IRDAI", "BANK_INTERNAL"];
const DOC_STATUSES: RegulatoryDocumentStatus[] = ["uploaded", "processing", "indexed", "review_required", "active", "archived", "failed"];
const CHUNK_STATUSES = ["draft", "active", "archived"] as const;

export default function RegulatoryRagPage() {
  const { user, isLoading } = useAuth();
  const [documents, setDocuments] = useState<RegulatoryDocumentRead[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [docRegulator, setDocRegulator] = useState<ComplianceRegulator | "">("");
  const [docStatus, setDocStatus] = useState<RegulatoryDocumentStatus | "">("");
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [regulator, setRegulator] = useState<ComplianceRegulator | "">("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [version, setVersion] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [embedding, setEmbedding] = useState(false);
  const [embeddingLimit, setEmbeddingLimit] = useState(100);
  const [chunks, setChunks] = useState<RegulatoryKnowledgeChunkRead[]>([]);
  const [chunkCount, setChunkCount] = useState(0);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [reviewNotes, setReviewNotes] = useState("");

  const [searching, setSearching] = useState(false);
  const [query, setQuery] = useState("");
  const [searchRegulator, setSearchRegulator] = useState<ComplianceRegulator | "">("");
  const [domain, setDomain] = useState("");
  const [chunkStatus, setChunkStatus] = useState<(typeof CHUNK_STATUSES)[number] | "">("");
  const [resultLimit, setResultLimit] = useState(8);
  const [minSimilarity, setMinSimilarity] = useState(0);
  const [results, setResults] = useState<RegulatoryKnowledgeSearchResult[]>([]);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((doc) => doc.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId]
  );

  const reloadChunks = useCallback(async () => {
    if (!selectedDocumentId) {
      setChunks([]);
      setChunkCount(0);
      return;
    }
    setLoadingChunks(true);
    try {
      const response = await listRegulatoryDocumentChunks(selectedDocumentId, { limit: 12, offset: 0 });
      setChunks(response.items);
      setChunkCount(response.count);
    } catch {
      setChunks([]);
      setChunkCount(0);
    } finally {
      setLoadingChunks(false);
    }
  }, [selectedDocumentId]);

  const reloadDocuments = useCallback(async (soft = false) => {
    if (soft) setRefreshing(true); else setLoadingDocs(true);
    setError(null);
    try {
      const response = await listRegulatoryDocuments({
        limit: 100,
        regulator: docRegulator,
        status: docStatus,
      });
      setDocuments(response.items);
      setSelectedDocumentId((current) => {
        if (current && response.items.some((doc) => doc.id === current)) return current;
        return response.items[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load regulatory documents");
    } finally {
      setLoadingDocs(false);
      setRefreshing(false);
    }
  }, [docRegulator, docStatus]);

  useEffect(() => { void reloadDocuments(); }, [reloadDocuments]);
  useEffect(() => { void reloadChunks(); }, [reloadChunks]);

  const canAdmin = user?.role === "admin" || user?.role === "super_admin";
  const canUpload = Boolean(file && regulator && documentTitle.trim() && version.trim() && !uploading);
  const workflowStep = selectedDocument ? statusToStep(selectedDocument.status) : 0;

  if (isLoading) return <LoadingSpinner fullPage label="Loading regulatory workspace..." />;

  if (!canAdmin) {
    return (
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div className="card"><div className="card-body" style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Lock size={22} style={{ color: "var(--color-error)" }} />
          <div><h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>403 Unauthorized</h1><p style={{ color: "var(--color-on-surface-variant)", fontSize: 13 }}>Regulatory RAG administration is available only to admin and super admin users.</p></div>
        </div></div>
      </div>
    );
  }

  async function handleUpload() {
    if (!file || !documentTitle.trim() || !version.trim()) return;
    setUploading(true); setError(null); setStatusMessage(null);
    try {
      const uploaded = await uploadRegulatoryDocument({
        file,
        regulator: regulator as ComplianceRegulator,
        documentTitle: documentTitle.trim(),
        version: version.trim(),
        effectiveFrom: toApiDate(effectiveFrom),
        effectiveTo: toApiDate(effectiveTo),
      });
      setFile(null); setDocumentTitle(""); setVersion(""); setEffectiveFrom(""); setEffectiveTo("");
      setStatusMessage(`Uploaded ${uploaded.document_title}.`);
      await reloadDocuments(true);
      setSelectedDocumentId(uploaded.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally { setUploading(false); }
  }

  async function handleProcess() {
    if (!selectedDocument) return;
    setProcessing(true); setError(null); setStatusMessage(null);
    try {
      const processed = await processRegulatoryDocument(selectedDocument.id);
      setStatusMessage(`Processed ${processed.pages_created} page(s) and ${processed.chunks_created} chunk(s).`);
      await reloadDocuments(true);
      setSelectedDocumentId(processed.document.id);
      await reloadChunks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Processing failed");
    } finally { setProcessing(false); }
  }

  async function handleEmbed() {
    if (!selectedDocument) return;
    setEmbedding(true); setError(null); setStatusMessage(null);
    try {
      const result = await embedRegulatoryDocumentChunks(selectedDocument.id, embeddingLimit);
      setStatusMessage(`Embedded ${result.embedded_count} chunk(s); skipped ${result.skipped_count}. Model: ${result.embedding_model}`);
      await reloadDocuments(true);
      await reloadChunks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Embedding backfill failed");
    } finally { setEmbedding(false); }
  }


  async function handleReview(action: "activate" | "request_changes" | "archive") {
    if (!selectedDocument) return;
    setReviewing(true); setError(null); setStatusMessage(null);
    try {
      const result = await reviewRegulatoryDocument(selectedDocument.id, { action, notes: reviewNotes });
      setStatusMessage(
        action === "activate"
          ? `Activated ${result.chunks_updated} reviewed chunk(s) for RAG.`
          : action === "request_changes"
            ? `Marked ${result.chunks_updated} chunk(s) for changes.`
            : `Archived ${result.chunks_updated} chunk(s).`
      );
      setReviewNotes("");
      await reloadDocuments(true);
      setSelectedDocumentId(result.document.id);
      await reloadChunks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review action failed");
    } finally { setReviewing(false); }
  }
  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true); setError(null); setStatusMessage(null);
    try {
      const response = await searchRegulatoryKnowledge({
        query: query.trim(),
        regulator: searchRegulator,
        domain,
        status: chunkStatus,
        limit: resultLimit,
        minSimilarity,
      });
      setResults(response.results);
      setStatusMessage(`Found ${response.results.length} regulatory chunk(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally { setSearching(false); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Regulatory RAG</h1>
          <p className="page-subtitle">Upload policy documents, process them into knowledge chunks, backfill embeddings, and validate retrieval quality.</p>
        </div>
        <button className="btn-secondary" onClick={() => reloadDocuments(true)} disabled={refreshing}>{refreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}Refresh</button>
      </div>

      {error && <div className="alert-error"><AlertTriangle size={14} />{error}</div>}
      {statusMessage && <div className="alert-success"><CheckCircle2 size={14} />{statusMessage}</div>}

      <Workflow step={workflowStep} />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, 390px) minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
        <div style={{ display: "grid", gap: 16 }}>
          <UploadPanel
            file={file}
            setFile={setFile}
            regulator={regulator}
            setRegulator={setRegulator}
            documentTitle={documentTitle}
            setDocumentTitle={setDocumentTitle}
            version={version}
            setVersion={setVersion}
            effectiveFrom={effectiveFrom}
            setEffectiveFrom={setEffectiveFrom}
            effectiveTo={effectiveTo}
            setEffectiveTo={setEffectiveTo}
            uploading={uploading}
            canUpload={canUpload}
            onUpload={handleUpload}
          />
          <DocumentLibrary
            documents={documents}
            selectedId={selectedDocumentId}
            onSelect={setSelectedDocumentId}
            regulator={docRegulator}
            setRegulator={setDocRegulator}
            status={docStatus}
            setStatus={setDocStatus}
            loading={loadingDocs}
          />
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <ProcessingPanel
            document={selectedDocument}
            processing={processing}
            embedding={embedding}
            embeddingLimit={embeddingLimit}
            setEmbeddingLimit={setEmbeddingLimit}
            onProcess={handleProcess}
            onEmbed={handleEmbed}
          />
          <ReviewPanel
            document={selectedDocument}
            chunks={chunks}
            chunkCount={chunkCount}
            loading={loadingChunks}
            reviewing={reviewing}
            notes={reviewNotes}
            setNotes={setReviewNotes}
            onRefresh={reloadChunks}
            onReview={handleReview}
          />
          <SearchPanel
            query={query}
            setQuery={setQuery}
            regulator={searchRegulator}
            setRegulator={setSearchRegulator}
            domain={domain}
            setDomain={setDomain}
            status={chunkStatus}
            setStatus={setChunkStatus}
            limit={resultLimit}
            setLimit={setResultLimit}
            minSimilarity={minSimilarity}
            setMinSimilarity={setMinSimilarity}
            searching={searching}
            results={results}
            onSearch={handleSearch}
          />
        </div>
      </div>
    </div>
  );
}

function UploadPanel(props: {
  file: File | null; setFile: (file: File | null) => void; regulator: ComplianceRegulator | ""; setRegulator: (value: ComplianceRegulator | "") => void; documentTitle: string; setDocumentTitle: (value: string) => void; version: string; setVersion: (value: string) => void; effectiveFrom: string; setEffectiveFrom: (value: string) => void; effectiveTo: string; setEffectiveTo: (value: string) => void; uploading: boolean; canUpload: boolean; onUpload: () => void;
}) {
  return <div className="card"><div className="card-header"><div style={{ display: "flex", alignItems: "center", gap: 8 }}><Upload size={16} /><strong>Guideline Upload</strong></div></div><div className="card-body" style={{ display: "grid", gap: 12 }}>
    <label className="form-label">File</label>
    <label style={{ border: "1px dashed var(--color-outline)", borderRadius: 8, padding: 14, background: "var(--color-surface-container-low)", cursor: "pointer" }}>
      <input type="file" accept=".pdf,.doc,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown" onChange={(event) => props.setFile(event.target.files?.[0] ?? null)} style={{ display: "none" }} />
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}><FileText size={18} /><div><strong style={{ fontSize: 13 }}>{props.file?.name ?? "Choose a PDF, DOCX, TXT, or Markdown file"}</strong><p style={{ fontSize: 12, color: "var(--color-on-surface-variant)" }}>{props.file ? `${Math.ceil(props.file.size / 1024)} KB selected` : "The backend will store, convert, chunk, and index it."}</p></div></div>
    </label>
    <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 12 }}><Field label="Regulator"><select className="form-select" value={props.regulator} onChange={(e) => props.setRegulator(e.target.value as ComplianceRegulator | "")}><option value="">Select regulator</option>{REGULATORS.map((item) => <option key={item} value={item}>{item}</option>)}</select></Field><Field label="Version"><input className="form-input" value={props.version} onChange={(e) => props.setVersion(e.target.value)} placeholder="Enter version" /></Field></div>
    <Field label="Document Title"><input className="form-input" value={props.documentTitle} onChange={(e) => props.setDocumentTitle(e.target.value)} placeholder="Enter document title" /></Field>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}><Field label="Effective From"><input className="form-input" type="datetime-local" value={props.effectiveFrom} onChange={(e) => props.setEffectiveFrom(e.target.value)} /></Field><Field label="Effective To"><input className="form-input" type="datetime-local" value={props.effectiveTo} onChange={(e) => props.setEffectiveTo(e.target.value)} /></Field></div>
    <button className="btn-primary" onClick={props.onUpload} disabled={!props.canUpload}>{props.uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}Upload Document</button>
  </div></div>;
}

function DocumentLibrary({ documents, selectedId, onSelect, regulator, setRegulator, status, setStatus, loading }: { documents: RegulatoryDocumentRead[]; selectedId: string | null; onSelect: (id: string) => void; regulator: ComplianceRegulator | ""; setRegulator: (value: ComplianceRegulator | "") => void; status: RegulatoryDocumentStatus | ""; setStatus: (value: RegulatoryDocumentStatus | "") => void; loading: boolean }) {
  return <div className="card"><div className="card-header" style={{ gap: 8, flexWrap: "wrap" }}><div style={{ display: "flex", alignItems: "center", gap: 8 }}><BookOpen size={16} /><strong>Document Library</strong><Badge>{documents.length}</Badge></div><Filter size={14} /></div><div className="card-body" style={{ display: "grid", gap: 10 }}><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}><select className="form-select" value={regulator} onChange={(e) => setRegulator(e.target.value as ComplianceRegulator | "")}><option value="">All regulators</option>{REGULATORS.map((item) => <option key={item} value={item}>{item}</option>)}</select><select className="form-select" value={status} onChange={(e) => setStatus(e.target.value as RegulatoryDocumentStatus | "")}><option value="">All status</option>{DOC_STATUSES.map((item) => <option key={item} value={item}>{humanize(item)}</option>)}</select></div>{loading ? <LoadingSpinner label="Loading documents..." /> : documents.length ? <div style={{ display: "grid", gap: 8, maxHeight: 390, overflowY: "auto" }}>{documents.map((doc) => <button key={doc.id} onClick={() => onSelect(doc.id)} className={selectedId === doc.id ? "stat-card selected" : "stat-card"} style={{ textAlign: "left", borderColor: selectedId === doc.id ? "var(--color-primary)" : undefined }}><div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><strong style={{ fontSize: 13 }}>{doc.document_title}</strong><Badge variant={statusVariant(doc.status)}>{humanize(doc.status)}</Badge></div><p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", marginTop: 3 }}>{doc.regulator} / {doc.document_type.toUpperCase()} / v{doc.version}</p><p style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginTop: 3 }}>{formatDateTime(doc.uploaded_at)}</p></button>)}</div> : <EmptyState title="No regulatory documents" description="Upload a document or clear the filters." icon={<FileText size={28} />} />}</div></div>;
}

function ProcessingPanel({ document, processing, embedding, embeddingLimit, setEmbeddingLimit, onProcess, onEmbed }: { document: RegulatoryDocumentRead | null; processing: boolean; embedding: boolean; embeddingLimit: number; setEmbeddingLimit: (value: number) => void; onProcess: () => void; onEmbed: () => void }) {
  return <div className="card"><div className="card-header"><div style={{ display: "flex", alignItems: "center", gap: 8 }}><DatabaseZap size={16} /><strong>Processing Pipeline</strong></div>{document && <Badge variant={statusVariant(document.status)}>{humanize(document.status)}</Badge>}</div><div className="card-body" style={{ display: "grid", gap: 14 }}>{document ? <><div><h2 style={{ fontSize: 16, fontWeight: 800 }}>{document.document_title}</h2><p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", marginTop: 4 }}>{document.source_filename} / uploaded by {document.uploaded_by ?? "unknown"}</p></div><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}><Info label="Regulator" value={document.regulator} /><Info label="Version" value={document.version} /><Info label="Effective From" value={formatDateTime(document.effective_from)} /><Info label="Updated" value={formatDateTime(document.updated_at)} /></div><div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}><button className="btn-primary" onClick={onProcess} disabled={processing}>{processing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}Process / Reprocess</button><select className="form-select" value={embeddingLimit} onChange={(e) => setEmbeddingLimit(Number(e.target.value))} style={{ width: 120 }}>{[50, 100, 250, 500].map((value) => <option key={value} value={value}>{value} chunks</option>)}</select><button className="btn-secondary" onClick={onEmbed} disabled={embedding}>{embedding ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}Backfill Embeddings</button></div></> : <EmptyState title="Select a document" description="Choose a document from the library or upload a new guideline to start processing." icon={<FileSearch size={28} />} />}</div></div>;
}

function ReviewPanel({ document, chunks, chunkCount, loading, reviewing, notes, setNotes, onRefresh, onReview }: { document: RegulatoryDocumentRead | null; chunks: RegulatoryKnowledgeChunkRead[]; chunkCount: number; loading: boolean; reviewing: boolean; notes: string; setNotes: (value: string) => void; onRefresh: () => void; onReview: (action: "activate" | "request_changes" | "archive") => void }) {
  const draftCount = chunks.filter((chunk) => chunk.status === "draft").length;
  const activeCount = chunks.filter((chunk) => chunk.status === "active").length;
  const embeddedCount = chunks.filter((chunk) => Boolean(chunk.embedding_model)).length;
  const pageCoverage = chunks.length
    ? `${Math.min(...chunks.map((chunk) => chunk.page_start ?? chunk.page_end ?? 0).filter(Boolean)) || "-"}-${Math.max(...chunks.map((chunk) => chunk.page_end ?? chunk.page_start ?? 0).filter(Boolean)) || "-"}`
    : "-";
  const canReview = Boolean(document && chunkCount > 0 && !reviewing);

  return <div className="card"><div className="card-header"><div style={{ display: "flex", alignItems: "center", gap: 8 }}><Eye size={16} /><strong>Human Review & Activation</strong></div>{document && <Badge variant={statusVariant(document.status)}>{humanize(document.status)}</Badge>}</div><div className="card-body" style={{ display: "grid", gap: 14 }}>{!document ? <EmptyState title="Select a document to review" description="After processing, extracted chunks will appear here for human approval before they are activated for RAG." icon={<Eye size={28} />} /> : document.status === "uploaded" ? <EmptyState title="Process this document first" description="Click Process / Reprocess to convert the guideline into page-aware chunks, then review and activate them here." icon={<FileSearch size={28} />} /> : <><div style={{ border: "1px solid var(--color-outline-variant)", borderRadius: 8, padding: 12, background: "var(--color-surface-container-low)", display: "grid", gap: 6 }}><strong style={{ fontSize: 13 }}>Review gate before knowledge base use</strong><p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", lineHeight: 1.5 }}>Draft chunks are preview-only. When you approve them, the document and its chunks become active, so semantic search and complaint compliance explanations can cite this guideline.</p></div><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}><Info label="Total Chunks" value={String(chunkCount)} /><Info label="Draft Preview" value={String(draftCount)} /><Info label="Active Preview" value={String(activeCount)} /><Info label="Embedded Here" value={String(embeddedCount)} /><Info label="Preview Pages" value={pageCoverage} /></div><Field label="Review Notes"><textarea className="form-input" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add reviewer notes, missing sections, or approval reason" rows={3} style={{ resize: "vertical" }} /></Field><div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}><button className="btn-secondary" onClick={onRefresh} disabled={loading}>{loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}Refresh Preview</button><button className="btn-secondary" onClick={() => onReview("request_changes")} disabled={!canReview}>Request Changes</button><button className="btn-secondary" onClick={() => onReview("archive")} disabled={!canReview}>Archive</button><button className="btn-primary" onClick={() => onReview("activate")} disabled={!canReview}>{reviewing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}Activate for RAG</button></div><div style={{ display: "grid", gap: 10 }}>{loading ? <LoadingSpinner label="Loading chunk preview..." /> : chunks.length ? chunks.map((chunk) => <div key={chunk.id} className="stat-card" style={{ gap: 8 }}><div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}><div style={{ minWidth: 0 }}><p style={{ fontWeight: 800, fontSize: 13 }}>Chunk {chunk.chunk_index + 1} / pages {formatPageRange(chunk.page_start, chunk.page_end)}</p><p style={{ color: "var(--color-on-surface-variant)", fontSize: 12, marginTop: 2 }}>{chunk.domain ?? "General"} / {chunk.section_reference ?? "Unsectioned"}</p></div><div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}><Badge variant={statusVariant(chunk.status)}>{humanize(chunk.status)}</Badge><Badge variant={chunk.embedding_model ? "success" : "warning"}>{chunk.embedding_model ? "Embedded" : "Needs Embedding"}</Badge></div></div><p style={{ color: "var(--color-on-surface)", fontSize: 13, lineHeight: 1.55 }}>{truncateText(chunk.chunk_text, 620)}</p>{chunk.keywords.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{chunk.keywords.slice(0, 10).map((keyword) => <span key={keyword} className="id-pill">{keyword}</span>)}</div>}</div>) : <EmptyState title="No chunks found" description="Run Process / Reprocess. If it already ran, refresh the preview to load the extracted chunks." icon={<FileText size={28} />} />}{chunkCount > chunks.length && <p style={{ fontSize: 12, color: "var(--color-on-surface-variant)", textAlign: "center" }}>Showing first {chunks.length} of {chunkCount} chunks for review.</p>}</div></>}</div></div>;
}
function SearchPanel(props: { query: string; setQuery: (value: string) => void; regulator: ComplianceRegulator | ""; setRegulator: (value: ComplianceRegulator | "") => void; domain: string; setDomain: (value: string) => void; status: "draft" | "active" | "archived" | ""; setStatus: (value: "draft" | "active" | "archived" | "") => void; limit: number; setLimit: (value: number) => void; minSimilarity: number; setMinSimilarity: (value: number) => void; searching: boolean; results: RegulatoryKnowledgeSearchResult[]; onSearch: () => void }) {
  return <div className="card"><div className="card-header"><div style={{ display: "flex", alignItems: "center", gap: 8 }}><Search size={16} /><strong>Retrieval Test</strong></div></div><div className="card-body" style={{ display: "grid", gap: 12 }}><div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 10 }}><input className="form-input" value={props.query} onChange={(e) => props.setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void props.onSearch(); }} placeholder="Enter regulatory search query" /><button className="btn-primary" onClick={props.onSearch} disabled={!props.query.trim() || props.searching}>{props.searching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}Search</button></div><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 8 }}><select className="form-select" value={props.regulator} onChange={(e) => props.setRegulator(e.target.value as ComplianceRegulator | "")}><option value="">All regulators</option>{REGULATORS.map((item) => <option key={item} value={item}>{item}</option>)}</select><input className="form-input" value={props.domain} onChange={(e) => props.setDomain(e.target.value)} placeholder="Domain filter" /><select className="form-select" value={props.status} onChange={(e) => props.setStatus(e.target.value as "draft" | "active" | "archived" | "")}><option value="">Any chunk status</option>{CHUNK_STATUSES.map((item) => <option key={item} value={item}>{humanize(item)}</option>)}</select><select className="form-select" value={props.limit} onChange={(e) => props.setLimit(Number(e.target.value))}>{[5, 8, 12, 20].map((value) => <option key={value} value={value}>{value} results</option>)}</select></div><label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: "var(--color-on-surface-variant)", fontWeight: 700 }}>Min similarity {Math.round(props.minSimilarity * 100)}%<input type="range" min={0} max={0.9} step={0.05} value={props.minSimilarity} onChange={(e) => props.setMinSimilarity(Number(e.target.value))} style={{ width: 180 }} /></label><div style={{ display: "grid", gap: 10 }}>{props.results.map((result) => <div key={result.chunk_id} className="stat-card" style={{ gap: 8 }}><div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}><div style={{ minWidth: 0 }}><p style={{ fontWeight: 700, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{result.document_title ?? "Untitled regulatory document"}</p><p style={{ color: "var(--color-on-surface-variant)", fontSize: 12, marginTop: 2 }}>{result.regulator} / {result.domain} / {result.section_reference ?? "Unsectioned"} / pages {formatPageRange(result.page_start, result.page_end)}</p></div><Badge variant={result.similarity_score >= 0.75 ? "success" : result.similarity_score >= 0.5 ? "warning" : "neutral"}>{(result.similarity_score * 100).toFixed(1)}%</Badge></div><p style={{ color: "var(--color-on-surface)", fontSize: 13, lineHeight: 1.55 }}>{truncateText(result.chunk_text, 520)}</p>{result.keywords.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{result.keywords.slice(0, 8).map((keyword) => <span key={keyword} className="id-pill">{keyword}</span>)}</div>}</div>)}{!props.searching && props.results.length === 0 && <EmptyState title="No retrieval results yet" description="Process and embed a document, then run a semantic search." icon={<Search size={28} />} />}</div></div></div>;
}

function Workflow({ step }: { step: number }) {
  const items = ["Upload", "Process", "Embed", "Search"];
  return <div className="card"><div className="card-body" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>{items.map((item, index) => <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, color: index <= step ? "var(--color-primary)" : "var(--color-on-surface-variant)", fontWeight: 700, fontSize: 12 }}><span style={{ width: 22, height: 22, borderRadius: 999, display: "inline-flex", alignItems: "center", justifyContent: "center", background: index <= step ? "var(--color-primary)" : "var(--color-surface-container)", color: index <= step ? "var(--color-on-primary)" : "var(--color-on-surface-variant)" }}>{index + 1}</span>{item}</div>)}</div></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label><span className="form-label">{label}</span>{children}</label>; }
function Info({ label, value }: { label: string; value: string }) { return <div className="stat-card"><span style={{ color: "var(--color-on-surface-variant)", fontSize: 12 }}>{label}</span><strong style={{ fontSize: 13 }}>{value || "-"}</strong></div>; }
function formatPageRange(start: number | null, end: number | null): string { if (start == null && end == null) return "-"; if (start === end || end == null) return String(start ?? end); return `${start}-${end}`; }
function truncateText(value: string, maxLength: number): string { return value.length <= maxLength ? value : `${value.slice(0, maxLength - 3)}...`; }
function statusToStep(status: RegulatoryDocumentStatus): number { if (status === "uploaded") return 0; if (status === "processing") return 1; if (status === "indexed" || status === "review_required") return 2; if (status === "active" || status === "archived") return 3; return 0; }
function statusVariant(status: string): BadgeVariant { if (status === "active" || status === "indexed") return "success"; if (status === "processing" || status === "review_required" || status === "uploaded") return "warning"; if (status === "failed") return "danger"; return "neutral"; }
function toApiDate(value: string): string | undefined { return value ? new Date(value).toISOString() : undefined; }







