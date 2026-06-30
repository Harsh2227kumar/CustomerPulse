/** Formatting utilities shared across the frontend. */

// ── Date / time ──────────────────────────────────────────────────────────────

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(
    new Date(value)
  );
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return formatDate(value);
}

// ── Numbers ───────────────────────────────────────────────────────────────────

export function toPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0%";
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.round(normalized)}%`;
}

export function normalizeScore(value: number | null | undefined): number {
  if (value == null || Number.isNaN(value)) return 0;
  return value <= 1 ? value * 100 : value;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

// ── Badge / status helpers ───────────────────────────────────────────────────

export type BadgeVariant =
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral";

export function sentimentVariant(sentiment: string | null): BadgeVariant {
  if (sentiment === "Positive") return "success";
  if (sentiment === "Negative") return "danger";
  if (sentiment === "Neutral") return "warning";
  return "neutral";
}

export function churnRiskVariant(risk: string | null): BadgeVariant {
  if (risk === "High") return "danger";
  if (risk === "Medium") return "warning";
  if (risk === "Low") return "success";
  return "neutral";
}

export function aiStatusVariant(status: string): BadgeVariant {
  if (status === "completed") return "success";
  if (status === "human_review") return "warning";
  if (status === "failed") return "danger";
  if (status === "processing") return "info";
  return "neutral";
}

export function confidenceVariant(score: number | null | undefined): BadgeVariant {
  const normalized = normalizeScore(score);
  if (normalized >= 75) return "success";
  if (normalized >= 60) return "warning";
  return "danger";
}

export function slaVariant(timelyResponse: string | boolean | null): BadgeVariant {
  const isTimely =
    timelyResponse === true ||
    timelyResponse === "Yes";
  return isTimely ? "success" : "danger";
}

// ── Text helpers ─────────────────────────────────────────────────────────────

export function humanize(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function truncate(value: string, max = 120): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max)}…`;
}

// ── File download ─────────────────────────────────────────────────────────────

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
