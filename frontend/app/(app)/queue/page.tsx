"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ChevronRight,
  ClipboardCopy,
  ExternalLink,
  Filter,
  FilePlus,
  RefreshCw,
  Search,
  X,
  Zap,
} from "lucide-react";
import { getComplaints } from "@/lib/api/complaints";
import { createProcessingJob } from "@/lib/api/jobs";
import type { ComplaintFilters, ComplaintListItem } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Pagination } from "@/components/ui/Pagination";
import {
  aiStatusVariant,
  churnRiskVariant,
  formatDate,
  formatDateTime,
  humanize,
  sentimentVariant,
  slaVariant,
  toPercent,
  truncate,
} from "@/lib/utils/format";

const EMPTY_FILTERS: ComplaintFilters = {
  search: "",
  sentiment: "",
  channel: "",
  product: "",
  churn_risk: "",
  urgency_min: "",
  urgency_max: "",
  date_received_min: "",
  date_received_max: "",
  timely_response: "",
  ai_status: "",
  human_review_reason: "",
  sort_by: "created_at",
  sort_direction: "desc",
};

export default function QueuePage() {
  const [filters, setFilters] = useState<ComplaintFilters>(EMPTY_FILTERS);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<ComplaintListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchGroupType, setBatchGroupType] = useState<"product" | "channel" | "category">("product");
  const [batchGroupVal, setBatchGroupVal] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchData = useCallback(async (f: ComplaintFilters, l: number, o: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getComplaints(f, l, o);
      setItems(res.items);
      setTotal(res.count);
      if (res.items.length > 0 && (!selectedId || !res.items.find((i) => i.complaint_id === selectedId))) {
        setSelectedId(res.items[0].complaint_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load complaints");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { fetchData(filters, limit, offset); }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [filters, limit, offset, fetchData]);

  function setFilter<K extends keyof ComplaintFilters>(key: K, val: ComplaintFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: val }));
    setOffset(0);
  }

  function resetFilters() {
    setFilters(EMPTY_FILTERS);
    setOffset(0);
  }

  function copyId(id: string) {
    navigator.clipboard.writeText(id).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function handleProcessSelected() {
    if (selectedRows.length === 0) return;
    setBatchLoading(true);
    try {
      const res = await createProcessingJob(selectedRows);
      alert(`Dispatched AI analysis job ${res.job_id} for ${res.total_items} selected complaints!`);
      setSelectedRows([]);
      fetchData(filters, limit, offset);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Batch AI dispatch failed");
    } finally {
      setBatchLoading(false);
    }
  }

  async function handleProcessGroup() {
    if (!batchGroupVal.trim()) return;
    setBatchLoading(true);
    try {
      const filterKey = batchGroupType === "product" ? "product" : batchGroupType === "channel" ? "channel" : "search";
      const qRes = await getComplaints({ ...EMPTY_FILTERS, [filterKey]: batchGroupVal, ai_status: "pending" }, 100, 0);
      const ids = qRes.items.map((i) => i.complaint_id);
      if (ids.length === 0) {
        alert(`No pending/unprocessed complaints found for ${batchGroupType} "${batchGroupVal}".`);
        return;
      }
      const res = await createProcessingJob(ids);
      alert(`Dispatched AI batch job ${res.job_id} for ${res.total_items} complaints in "${batchGroupVal}"!`);
      setBatchModalOpen(false);
      setBatchGroupVal("");
      fetchData(filters, limit, offset);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Group AI batch dispatch failed");
    } finally {
      setBatchLoading(false);
    }
  }

  const selected = items.find((i) => i.complaint_id === selectedId) ?? null;
  const activeFilterCount = Object.entries(filters).filter(
    ([k, v]) => k !== "sort_by" && k !== "sort_direction" && v !== ""
  ).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)", gap: 0 }}>
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div style={{ padding: "16px 0 12px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexShrink: 0 }}>
        <div>
          <h1 className="page-title">Complaint Queue</h1>
          <p className="page-subtitle">{total.toLocaleString()} complaints · Select a row to preview details</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className={showFilters ? "btn-primary" : "btn-secondary"}
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter size={14} />
            Filters
            {activeFilterCount > 0 && (
              <span className="badge-info" style={{ marginLeft: 4 }}>{activeFilterCount}</span>
            )}
          </button>
          <button className="btn-secondary" onClick={() => fetchData(filters, limit, offset)} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            className="btn-secondary"
            style={{ color: "var(--color-primary)", borderColor: "var(--color-primary)", fontWeight: 600 }}
            onClick={() => setBatchModalOpen(true)}
            title="Run AI processing on a category or group"
          >
            <Zap size={14} /> Batch AI Process
          </button>
          <Link href="/new-complaint" className="btn-primary">
            <FilePlus size={14} /> New Complaint
          </Link>
        </div>
      </div>

      {/* ── Filter bar (collapsible) ───────────────────────────────────────── */}
      {showFilters && (
        <div className="card" style={{ padding: 12, marginBottom: 12, flexShrink: 0 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 8 }}>
            {/* Search */}
            <div style={{ gridColumn: "span 2" }}>
              <label className="form-label" htmlFor="q-search">Search</label>
              <div style={{ position: "relative" }}>
                <Search size={14} style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", color: "var(--color-on-surface-variant)" }} />
                <input
                  id="q-search"
                  type="text"
                  className="form-input"
                  style={{ paddingLeft: 28 }}
                  placeholder="Keyword or complaint ID…"
                  value={filters.search}
                  onChange={(e) => setFilter("search", e.target.value)}
                />
              </div>
            </div>

            {/* Sentiment */}
            <div>
              <label className="form-label" htmlFor="q-sentiment">Sentiment</label>
              <select id="q-sentiment" className="form-select" value={filters.sentiment} onChange={(e) => setFilter("sentiment", e.target.value as ComplaintFilters["sentiment"])}>
                <option value="">All</option>
                <option value="Positive">Positive</option>
                <option value="Neutral">Neutral</option>
                <option value="Negative">Negative</option>
              </select>
            </div>

            {/* Churn Risk */}
            <div>
              <label className="form-label" htmlFor="q-churn">Churn Risk</label>
              <select id="q-churn" className="form-select" value={filters.churn_risk} onChange={(e) => setFilter("churn_risk", e.target.value as ComplaintFilters["churn_risk"])}>
                <option value="">All</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>

            {/* AI Status */}
            <div>
              <label className="form-label" htmlFor="q-status">AI Status</label>
              <select id="q-status" className="form-select" value={filters.ai_status} onChange={(e) => setFilter("ai_status", e.target.value as ComplaintFilters["ai_status"])}>
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="human_review">Human Review</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {/* Timely */}
            <div>
              <label className="form-label" htmlFor="q-timely">Timely</label>
              <select id="q-timely" className="form-select" value={filters.timely_response} onChange={(e) => setFilter("timely_response", e.target.value as ComplaintFilters["timely_response"])}>
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            {/* Channel */}
            <div>
              <label className="form-label" htmlFor="q-channel">Channel</label>
              <input id="q-channel" type="text" className="form-input" placeholder="e.g. Phone" value={filters.channel} onChange={(e) => setFilter("channel", e.target.value)} />
            </div>

            {/* Product */}
            <div>
              <label className="form-label" htmlFor="q-product">Product</label>
              <input id="q-product" type="text" className="form-input" placeholder="e.g. Mortgage" value={filters.product} onChange={(e) => setFilter("product", e.target.value)} />
            </div>

            {/* Urgency */}
            <div>
              <label className="form-label">Urgency Range</label>
              <div style={{ display: "flex", gap: 4 }}>
                <input type="number" className="form-input" placeholder="Min" min={0} max={100} value={filters.urgency_min} onChange={(e) => setFilter("urgency_min", e.target.value)} style={{ width: "50%" }} />
                <input type="number" className="form-input" placeholder="Max" min={0} max={100} value={filters.urgency_max} onChange={(e) => setFilter("urgency_max", e.target.value)} style={{ width: "50%" }} />
              </div>
            </div>

            {/* Date range */}
            <div>
              <label className="form-label">Date Received</label>
              <div style={{ display: "flex", gap: 4 }}>
                <input type="date" className="form-input" value={filters.date_received_min} onChange={(e) => setFilter("date_received_min", e.target.value)} style={{ width: "50%" }} />
                <input type="date" className="form-input" value={filters.date_received_max} onChange={(e) => setFilter("date_received_max", e.target.value)} style={{ width: "50%" }} />
              </div>
            </div>

            {/* Sort */}
            <div>
              <label className="form-label" htmlFor="q-sort">Sort By</label>
              <select id="q-sort" className="form-select" value={filters.sort_by} onChange={(e) => setFilter("sort_by", e.target.value as ComplaintFilters["sort_by"])}>
                <option value="created_at">Date Created</option>
                <option value="date_received">Date Received</option>
                <option value="processed_at">Processed At</option>
                <option value="urgency_score">Urgency Score</option>
                <option value="ai_confidence">AI Confidence</option>
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="q-dir">Direction</label>
              <select id="q-dir" className="form-select" value={filters.sort_direction} onChange={(e) => setFilter("sort_direction", e.target.value as "asc" | "desc")}>
                <option value="desc">Newest first</option>
                <option value="asc">Oldest first</option>
              </select>
            </div>
          </div>
          {activeFilterCount > 0 && (
            <div style={{ marginTop: 8, display: "flex", justifyContent: "flex-end" }}>
              <button className="btn-ghost" style={{ fontSize: "var(--text-body-sm)" }} onClick={resetFilters}>
                <X size={12} /> Clear all filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Main two-panel area ────────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, gap: 12, overflow: "hidden" }}>
        {/* Left: table */}
        <div className="card" style={{ flex: "0 0 60%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {error && (
            <div className="alert-error" style={{ margin: 12 }}>
              <AlertTriangle size={14} className="shrink-0" />
              {error}
            </div>
          )}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {loading && items.length === 0 ? (
              <LoadingSpinner fullPage label="Loading complaints…" />
            ) : items.length === 0 ? (
              <EmptyState
                title="No complaints found"
                description="Try adjusting your filters or search term."
                action={
                  <button className="btn-secondary" onClick={resetFilters}>
                    Clear filters
                  </button>
                }
              />
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 36, textAlign: "center" }}>
                      <input
                        type="checkbox"
                        checked={items.length > 0 && items.every((i) => selectedRows.includes(i.complaint_id))}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedRows(Array.from(new Set([...selectedRows, ...items.map((i) => i.complaint_id)])));
                          else setSelectedRows(selectedRows.filter((id) => !items.some((i) => i.complaint_id === id)));
                        }}
                      />
                    </th>
                    <th>ID</th>
                    <th>Product / Issue</th>
                    <th>Urgency</th>
                    <th>Risk</th>
                    <th>Sentiment</th>
                    <th>Status</th>
                    <th>SLA</th>
                    <th>Received</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.complaint_id}
                      className={selectedId === item.complaint_id ? "selected" : ""}
                      onClick={() => setSelectedId(item.complaint_id)}
                    >
                      <td style={{ textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedRows.includes(item.complaint_id)}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedRows([...selectedRows, item.complaint_id]);
                            else setSelectedRows(selectedRows.filter((id) => id !== item.complaint_id));
                          }}
                        />
                      </td>
                      <td>
                        <span className="id-pill">{item.complaint_id.slice(0, 12)}…</span>
                      </td>
                      <td style={{ maxWidth: 180 }}>
                        <div style={{ fontWeight: 500, fontSize: "var(--text-body-sm)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {item.product ?? "—"}
                        </div>
                        {item.issue && (
                          <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {item.issue}
                          </div>
                        )}
                      </td>
                      <td>
                        <UrgencyBar score={item.urgency_score} />
                      </td>
                      <td>
                        {item.churn_risk ? (
                          <Badge variant={churnRiskVariant(item.churn_risk)}>{item.churn_risk}</Badge>
                        ) : "—"}
                      </td>
                      <td>
                        {item.sentiment ? (
                          <Badge variant={sentimentVariant(item.sentiment)}>{item.sentiment}</Badge>
                        ) : "—"}
                      </td>
                      <td>
                        <Badge variant={aiStatusVariant(item.ai_status)}>
                          {item.ai_status.replace("_", " ")}
                        </Badge>
                      </td>
                      <td>
                        {item.timely_response != null ? (
                          <Badge variant={slaVariant(item.timely_response)}>
                            {item.timely_response === "Yes" ? "Timely" : "Late"}
                          </Badge>
                        ) : "—"}
                      </td>
                      <td style={{ whiteSpace: "nowrap", color: "var(--color-on-surface-variant)", fontSize: 11 }}>
                        {formatDate(item.date_received)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {/* Pagination */}
          <Pagination
            total={total}
            limit={limit}
            offset={offset}
            onOffsetChange={setOffset}
            onLimitChange={setLimit}
            isLoading={loading}
          />
        </div>

        {/* Right: detail panel */}
        <div className="card" style={{ flex: "0 0 calc(40% - 12px)", overflowY: "auto", display: "flex", flexDirection: "column" }}>
          {!selected ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <EmptyState title="No complaint selected" description="Click a row in the queue to preview details." />
            </div>
          ) : (
            <DetailPanel
              item={selected}
              onCopyId={() => copyId(selected.complaint_id)}
              copied={copied}
            />
          )}
        </div>
      </div>

      {/* Floating Action Bar */}
      {selectedRows.length > 0 && (
        <div style={{ position: "fixed", bottom: 28, left: "50%", transform: "translateX(-50%)", zIndex: 100, background: "var(--color-surface)", border: "2px solid var(--color-primary)", boxShadow: "0 10px 25px -5px rgba(0,0,0,0.3)", borderRadius: 999, padding: "10px 24px", display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontWeight: 600, fontSize: 13, color: "var(--color-on-surface)" }}>✓ {selectedRows.length} complaints selected</span>
          <button className="btn-secondary" style={{ height: 28, fontSize: 11, padding: "0 12px", borderRadius: 999 }} onClick={() => setSelectedRows([])}>Clear</button>
          <button className="btn-primary" style={{ height: 32, fontSize: 12, padding: "0 16px", borderRadius: 999 }} onClick={handleProcessSelected} disabled={batchLoading}>
            {batchLoading ? <RefreshCw size={14} className="animate-spin" /> : "⚡ Dispatch AI Analysis"}
          </button>
        </div>
      )}

      {/* Batch Group Modal */}
      {batchModalOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div className="card" style={{ width: 440, padding: 24, display: "flex", flexDirection: "column", gap: 16, background: "var(--color-surface)", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.3)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}><Zap size={18} className="text-primary" /> Batch AI Process Group</h3>
              <button className="btn-icon" onClick={() => setBatchModalOpen(false)}><X size={16} /></button>
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.5, color: "var(--color-on-surface-variant)" }}>
              Select a category, product, or channel to immediately dispatch all pending/unprocessed complaints in that group for AI analysis.
            </p>
            <div>
              <label className="form-label" style={{ marginBottom: 6 }}>Grouping Dimension</label>
              <select className="form-select" value={batchGroupType} onChange={(e: any) => setBatchGroupType(e.target.value)}>
                <option value="product">By Product (e.g. Mortgage, Credit Card)</option>
                <option value="channel">By Channel (e.g. Web, Phone)</option>
                <option value="category">By Category / Keyword</option>
              </select>
            </div>
            <div>
              <label className="form-label" style={{ marginBottom: 6 }}>Group Name / Keyword</label>
              <input className="form-input" placeholder={batchGroupType === "product" ? "e.g. Credit card" : batchGroupType === "channel" ? "e.g. Phone" : "e.g. Billing"} value={batchGroupVal} onChange={(e) => setBatchGroupVal(e.target.value)} />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
              <button className="btn-secondary" onClick={() => setBatchModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleProcessGroup} disabled={batchLoading || !batchGroupVal.trim()}>
                {batchLoading ? <RefreshCw size={14} className="animate-spin" /> : "Dispatch Batch AI Job"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function UrgencyBar({ score }: { score: number | null | undefined }) {
  if (score == null) return <span style={{ color: "var(--color-on-surface-variant)" }}>—</span>;
  const color =
    score >= 70 ? "var(--color-breach)"
    : score >= 40 ? "var(--color-pending)"
    : "var(--color-resolved)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <div style={{ width: 44, height: 4, background: "var(--color-surface-container)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${score}%`, background: color, borderRadius: 999 }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 600, minWidth: 20 }}>{score}</span>
    </div>
  );
}

function DetailPanel({ item, onCopyId, copied }: { item: ComplaintListItem; onCopyId: () => void; copied: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      {/* Header */}
      <div className="card-header" style={{ padding: "12px 16px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span className="id-pill" style={{ maxWidth: 200 }} title={item.complaint_id}>
              {item.complaint_id}
            </span>
            <button className="btn-icon" style={{ width: 24, height: 24 }} onClick={onCopyId} title="Copy ID">
              <ClipboardCopy size={12} />
            </button>
            {copied && <span style={{ fontSize: 10, color: "var(--color-resolved)" }}>Copied!</span>}
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Badge variant={aiStatusVariant(item.ai_status)}>{humanize(item.ai_status)}</Badge>
            {item.sentiment && <Badge variant={sentimentVariant(item.sentiment)}>{item.sentiment}</Badge>}
            {item.churn_risk && <Badge variant={churnRiskVariant(item.churn_risk)}>{item.churn_risk} Risk</Badge>}
          </div>
        </div>
        <Link href={`/queue/${item.complaint_id}`} className="btn-icon" title="Open full workspace">
          <ExternalLink size={16} />
        </Link>
      </div>

      {/* Info grid */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--color-outline-variant)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <InfoChip label="Product" value={item.product} />
          <InfoChip label="Channel" value={item.channel} />
          <InfoChip label="Company" value={item.company} />
          <InfoChip label="Timely SLA" value={item.timely_response ?? "N/A"} />
          <InfoChip label="Urgency" value={item.urgency_score != null ? `${item.urgency_score}/100` : "—"} />
          <InfoChip label="AI Confidence" value={item.ai_confidence != null ? toPercent(item.ai_confidence) : "—"} />
          <InfoChip label="Received" value={formatDate(item.date_received)} />
          <InfoChip label="Processed" value={formatDateTime(item.processed_at)} />
        </div>
      </div>

      {/* Human review flag */}
      {item.human_review_required && (
        <div className="alert-warning" style={{ margin: "12px 16px", borderRadius: "var(--radius-DEFAULT)" }}>
          <AlertTriangle size={14} />
          <div>
            <strong>Human review required</strong>
            {item.human_review_reason && (
              <p style={{ marginTop: 2 }}>{humanize(item.human_review_reason)}</p>
            )}
          </div>
        </div>
      )}

      {/* Next action */}
      {item.next_action && (
        <div style={{ padding: "0 16px 12px" }}>
          <p className="form-label" style={{ marginBottom: 4 }}>Next Action</p>
          <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)" }}>{item.next_action}</p>
        </div>
      )}

      {/* Draft response */}
      {item.draft_response && (
        <div style={{ padding: "0 16px 12px" }}>
          <p className="form-label" style={{ marginBottom: 4 }}>Draft Response</p>
          <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", background: "var(--color-surface-container-low)", padding: "8px", borderRadius: "var(--radius-DEFAULT)", lineHeight: 1.5 }}>
            {item.draft_response}
          </p>
        </div>
      )}

      {/* Narrative */}
      <div style={{ padding: "0 16px 12px", flex: 1 }}>
        <p className="form-label" style={{ marginBottom: 4 }}>Narrative</p>
        <p style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
          {expanded ? item.narrative : truncate(item.narrative, 200)}
        </p>
        {item.narrative.length > 200 && (
          <button
            className="btn-ghost"
            style={{ marginTop: 4, height: 24, padding: "0 4px", fontSize: 11 }}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Show less" : "Show more"} <ChevronRight size={11} style={{ transform: expanded ? "rotate(90deg)" : "none" }} />
          </button>
        )}
      </div>

      {/* Full workspace link */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--color-outline-variant)" }}>
        <Link href={`/queue/${item.complaint_id}`} className="btn-primary" style={{ width: "100%", justifyContent: "center" }}>
          Open Full Workspace <ChevronRight size={14} />
        </Link>
      </div>
    </>
  );
}

function InfoChip({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div style={{ background: "var(--color-surface-container-low)", borderRadius: "var(--radius-DEFAULT)", padding: "6px 8px" }}>
      <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: "var(--text-body-sm)", color: "var(--color-on-surface)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {value ?? "—"}
      </div>
    </div>
  );
}
