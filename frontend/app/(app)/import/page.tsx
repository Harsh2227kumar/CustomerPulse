"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Database,
  Eye,
  Loader2,
  XCircle,
} from "lucide-react";
import { getS3ImportOptions, importS3Complaints, previewS3Import } from "@/lib/api/ingestion";
import type {
  S3ImportFilters,
  S3ImportOptionsResponse,
  S3ImportPreviewResponse,
  S3ImportResponse,
} from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { formatDate, truncate } from "@/lib/utils/format";

type Step = "options" | "preview" | "result";

const EMPTY_FILTERS: S3ImportFilters = {
  product: null, sub_product: null, issue: null, company: null,
  channel: null, timely_response: null,
  date_received_min: null, date_received_max: null,
  max_records: 50,
};

export default function ImportPage() {
  const [step, setStep] = useState<Step>("options");
  const [optionsData, setOptionsData] = useState<S3ImportOptionsResponse | null>(null);
  const [previewData, setPreviewData] = useState<S3ImportPreviewResponse | null>(null);
  const [resultData, setResultData] = useState<S3ImportResponse | null>(null);
  const [filters, setFilters] = useState<S3ImportFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load import options on mount
  useEffect(() => {
    setLoading(true);
    getS3ImportOptions()
      .then((data) => { setOptionsData(data); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load import options"))
      .finally(() => setLoading(false));
  }, []);

  function setFilter<K extends keyof S3ImportFilters>(key: K, val: S3ImportFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: val }));
  }

  async function handlePreview() {
    setActionLoading(true); setError(null);
    try {
      const preview = await previewS3Import(filters);
      setPreviewData(preview);
      setStep("preview");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to preview"); }
    finally { setActionLoading(false); }
  }

  async function handleImport() {
    if (!previewData) return;
    setActionLoading(true); setError(null);
    try {
      const result = await importS3Complaints(filters);
      setResultData(result);
      setStep("result");
    } catch (e) { setError(e instanceof Error ? e.message : "Import failed"); }
    finally { setActionLoading(false); }
  }

  function resetWizard() {
    setStep("options");
    setFilters(EMPTY_FILTERS);
    setPreviewData(null);
    setResultData(null);
    setError(null);
  }

  if (loading) return <LoadingSpinner fullPage label="Loading import options…" />;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Data Import</h1>
          <p className="page-subtitle">Import complaint data from the configured S3/Athena data source.</p>
        </div>
      </div>

      {/* Step indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
        {(["options", "preview", "result"] as Step[]).map((s, i) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: step === s ? "var(--color-primary)" : (["preview", "result"].includes(step) && i === 0) || (step === "result" && i === 1) ? "var(--color-resolved)" : "var(--color-surface-container)",
              color: step === s || (["preview", "result"].includes(step) && i === 0) || (step === "result" && i === 1) ? "white" : "var(--color-on-surface-variant)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, fontWeight: 700, transition: "all 0.2s",
            }}>
              {(["preview", "result"].includes(step) && i === 0) || (step === "result" && i === 1) ? "✓" : i + 1}
            </div>
            <span style={{ fontSize: "var(--text-body-sm)", fontWeight: step === s ? 600 : 400, color: step === s ? "var(--color-primary)" : "var(--color-on-surface-variant)" }}>
              {s === "options" ? "Configure" : s === "preview" ? "Preview" : "Complete"}
            </span>
            {i < 2 && <div style={{ width: 40, height: 1, background: "var(--color-outline-variant)" }} />}
          </div>
        ))}
      </div>

      {error && (
        <div className="alert-error" style={{ marginBottom: 16 }}>
          <AlertTriangle size={14} />{error}
        </div>
      )}

      {/* ── Step 1: Configure ─────────────────────────────────────────────── */}
      {step === "options" && optionsData && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Source status */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Database size={18} style={{ color: "var(--color-primary)" }} />
                <span style={{ fontWeight: 600 }}>Data Source</span>
              </div>
              <Badge variant={optionsData.available ? "success" : "danger"}>
                {optionsData.available ? "Available" : "Unavailable"}
              </Badge>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <div className="info-row"><span className="info-label">Source</span><span className="info-value">{optionsData.source.label}</span></div>
              <div className="info-row"><span className="info-label">Query Mode</span><span className="info-value">{optionsData.query_mode.toUpperCase()}</span></div>
              {optionsData.scanned_rows != null && <div className="info-row"><span className="info-label">Scanned Rows</span><span className="info-value">{optionsData.scanned_rows.toLocaleString()}</span></div>}
              {optionsData.eligible_rows != null && <div className="info-row"><span className="info-label">Eligible Rows</span><span className="info-value">{optionsData.eligible_rows.toLocaleString()}</span></div>}
              {!optionsData.available && optionsData.unavailable_reason && (
                <div className="alert-error" style={{ marginTop: 8 }}>
                  <AlertTriangle size={13} />{optionsData.unavailable_reason}
                </div>
              )}
            </div>
          </div>

          {/* Filters */}
          {optionsData.available && (
            <div className="card">
              <div className="card-header"><span style={{ fontWeight: 600 }}>Filter & Select Data</span></div>
              <div style={{ padding: "16px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
                  {/* Product */}
                  <div>
                    <label className="form-label">Product</label>
                    <select className="form-select" value={filters.product ?? ""} onChange={(e) => setFilter("product", e.target.value || null)}>
                      <option value="">All products</option>
                      {optionsData.products.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>

                  {/* Channel */}
                  <div>
                    <label className="form-label">Channel</label>
                    <select className="form-select" value={filters.channel ?? ""} onChange={(e) => setFilter("channel", e.target.value || null)}>
                      <option value="">All channels</option>
                      {optionsData.channels.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>

                  {/* Company */}
                  <div>
                    <label className="form-label">Company</label>
                    <select className="form-select" value={filters.company ?? ""} onChange={(e) => setFilter("company", e.target.value || null)}>
                      <option value="">All companies</option>
                      {optionsData.companies.slice(0, 50).map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>

                  {/* Issue */}
                  <div>
                    <label className="form-label">Issue</label>
                    <select className="form-select" value={filters.issue ?? ""} onChange={(e) => setFilter("issue", e.target.value || null)}>
                      <option value="">All issues</option>
                      {optionsData.issues.map((i) => <option key={i} value={i}>{i}</option>)}
                    </select>
                  </div>

                  {/* Timely response */}
                  <div>
                    <label className="form-label">Timely Response</label>
                    <select className="form-select" value={filters.timely_response == null ? "" : String(filters.timely_response)} onChange={(e) => setFilter("timely_response", e.target.value === "" ? null : e.target.value === "true")}>
                      <option value="">All</option>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </div>

                  {/* Max records */}
                  <div>
                    <label className="form-label">Max Records</label>
                    <input
                      type="number" min={1} max={5000}
                      className="form-input"
                      value={filters.max_records}
                      onChange={(e) => setFilter("max_records", parseInt(e.target.value) || 100)}
                    />
                  </div>

                  {/* Date range */}
                  <div>
                    <label className="form-label">Date Received (From)</label>
                    <input type="date" className="form-input" value={filters.date_received_min ?? ""}
                      onChange={(e) => setFilter("date_received_min", e.target.value || null)} />
                  </div>
                  <div>
                    <label className="form-label">Date Received (To)</label>
                    <input type="date" className="form-input" value={filters.date_received_max ?? ""}
                      onChange={(e) => setFilter("date_received_max", e.target.value || null)} />
                  </div>
                </div>
              </div>
              <div style={{ padding: "12px 16px", borderTop: "1px solid var(--color-outline-variant)", display: "flex", justifyContent: "flex-end" }}>
                <button className="btn-primary" onClick={handlePreview} disabled={actionLoading}>
                  {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
                  Preview Import
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Step 2: Preview ───────────────────────────────────────────────── */}
      {step === "preview" && previewData && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Preview stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {[
              { label: "Scanned", value: previewData.scanned_rows.toLocaleString() },
              { label: "Matched", value: previewData.matched_rows.toLocaleString() },
              { label: "Selected", value: previewData.selected_rows.toLocaleString() },
              { label: "Limited", value: previewData.result_limited ? "Yes" : "No", color: previewData.result_limited ? "var(--color-pending)" : undefined },
            ].map(({ label, value, color }) => (
              <div key={label} className="stat-card">
                <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-on-surface-variant)", fontWeight: 600 }}>{label}</span>
                <span style={{ fontSize: 22, fontWeight: 700, color: color ?? "var(--color-on-background)" }}>{value}</span>
              </div>
            ))}
          </div>

          {previewData.result_limited && (
            <div className="alert-warning">
              <AlertTriangle size={13} />
              Results were limited to {filters.max_records} records. Increase max records to import more.
            </div>
          )}

          {/* Preview table */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontWeight: 600 }}>Preview ({previewData.items.length} records)</span>
              <Badge variant="neutral">{previewData.source.label}</Badge>
            </div>
            <div style={{ overflowX: "auto", maxHeight: 400, overflowY: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr><th>Complaint ID</th><th>Product</th><th>Issue</th><th>Company</th><th>Channel</th><th>Date</th><th>Narrative</th></tr>
                </thead>
                <tbody>
                  {previewData.items.map((item) => (
                    <tr key={item.complaint_id}>
                      <td><span className="id-pill">{item.complaint_id.slice(0, 12)}…</span></td>
                      <td style={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.product ?? "—"}</td>
                      <td style={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.issue ?? "—"}</td>
                      <td style={{ maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.company ?? "—"}</td>
                      <td>{item.channel ?? "—"}</td>
                      <td style={{ whiteSpace: "nowrap", fontSize: 11 }}>{formatDate(item.date_received)}</td>
                      <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--color-on-surface-variant)" }}>
                        {truncate(item.narrative, 60)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
            <button className="btn-secondary" onClick={() => setStep("options")}>
              <ArrowLeft size={14} /> Back to Configure
            </button>
            <button className="btn-primary" onClick={handleImport} disabled={actionLoading}>
              {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
              Import {previewData.selected_rows.toLocaleString()} Records
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Result ────────────────────────────────────────────────── */}
      {step === "result" && resultData && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Summary */}
          <div className="card" style={{ border: "1px solid color-mix(in oklch, var(--color-resolved) 35%, transparent)" }}>
            <div className="card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <CheckCircle2 size={20} style={{ color: "var(--color-resolved)" }} />
                <span style={{ fontWeight: 600, fontSize: "var(--text-headline-sm)" }}>Import Complete</span>
              </div>
              <Badge variant="success">Success</Badge>
            </div>
            <div style={{ padding: "16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
                {[
                  { label: "Scanned", value: resultData.scanned_rows.toLocaleString() },
                  { label: "Matched", value: resultData.matched_rows.toLocaleString() },
                  { label: "Imported", value: resultData.imported_rows.toLocaleString(), color: "var(--color-resolved)" },
                  { label: "Skipped", value: resultData.skipped_rows.toLocaleString(), color: resultData.skipped_rows > 0 ? "var(--color-pending)" : undefined },
                ].map(({ label, value, color }) => (
                  <div key={label} className="stat-card">
                    <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-on-surface-variant)", fontWeight: 600 }}>{label}</span>
                    <span style={{ fontSize: 22, fontWeight: 700, color: color ?? "var(--color-on-background)" }}>{value}</span>
                  </div>
                ))}
              </div>

              {/* Log messages */}
              <div>
                <p className="form-label" style={{ marginBottom: 8 }}>Import Log</p>
                <div style={{ background: "var(--color-surface-container-low)", borderRadius: "var(--radius-DEFAULT)", padding: "12px", border: "1px solid var(--color-outline-variant)", maxHeight: 240, overflowY: "auto" }}>
                  {resultData.logs.map((log, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 4, fontSize: "var(--text-body-sm)" }}>
                      {log.level === "success" ? <CheckCircle2 size={13} style={{ color: "var(--color-resolved)", flexShrink: 0, marginTop: 2 }} />
                        : log.level === "error" ? <XCircle size={13} style={{ color: "var(--color-error)", flexShrink: 0, marginTop: 2 }} />
                        : <div style={{ width: 13, height: 13, borderRadius: "50%", background: "var(--color-on-surface-variant)", flexShrink: 0, marginTop: 2, opacity: 0.4 }} />}
                      <span style={{ color: log.level === "error" ? "var(--color-error)" : "var(--color-on-surface)", lineHeight: 1.5 }}>
                        {log.message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-secondary" onClick={resetWizard}>Import More</button>
            <Link href="/queue" className="btn-primary">
              View Queue <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

