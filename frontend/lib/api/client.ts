/**
 * Base API client — thin fetch wrapper with auth, error handling, and
 * type-safe response parsing.
 *
 * All domain-specific functions live in their own modules (auth.ts,
 * complaints.ts, …) and import `request` / `download` from here.
 */

const AUTH_KEY = "cp_api_key";

// ── Public helpers ───────────────────────────────────────────────────────────

export function getApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(AUTH_KEY) ?? "";
}

export function setApiKey(value: string): void {
  if (typeof window === "undefined") return;
  if (value.trim()) {
    localStorage.setItem(AUTH_KEY, value.trim());
  } else {
    localStorage.removeItem(AUTH_KEY);
  }
}

export function clearApiKey(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_KEY);
}

/** Base URL — set via NEXT_PUBLIC_API_BASE_URL env var. */
export function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? ""
  );
}

/** WebSocket URL derived from the API base URL. */
export function websocketUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_BASE_URL?.replace(/\/$/, "");
  if (explicit) return explicit.endsWith("/ws") ? explicit : `${explicit}/ws`;

  const base = apiBase();
  if (base) {
    try {
      const url = new URL(base);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      url.pathname = "/ws";
      return url.toString();
    } catch {
      /* fall through */
    }
  }

  if (typeof window !== "undefined") {
    const protocol =
      window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws`;
  }

  return "ws://localhost:8000/ws";
}

// ── Internal fetch helpers ───────────────────────────────────────────────────

function authHeaders(): HeadersInit {
  const key = getApiKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.text();
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
      else if (body) detail = body;
    } catch {
      /* ignore json parse errors */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

// ── Exported request functions ───────────────────────────────────────────────

export async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...init?.headers,
    },
  });
  return handleResponse<T>(response);
}

export async function download(path: string): Promise<Blob> {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(body || `Download failed with status ${response.status}`);
  }
  return response.blob();
}
