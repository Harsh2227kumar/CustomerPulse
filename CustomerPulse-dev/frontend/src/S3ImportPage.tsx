import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  CloudDownload,
  Database,
  FileSearch,
  Loader2,
  RefreshCcw,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { getS3ImportOptions, importS3Complaints, previewS3Import, processImportedComplaint } from "./api/client";
import type {
  ProcessedComplaintResponse,
  S3ImportFilters,
  S3ImportLog,
  S3ImportOptionsResponse,
  S3ImportPreviewResponse,
  S3ImportResponse,
} from "./types";

const initialFilters: S3ImportFilters = {
  product: null,
  sub_product: null,
  issue: null,
  company: null,
  channel: null,
  timely_response: null,
  date_received_min: null,
  date_received_max: null,
  max_records: 50,
};

function valueOrNull(value: string): string | null {
  return value.trim() || null;
}

function formatDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value)) : "Unknown";
}

export function S3ImportPage({ onBack }: { onBack: () => void }) {
  const [options, setOptions] = useState<S3ImportOptionsResponse | null>(null);
  const [filters, setFilters] = useState<S3ImportFilters>(initialFilters);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [preview, setPreview] = useState<S3ImportPreviewResponse | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<S3ImportResponse | null>(null);
  const [failureLogs, setFailureLogs] = useState<S3ImportLog[]>([]);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [processedRows, setProcessedRows] = useState<Record<string, ProcessedComplaintResponse>>({});
  const [processingError, setProcessingError] = useState<string | null>(null);

  async function loadOptions() {
    setLoadingOptions(true);
    setOptionsError(null);
    setOptions(null);
    try {
      setOptions(await getS3ImportOptions());
    } catch (error) {
      setOptionsError(error instanceof Error ? error.message : "Unable to read S3 import source");
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    loadOptions();
  }, []);

  useEffect(() => {
    setPreview(null);
    setResult(null);
    setFailureLogs([]);
    setProcessedRows({});
    setProcessingError(null);
  }, [filters]);

  async function runPreview(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setPreviewing(true);
    setResult(null);
    setFailureLogs([]);
    try {
      setPreview(await previewS3Import(filters));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to preview import";
      setFailureLogs([{ level: "error", message }]);
    } finally {
      setPreviewing(false);
    }
  }

  async function runImport() {
    setImporting(true);
    setResult(null);
    setFailureLogs([]);
    try {
      const response = await importS3Complaints(filters);
      setResult(response);
      setPreview(await previewS3Import(filters));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Import failed";
      setFailureLogs([
        { level: "error", message: "No successful PostgreSQL import was confirmed." },
        { level: "error", message },
      ]);
    } finally {
      setImporting(false);
    }
  }

  async function runProcessing(complaintId: string) {
    setProcessingId(complaintId);
    setProcessingError(null);
    try {
      const processed = await processImportedComplaint(complaintId);
      setProcessedRows((current) => ({ ...current, [complaintId]: processed }));
    } catch (error) {
      setProcessingError(error instanceof Error ? error.message : "Complaint processing failed.");
    } finally {
      setProcessingId(null);
    }
  }

  return (
    <main className="import-page">
      <header className="import-header">
        <button className="icon-button" type="button" onClick={onBack} aria-label="Return to dashboard">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1>S3 Complaint Import</h1>
          <p>Private CFPB source to PostgreSQL</p>
        </div>
        <button className="secondary-action" type="button" onClick={loadOptions} disabled={loadingOptions}>
          {loadingOptions ? <Loader2 className="spin" size={16} /> : <RefreshCcw size={16} />}
          Refresh source
        </button>
      </header>

      <section className="source-band" aria-label="S3 source status">
        <div><CloudDownload size={18} /><span>Source</span><strong>{options?.source.label ?? "Not loaded"}</strong></div>
        <div><FileSearch size={18} /><span>Filter source</span><strong>{options?.query_mode === "athena" ? "Athena / Parquet" : options ? "CSV" : "-"}</strong></div>
        <div><Database size={18} /><span>Import limit</span><strong>{filters.max_records.toLocaleString()}</strong></div>
      </section>

      {optionsError && (
        <section className="import-alert failure">
          <AlertCircle size={18} />
          <strong>Source unavailable</strong>
          <span>{optionsError}</span>
        </section>
      )}

      <section className="import-layout">
        <form className="panel import-controls" onSubmit={runPreview}>
          <div className="panel-heading">
            <h2>Import Selection</h2>
            <span>S3 query filters</span>
          </div>
          <label>
            Product category
            <select
              disabled={!options || loadingOptions}
              value={filters.product ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, product: valueOrNull(event.target.value) }))}
            >
              <option value="">All products</option>
              {options?.products.map((product) => <option key={product} value={product}>{product}</option>)}
            </select>
          </label>
          <label>
            Sub-product
            <select
              disabled={!options || loadingOptions}
              value={filters.sub_product ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, sub_product: valueOrNull(event.target.value) }))}
            >
              <option value="">All sub-products</option>
              {options?.sub_products.map((product) => <option key={product} value={product}>{product}</option>)}
            </select>
          </label>
          <label>
            Issue
            <select
              disabled={!options || loadingOptions}
              value={filters.issue ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, issue: valueOrNull(event.target.value) }))}
            >
              <option value="">All issues</option>
              {options?.issues.map((issue) => <option key={issue} value={issue}>{issue}</option>)}
            </select>
          </label>
          <label>
            Company
            <select
              disabled={!options || loadingOptions}
              value={filters.company ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, company: valueOrNull(event.target.value) }))}
            >
              <option value="">All companies</option>
              {options?.companies.map((company) => <option key={company} value={company}>{company}</option>)}
            </select>
          </label>
          <div className="control-pair">
            <label>
              Channel
              <select
                disabled={!options || loadingOptions}
                value={filters.channel ?? ""}
                onChange={(event) => setFilters((current) => ({ ...current, channel: valueOrNull(event.target.value) }))}
              >
                <option value="">All channels</option>
                {options?.channels.map((channel) => <option key={channel} value={channel}>{channel}</option>)}
              </select>
            </label>
            <label>
              Timely response
              <select
                disabled={!options || loadingOptions}
                value={filters.timely_response === null ? "" : String(filters.timely_response)}
                onChange={(event) => setFilters((current) => ({
                  ...current,
                  timely_response: event.target.value === "" ? null : event.target.value === "true",
                }))}
              >
                <option value="">Any</option>
                {options?.timely_responses.includes(true) && <option value="true">Yes</option>}
                {options?.timely_responses.includes(false) && <option value="false">No</option>}
              </select>
            </label>
          </div>
          <div className="control-pair">
            <label>
              Received after
              <input
                type="date"
                disabled={!options || loadingOptions}
                min={options?.date_received_min ?? undefined}
                max={options?.date_received_max ?? undefined}
                value={filters.date_received_min ?? ""}
                onChange={(event) => setFilters((current) => ({ ...current, date_received_min: valueOrNull(event.target.value) }))}
              />
            </label>
            <label>
              Received before
              <input
                type="date"
                disabled={!options || loadingOptions}
                min={options?.date_received_min ?? undefined}
                max={options?.date_received_max ?? undefined}
                value={filters.date_received_max ?? ""}
                onChange={(event) => setFilters((current) => ({ ...current, date_received_max: valueOrNull(event.target.value) }))}
              />
            </label>
          </div>
          <label>
            Maximum complaints to import
            <input
              type="number"
              disabled={!options || loadingOptions}
              min={1}
              max={5000}
              value={filters.max_records}
              onChange={(event) => setFilters((current) => ({
                ...current,
                max_records: Math.min(5000, Math.max(1, Number(event.target.value) || 1)),
              }))}
            />
          </label>
          <div className="import-actions">
            <button className="secondary-action" type="submit" disabled={!options || previewing}>
              {previewing ? <Loader2 className="spin" size={16} /> : <FileSearch size={16} />}
              Preview
            </button>
            <button className="primary-action" type="button" onClick={runImport} disabled={!preview || importing}>
              {importing ? <Loader2 className="spin" size={16} /> : <Database size={16} />}
              Import to PostgreSQL
            </button>
          </div>
        </form>

        <section className="import-results">
          {result && (
            <article className="import-alert success">
              <CheckCircle2 size={20} />
              <strong>Import successful</strong>
              <span>{result.imported_rows.toLocaleString()} complaints saved in PostgreSQL.</span>
            </article>
          )}
          {failureLogs.length > 0 && (
            <article className="import-alert failure">
              <AlertCircle size={20} />
              <strong>Import failed</strong>
              <span>Review the operation log below.</span>
            </article>
          )}
          {processingError && (
            <article className="import-alert failure">
              <AlertCircle size={20} />
              <strong>Processing failed</strong>
              <span>{processingError}</span>
            </article>
          )}
          <article className="panel preview-panel">
            <div className="panel-heading">
              <div>
                <h2>Selected Complaints</h2>
                <p>
                  {preview
                    ? preview.result_limited
                      ? `First ${preview.selected_rows.toLocaleString()} matching complaints ready`
                      : `${preview.selected_rows.toLocaleString()} matching complaints found`
                    : "Preview a selection before importing"}
                </p>
              </div>
            </div>
            {preview?.items.length ? (
              <div className="table-scroll">
                <table>
                  <thead><tr><th>Product</th><th>Issue</th><th>Company</th><th>Received</th><th>AI action</th></tr></thead>
                  <tbody>
                    {preview.items.map((item) => (
                      <tr key={item.complaint_id}>
                        <td><strong>{item.product ?? "Unknown"}</strong><span>{item.narrative}</span></td>
                        <td>{item.issue ?? "Unknown"}</td>
                        <td>{item.company ?? "Unknown"}</td>
                        <td>{formatDate(item.date_received)}</td>
                        <td>
                          {processedRows[item.complaint_id] ? (
                            <span className="status-pill">Processed</span>
                          ) : (
                            <button
                              className="secondary-action"
                              type="button"
                              onClick={() => runProcessing(item.complaint_id)}
                              disabled={!result || processingId !== null}
                            >
                              {processingId === item.complaint_id ? <Loader2 className="spin" size={16} /> : null}
                              {result ? "Process" : "Import first"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <FileSearch size={22} />
                <strong>No preview loaded</strong>
                <span>The selected rows appear here before database import.</span>
              </div>
            )}
          </article>
          {Boolean(result?.logs.length || failureLogs.length) && (
            <article className="panel log-panel">
              <div className="panel-heading"><h2>Operation Log</h2></div>
              <ol>
                {(result?.logs ?? failureLogs).map((log, index) => (
                  <li className={log.level} key={`${log.level}-${index}`}>{log.message}</li>
                ))}
              </ol>
            </article>
          )}
        </section>
      </section>
    </main>
  );
}
