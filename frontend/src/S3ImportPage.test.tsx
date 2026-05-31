import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { S3ImportPage } from "./S3ImportPage";
import {
  createProcessingJob,
  getJob,
  getS3ImportOptions,
  importS3Complaints,
  previewS3Import,
  processImportedComplaint,
} from "./api/client";
import type { ProcessingJobResponse, S3ImportOptionsResponse, S3ImportPreviewResponse } from "./types";

vi.mock("./api/client", () => ({
  createProcessingJob: vi.fn(),
  getJob: vi.fn(),
  getS3ImportOptions: vi.fn(),
  importS3Complaints: vi.fn(),
  previewS3Import: vi.fn(),
  processImportedComplaint: vi.fn(),
}));

const options: S3ImportOptionsResponse = {
  source: { label: "Private CFPB import source" },
  query_mode: "athena",
  scanned_rows: 120,
  eligible_rows: 80,
  products: ["Credit card", "Mortgage"],
  sub_products: [],
  issues: ["Billing dispute"],
  companies: ["Example Bank"],
  channels: ["Web"],
  timely_responses: [true, false],
  date_received_min: "2026-01-01",
  date_received_max: "2026-05-20",
};

const preview: S3ImportPreviewResponse = {
  source: options.source,
  query_mode: "athena",
  scanned_rows: 120,
  matched_rows: 1,
  selected_rows: 1,
  result_limited: false,
  items: [
    {
      complaint_id: "complaint-1",
      narrative: "Unexpected credit card fee.",
      product: "Credit card",
      sub_product: null,
      issue: "Billing dispute",
      company: "Example Bank",
      channel: "Web",
      timely_response: true,
      date_received: "2026-05-20T00:00:00Z",
    },
  ],
};

const completedJob: ProcessingJobResponse = {
  job_id: "job-1",
  job_type: "process_complaints",
  status: "completed",
  total_items: 1,
  counts: { queued: 0, running: 0, completed: 1, human_review: 0, failed: 0 },
  created_by: "demo-manager",
  created_at: "2026-05-31T00:00:00Z",
  started_at: "2026-05-31T00:00:01Z",
  finished_at: "2026-05-31T00:00:02Z",
  items: [{ complaint_id: "complaint-1", status: "completed", attempt_count: 1, error_message: null, attempt_history: [] }],
};

describe("S3ImportPage", () => {
  beforeEach(() => {
    vi.mocked(createProcessingJob).mockReset();
    vi.mocked(getJob).mockReset();
    vi.mocked(getS3ImportOptions).mockResolvedValue(options);
    vi.mocked(previewS3Import).mockResolvedValue(preview);
    vi.mocked(importS3Complaints).mockReset();
    vi.mocked(processImportedComplaint).mockReset();
  });

  it("loads source options and returns to the dashboard", async () => {
    const onBack = vi.fn();
    const user = userEvent.setup();

    render(<S3ImportPage onBack={onBack} />);

    expect(await screen.findByText("Private CFPB import source")).toBeInTheDocument();
    expect(screen.getByText("Athena / Parquet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Return to dashboard" }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("previews complaints with the selected source filters", async () => {
    const user = userEvent.setup();
    render(<S3ImportPage onBack={vi.fn()} />);

    await screen.findByText("Private CFPB import source");
    await user.selectOptions(screen.getByLabelText("Product category"), "Credit card");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    await waitFor(() => {
      expect(previewS3Import).toHaveBeenCalledWith(
        expect.objectContaining({ product: "Credit card", max_records: 50 }),
      );
    });
    expect(await screen.findByText("1 selected from 120 scanned rows")).toBeInTheDocument();
    expect(screen.getByText("Unexpected credit card fee.")).toBeInTheDocument();
  });

  it("creates a batch processing job for imported preview rows", async () => {
    const user = userEvent.setup();
    vi.mocked(importS3Complaints).mockResolvedValue({
      status: "success",
      source: options.source,
      scanned_rows: 120,
      matched_rows: 1,
      imported_rows: 1,
      skipped_rows: 0,
      logs: [{ level: "success", message: "Imported 1 complaint." }],
    });
    vi.mocked(createProcessingJob).mockResolvedValue(completedJob);

    render(<S3ImportPage onBack={vi.fn()} />);

    await screen.findByText("Private CFPB import source");
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await screen.findByText("Unexpected credit card fee.");
    await user.click(screen.getByRole("button", { name: "Import to PostgreSQL" }));
    await screen.findByText(/1 complaints saved in PostgreSQL/i);
    await user.click(screen.getByRole("button", { name: "Process All" }));

    await waitFor(() => {
      expect(createProcessingJob).toHaveBeenCalledWith(["complaint-1"]);
    });
    expect(await screen.findByText("Batch processing completed")).toBeInTheDocument();
    expect(screen.getByText(/1 of 1 complaints handled/i)).toBeInTheDocument();
  });
});
