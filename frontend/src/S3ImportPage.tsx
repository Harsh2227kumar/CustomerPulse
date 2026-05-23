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
import { getS3ImportOptions, importS3Complaints, previewS3Import } from "./api/client";
import type {
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

  async function loadOptions() {
    setLoadingOptions(true);
    setOptionsError(null);
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
        <div><CloudDownload size={18} /><span>Source</span><strong>{options ? `s3://${options.source.bucket}/${options.source.key}` : "Not loaded"}</strong></div>
        <div><FileSearch size={18} /><span>Eligible rows</span><strong>{options?.eligible_rows.toLocaleString() ?? "-"}</strong></div>
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
            <span>Raw CSV filters</span>
          </div>
          <label>
            Product category
            <select
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
              value={filters.issue ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, issue: valueOrNull(event.target.value) }))}
            >
              <option value="">All issues</option>
              {options?.issues.map((issue) => <option key={issue} value={issue}>{issue}</option>)}
            </select>
          </label>
          <label>
            Company
            <input
              list="s3-companies"
              value={filters.company ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, company: valueOrNull(event.target.value) }))}
              placeholder="All companies"
            />
            <datalist id="s3-companies">
              {options?.companies.map((company) => <option key={company} value={company} />)}
            </datalist>
          </label>
          <div className="control-pair">
            <label>
              Channel
              <select
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
                value={filters.timely_response === null ? "" : String(filters.timely_response)}
                onChange={(event) => setFilters((current) => ({
                  ...current,
                  timely_response: event.target.value === "" ? null : event.target.value === "true",
                }))}
              >
                <option value="">Any</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
          </div>
          <div className="control-pair">
            <label>
              Received after
              <input type="date" value={filters.date_received_min ?? ""} onChange={(event) => setFilters((current) => ({ ...current, date_received_min: valueOrNull(event.target.value) }))} />
            </label>
            <label>
              Received before
              <input type="date" value={filters.date_received_max ?? ""} onChange={(event) => setFilters((current) => ({ ...current, date_received_max: valueOrNull(event.target.value) }))} />
            </label>
          </div>
          <label>
            Maximum complaints to import
            <input
              type="number"
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
          <article className="panel preview-panel">
            <div className="panel-heading">
              <div>
                <h2>Selected Complaints</h2>
                <p>
                  {preview
                    ? `${preview.selected_rows.toLocaleString()} selected from ${preview.matched_rows.toLocaleString()} matches`
                    : "Preview a selection before importing"}
                </p>
              </div>
            </div>
            {preview?.items.length ? (
              <div className="table-scroll">
                <table>
                  <thead><tr><th>Product</th><th>Issue</th><th>Company</th><th>Received</th></tr></thead>
                  <tbody>
                    {preview.items.map((item) => (
                      <tr key={item.complaint_id}>
                        <td><strong>{item.product ?? "Unknown"}</strong><span>{item.narrative}</span></td>
                        <td>{item.issue ?? "Unknown"}</td>
                        <td>{item.company ?? "Unknown"}</td>
                        <td>{formatDate(item.date_received)}</td>
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
          {(result?.logs.length || failureLogs.length) && (
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
