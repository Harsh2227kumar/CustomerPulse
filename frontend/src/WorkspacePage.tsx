import {
  ArrowLeft,
  Activity,
  MessageSquareText,
  Bell,
  Loader2,
  RefreshCcw,
  AlertTriangle,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { getComplaint360, addTimelineNote } from "./api/client";
import type { Complaint360Response, ChurnRisk, Sentiment } from "./types";

interface WorkspacePageProps {
  complaintId: string;
  onBack: () => void;
}

function riskClass(value: ChurnRisk | null): string {
  if (value === "High") return "danger";
  if (value === "Medium") return "warning";
  if (value === "Low") return "success";
  return "neutral";
}

function sentimentClass(value: Sentiment | null): string {
  if (value === "Negative") return "danger";
  if (value === "Positive") return "success";
  if (value === "Neutral") return "warning";
  return "neutral";
}

export function WorkspacePage({ complaintId, onBack }: WorkspacePageProps) {
  const [data, setData] = useState<Complaint360Response | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [submittingNote, setSubmittingNote] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const response = await getComplaint360(complaintId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load complaint 360 view");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [complaintId]);

  async function handleAddNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!noteText.trim()) return;

    setSubmittingNote(true);
    setNoteError(null);
    try {
      await addTimelineNote(complaintId, noteText.trim());
      setNoteText("");
      // Refresh timeline data
      const response = await getComplaint360(complaintId);
      setData(response);
    } catch (err) {
      setNoteError(err instanceof Error ? err.message : "Failed to add timeline note");
    } finally {
      setSubmittingNote(false);
    }
  }

  if (loading) {
    return (
      <main className="ops-page">
        <div className="loading-row" style={{ display: "flex", justifyContent: "center", padding: "100px 0" }}>
          <Loader2 className="spin" size={24} />
          <span style={{ marginLeft: "10px", fontSize: "16px", fontWeight: 600 }}>Loading 360 View...</span>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="ops-page">
        <header className="queue-page-header ops-header">
          <div>
            <button className="icon-button" type="button" onClick={onBack} aria-label="Back to dashboard">
              <ArrowLeft size={18} />
            </button>
            <div>
              <h1>Complaint 360 View</h1>
              <p>Failed to load view details</p>
            </div>
          </div>
        </header>
        <div className="ops-banner error" style={{ marginTop: "20px" }}>
          <AlertTriangle size={18} />
          <span style={{ marginLeft: "10px" }}>{error || "Complaint details not available"}</span>
        </div>
      </main>
    );
  }

  const { complaint, timeline, duplicate_group } = data;

  return (
    <main className="ops-page">
      <header className="queue-page-header ops-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button className="icon-button" type="button" onClick={onBack} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>Complaint 360 View</h1>
            <p>ID: {complaint.complaint_id || complaintId}</p>
          </div>
        </div>
        <button
          className="secondary-action compact-action"
          type="button"
          onClick={loadData}
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          <RefreshCcw size={14} /> Refresh
        </button>
      </header>

      {/* Highlights bar */}
      <section className="ops-banner success" style={{ display: "flex", gap: "20px", flexWrap: "wrap", padding: "16px", marginBottom: "20px" }}>
        <span>Sentiment: <strong className={`badge ${sentimentClass(complaint.sentiment)}`} style={{ marginLeft: "6px" }}>{complaint.sentiment ?? "Unknown"}</strong></span>
        <span>Category: <strong style={{ color: "#164f47" }}>{complaint.category ?? "Unclassified"}</strong></span>
        <span>Urgency: <strong style={{ color: "#164f47" }}>{complaint.urgency_score ?? 0}/100</strong></span>
        <span>Churn Risk: <strong className={`badge ${riskClass(complaint.churn_risk)}`} style={{ marginLeft: "6px" }}>{complaint.churn_risk ?? "Unknown"}</strong></span>
        <span>AI Status: <strong className={`status-pill ${complaint.ai_status}`} style={{ marginLeft: "6px" }}>{complaint.ai_status}</strong></span>
      </section>

      <section className="ops-grid">
        {/* Left Column: Timeline list & Add timeline note */}
        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          <article className="panel ops-card">
            <div className="panel-heading">
              <div>
                <h2>Timeline</h2>
                <p>Chronological communication and event history</p>
              </div>
              <Activity size={18} />
            </div>

            <div className="ops-detail" style={{ maxHeight: "520px", overflowY: "auto", paddingRight: "4px" }}>
              {timeline.items.length === 0 ? (
                <p className="ops-muted">No communication history or events logged.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  {timeline.items.map((item) => {
                    let typeColor = "#6f8580";
                    let IconComponent = MessageSquareText;

                    if (item.entry_type === "system") {
                      typeColor = "#22b89f";
                      IconComponent = Activity;
                    } else if (item.entry_type === "escalation") {
                      typeColor = "#b42318";
                      IconComponent = Bell;
                    }

                    return (
                      <div
                        key={item.id}
                        style={{
                          borderLeft: `4px solid ${typeColor}`,
                          paddingLeft: "12px",
                          paddingBottom: "4px",
                          display: "flex",
                          flexDirection: "column",
                          gap: "6px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "#164f47" }}>
                            <IconComponent size={14} style={{ color: typeColor }} />
                            {item.actor ? item.actor : "System"}
                          </span>
                          <span style={{ fontSize: "11px", color: "#607d75" }}>
                            {new Date(item.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p style={{ margin: 0, fontSize: "13.5px", color: "#18352f", lineHeight: "1.5" }}>
                          {item.message}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </article>

          <article className="panel ops-card">
            <div className="panel-heading">
              <div>
                <h2>Add Note</h2>
                <p>Post a custom note to the complaint timeline</p>
              </div>
              <MessageSquareText size={18} />
            </div>
            
            {noteError && <div className="ops-banner error">{noteError}</div>}

            <form className="ops-detail" onSubmit={handleAddNote}>
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Enter note text here..."
                required
                style={{ minHeight: "90px" }}
              />
              <div className="ops-button-row">
                <button
                  type="submit"
                  disabled={submittingNote || !noteText.trim()}
                  className="primary-action compact-action"
                >
                  {submittingNote ? "Posting Note..." : "Add Timeline Note"}
                </button>
              </div>
            </form>
          </article>
        </div>

        {/* Right Column: Duplicate group summary & Escalation */}
        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          {duplicate_group ? (
            <article className="panel ops-card">
              <div className="panel-heading">
                <div>
                  <h2>Duplicate Group</h2>
                  <p>Conflict and duplication group details</p>
                </div>
              </div>
              <div className="ops-detail">
                <span>Group ID <strong>{duplicate_group.group_id}</strong></span>
                <span>Status <strong className="badge warning">{duplicate_group.status}</strong></span>
                <span>Total Members <strong>{duplicate_group.member_count}</strong></span>
              </div>
            </article>
          ) : (
            <article className="panel ops-card">
              <div className="panel-heading">
                <div>
                  <h2>Duplicate Group</h2>
                  <p>Not member of any duplicate group</p>
                </div>
              </div>
              <p className="ops-muted" style={{ padding: "0 10px" }}>No duplicate groups detected for this complaint.</p>
            </article>
          )}

          <article className="panel ops-card">
            <div className="panel-heading">
              <div>
                <h2>Escalation Details</h2>
                <p>Tier level and team assignments</p>
              </div>
            </div>
            <div className="ops-detail">
              <p className="ops-muted" style={{ padding: "0 10px" }}>No escalation</p>
            </div>
          </article>
          
          <article className="panel ops-card">
            <div className="panel-heading">
              <div>
                <h2>Complaint narrative</h2>
                <p>Original text submission</p>
              </div>
            </div>
            <div className="ops-detail" style={{ padding: "10px" }}>
              <p style={{ margin: 0, color: "#18352f", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                {complaint.narrative}
              </p>
            </div>
          </article>
        </div>
      </section>
    </main>
  );
}
