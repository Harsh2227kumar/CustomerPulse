import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { S3ImportPage } from "./S3ImportPage";
import {
  getS3ImportOptions,
  importS3Complaints,
  previewS3Import,
  processImportedComplaint,
} from "./api/client";
import type { S3ImportOptionsResponse, S3ImportPreviewResponse } from "./types";

vi.mock("./api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;

    constructor(message: string, status: number, code?: string) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code;
    }
  },
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

describe("S3ImportPage", () => {
  beforeEach(() => {
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
        expect.objectContaining({ product: "Credit card", max_records: 5 }),
      );
    });
    expect(await screen.findByText("1 selected from 120 scanned rows")).toBeInTheDocument();
    expect(screen.getByText("Unexpected credit card fee.")).toBeInTheDocument();
  });

  it("shows a clear status panel for structured Athena failures", async () => {
    const { ApiError } = await import("./api/client");
    vi.mocked(getS3ImportOptions).mockRejectedValue(
      new ApiError("Athena query timed out.", 502, "athena_timeout"),
    );

    render(<S3ImportPage onBack={vi.fn()} />);

    await screen.findByText("Athena query timed out.");
    expect(screen.getAllByText("Athena query timed out")).toHaveLength(2);
    expect(screen.getByText("Athena query timed out.")).toBeInTheDocument();
  });
});
