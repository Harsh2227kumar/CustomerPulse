import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ComplaintFilters } from "../types";

const filters: ComplaintFilters = {
  search: " late fee ",
  sentiment: "Negative",
  channel: "Email",
  product: "Credit card",
  churn_risk: "High",
  urgency_min: "70",
  urgency_max: "",
  date_received_min: "2026-01-01",
  date_received_max: "",
  timely_response: "false",
  ai_status: "",
  human_review_reason: "",
  sort_by: "urgency_score",
  sort_direction: "asc",
};

describe("API client", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_API_BASE_URL", "");
    vi.stubEnv("VITE_WS_BASE_URL", "");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("serializes active complaint filters into the request URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], limit: 25, offset: 5, count: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { getComplaints } = await import("./client");

    const response = await getComplaints(filters, 25, 5);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/complaints?limit=25&offset=5&sort_by=urgency_score&sort_direction=asc&search=late+fee&sentiment=Negative&channel=Email&product=Credit+card&churn_risk=High&urgency_min=70&date_received_min=2026-01-01&timely_response=false",
      { headers: { "Content-Type": "application/json" } },
    );
    expect(response.count).toBe(0);
  });

  it("surfaces API detail messages for failed requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "S3 complaint import is not configured." }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const { getS3ImportOptions } = await import("./client");

    await expect(getS3ImportOptions()).rejects.toThrow("S3 complaint import is not configured.");
  });

  it("preserves structured S3 import failure codes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: { code: "athena_timeout", message: "Athena query timed out." } }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const { ApiError, getS3ImportOptions } = await import("./client");

    await expect(getS3ImportOptions()).rejects.toMatchObject({
      name: "ApiError",
      status: 502,
      code: "athena_timeout",
      message: "Athena query timed out.",
    });
    expect(ApiError).toBeDefined();
  });

  it("attaches a saved bearer key to protected requests", async () => {
    window.localStorage.setItem("customerpulse_api_key", "manager-key");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ job_id: "job-1", job_type: "embedding_backfill", status: "queued", total_items: 0, counts: {}, created_by: "manager", created_at: new Date().toISOString(), items: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { createEmbeddingBackfillJob } = await import("./client");

    await createEmbeddingBackfillJob();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/embedding-backfill",
      { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer manager-key" } },
    );
  });

  it("derives a secure websocket endpoint from an HTTPS API base URL", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.customerpulse.example/");
    const { apiBaseUrl, websocketUrl } = await import("./client");

    expect(apiBaseUrl).toBe("https://api.customerpulse.example");
    expect(websocketUrl()).toBe("wss://api.customerpulse.example/ws");
  });
});
