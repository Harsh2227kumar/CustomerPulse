"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  ChevronRight,
  Loader2,
  MessageSquarePlus,
  RotateCcw,
} from "lucide-react";
import { processComplaint } from "@/lib/api/complaints";
import type { ProcessedComplaintResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import {
  aiStatusVariant,
  churnRiskVariant,
  sentimentVariant,
  toPercent,
  formatDateTime,
  humanize,
} from "@/lib/utils/format";

const CHANNELS = ["Phone", "Email", "Web", "Chat", "Mail", "Referral", ""];
const PRODUCTS = [
  "Credit card",
  "Mortgage",
  "Checking or savings account",
  "Debt collection",
  "Student loan",
  "Auto loan or lease",
  "Money transfer",
  "Payday loan",
  "Virtual currency",
  "",
];

export default function NewComplaintPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    narrative: "",
    channel: "",
    product: "",
    issue: "",
    company: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ProcessedComplaintResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleChange(
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.narrative.trim()) return;
    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await processComplaint({
        complaint_id: crypto.randomUUID(),
        narrative: form.narrative.trim(),
        channel: form.channel || null,
        product: form.product || null,
        issue: form.issue || null,
        company: form.company || null,
      });
      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to process complaint."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleReset() {
    setForm({ narrative: "", channel: "", product: "", issue: "", company: "" });
    setResult(null);
    setError(null);
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-lg">
        <h1 className="text-headline-lg font-bold text-on-background">
          New Complaint
        </h1>
        <p className="text-body-sm text-on-surface-variant mt-xs">
          Submit a customer complaint for immediate AI analysis. The system will
          assess sentiment, urgency, churn risk, and generate a draft response.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-lg">
        {/* Form */}
        <div className="lg:col-span-3">
          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-sm">
                <MessageSquarePlus size={18} className="text-primary" />
                <h2 className="text-headline-sm font-semibold text-on-background">
                  Complaint Details
                </h2>
              </div>
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmit} className="flex flex-col gap-md">
                {/* Narrative */}
                <div>
                  <label className="form-label" htmlFor="narrative">
                    Customer Narrative *
                  </label>
                  <textarea
                    id="narrative"
                    name="narrative"
                    value={form.narrative}
                    onChange={handleChange}
                    rows={7}
                    placeholder="Describe the customer's complaint in detail…"
                    className="form-input resize-none h-auto py-sm"
                    required
                    disabled={submitting}
                  />
                  <p className="text-label-md text-on-surface-variant mt-xs">
                    {form.narrative.length} characters (min. recommended: 50)
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-md">
                  {/* Channel */}
                  <div>
                    <label className="form-label" htmlFor="channel">
                      Channel
                    </label>
                    <select
                      id="channel"
                      name="channel"
                      value={form.channel}
                      onChange={handleChange}
                      className="form-select"
                      disabled={submitting}
                    >
                      <option value="">Select channel</option>
                      {CHANNELS.filter(Boolean).map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Product */}
                  <div>
                    <label className="form-label" htmlFor="product">
                      Product
                    </label>
                    <select
                      id="product"
                      name="product"
                      value={form.product}
                      onChange={handleChange}
                      className="form-select"
                      disabled={submitting}
                    >
                      <option value="">Select product</option>
                      {PRODUCTS.filter(Boolean).map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Issue */}
                  <div>
                    <label className="form-label" htmlFor="issue">
                      Issue
                    </label>
                    <input
                      id="issue"
                      name="issue"
                      type="text"
                      value={form.issue}
                      onChange={handleChange}
                      placeholder="e.g. Billing dispute"
                      className="form-input"
                      disabled={submitting}
                    />
                  </div>

                  {/* Company */}
                  <div>
                    <label className="form-label" htmlFor="company">
                      Company
                    </label>
                    <input
                      id="company"
                      name="company"
                      type="text"
                      value={form.company}
                      onChange={handleChange}
                      placeholder="e.g. ACME Bank"
                      className="form-input"
                      disabled={submitting}
                    />
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <div className="flex items-start gap-sm p-md rounded bg-error-container border border-error/20">
                    <AlertCircle size={16} className="text-on-error-container mt-px shrink-0" />
                    <p className="text-body-sm text-on-error-container">{error}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-sm pt-xs">
                  <button
                    type="submit"
                    className="btn-primary flex-1"
                    disabled={submitting || !form.narrative.trim()}
                  >
                    {submitting ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Processing…
                      </>
                    ) : (
                      <>
                        <Bot size={16} />
                        Process with AI
                      </>
                    )}
                  </button>
                  {(result || error) && (
                    <button
                      type="button"
                      onClick={handleReset}
                      className="btn-secondary"
                    >
                      <RotateCcw size={16} />
                      Reset
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* Result panel */}
        <div className="lg:col-span-2">
          {submitting ? (
            <div className="card h-full flex items-center justify-center p-xl">
              <div className="text-center flex flex-col items-center gap-md">
                <Loader2 size={32} className="animate-spin text-primary" />
                <p className="text-body-md text-on-surface-variant">
                  AI is analyzing the complaint…
                </p>
              </div>
            </div>
          ) : result ? (
            <div className="card">
              <div className="card-header">
                <div className="flex items-center gap-sm">
                  <CheckCircle2 size={18} className="text-status-resolved" />
                  <h2 className="text-headline-sm font-semibold text-on-background">
                    AI Analysis
                  </h2>
                </div>
                <Badge variant={aiStatusVariant(result.ai_status)}>
                  {humanize(result.ai_status)}
                </Badge>
              </div>
              <div className="p-lg flex flex-col gap-md overflow-y-auto max-h-[70vh]">
                {/* Complaint ID */}
                <div>
                  <p className="form-label">Complaint ID</p>
                  <p className="font-mono text-mono-data text-on-surface-variant break-all">
                    {result.complaint_id}
                  </p>
                </div>

                {/* Metrics row */}
                <div className="grid grid-cols-2 gap-sm">
                  <div className="bg-surface-container-low rounded p-sm">
                    <p className="text-label-md text-on-surface-variant">Sentiment</p>
                    <Badge variant={sentimentVariant(result.sentiment)}>
                      {result.sentiment}
                    </Badge>
                  </div>
                  <div className="bg-surface-container-low rounded p-sm">
                    <p className="text-label-md text-on-surface-variant">Churn Risk</p>
                    <Badge variant={churnRiskVariant(result.churn_risk)}>
                      {result.churn_risk}
                    </Badge>
                  </div>
                  <div className="bg-surface-container-low rounded p-sm">
                    <p className="text-label-md text-on-surface-variant">Urgency</p>
                    <p className="text-headline-sm font-bold text-on-background">
                      {result.urgency_score}
                      <span className="text-on-surface-variant text-body-sm">/100</span>
                    </p>
                  </div>
                  <div className="bg-surface-container-low rounded p-sm">
                    <p className="text-label-md text-on-surface-variant">AI Confidence</p>
                    <p className="text-headline-sm font-bold text-on-background">
                      {toPercent(result.ai_confidence)}
                    </p>
                  </div>
                </div>

                {/* Category */}
                <div>
                  <p className="form-label">Category</p>
                  <p className="text-body-sm text-on-background">{result.category}</p>
                </div>

                {/* Next action */}
                <div>
                  <p className="form-label">Next Action</p>
                  <p className="text-body-sm text-on-background">{result.next_action}</p>
                </div>

                {/* Draft response */}
                <div>
                  <p className="form-label">Draft Response</p>
                  <p className="text-body-sm text-on-background bg-surface-container-low rounded p-sm">
                    {result.draft_response}
                  </p>
                </div>

                {/* Human review flag */}
                {result.human_review_reason && (
                  <div className="flex items-start gap-sm p-sm rounded bg-status-pending/10 border border-status-pending/20">
                    <AlertCircle size={14} className="text-status-pending mt-px shrink-0" />
                    <div>
                      <p className="text-label-md text-on-surface-variant">Human review required</p>
                      <p className="text-body-sm text-on-background">
                        {humanize(result.human_review_reason)}
                      </p>
                    </div>
                  </div>
                )}

                {/* Similar cases */}
                {result.similar_cases.length > 0 && (
                  <div>
                    <p className="form-label">Similar Cases ({result.similar_cases.length})</p>
                    <div className="flex flex-col gap-xs">
                      {result.similar_cases.map((sc) => (
                        <div
                          key={sc.complaint_id}
                          className="bg-surface-container-low rounded p-sm border border-outline-variant"
                        >
                          <p className="font-mono text-mono-data text-on-surface-variant">
                            {sc.complaint_id}
                          </p>
                          <p className="text-body-sm text-on-background mt-xs line-clamp-2">
                            {sc.approved_response ?? sc.next_action ?? "—"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* View in queue link */}
                <a
                  href={`/queue/${result.complaint_id}`}
                  className="btn-secondary w-full justify-center mt-sm"
                >
                  View full workspace
                  <ChevronRight size={16} />
                </a>
              </div>
            </div>
          ) : (
            <div className="card h-full flex items-center justify-center p-xl text-center">
              <div>
                <Bot size={40} className="text-on-surface-variant opacity-30 mx-auto mb-md" />
                <p className="text-body-md font-semibold text-on-surface-variant">
                  AI Results
                </p>
                <p className="text-body-sm text-on-surface-variant mt-xs">
                  Submit a complaint to see AI analysis, sentiment, urgency
                  score, and a draft response.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
