import unittest

from app.ingestion.cfpb_s3 import CfpbS3IngestionService, map_cfpb_csv_row
from app.schemas.ingestion import S3ComplaintImportFilters


ROWS = [
    {
        "Complaint ID": "100",
        "Consumer complaint narrative": "Unexpected credit card charge.",
        "Product": "Credit card",
        "Issue": "Billing dispute",
        "Company": "Example Bank",
        "Submitted via": "Web",
        "Timely response?": "Yes",
        "Date received": "2026-01-10",
    },
    {
        "Complaint ID": "101",
        "Consumer complaint narrative": "Mortgage payment issue.",
        "Product": "Mortgage",
        "Issue": "Payment",
        "Company": "Example Bank",
        "Submitted via": "Phone",
        "Timely response?": "No",
        "Date received": "2026-01-12",
    },
    {
        "Complaint ID": "102",
        "Consumer complaint narrative": "Credit card fee complaint.",
        "Product": "Credit card",
        "Issue": "Fees",
        "Company": "Other Bank",
        "Submitted via": "Web",
        "Timely response?": "Yes",
        "Date received": "2026-02-01",
    },
    {
        "Complaint ID": "103",
        "Consumer complaint narrative": "",
        "Product": "Credit card",
    },
]


class FixtureService(CfpbS3IngestionService):
    def __init__(self) -> None:
        self.bucket = "fixture-bucket"
        self.key = "raw/cfpb/fixture.csv"

    def _rows(self):
        yield from ROWS


class CfpbS3IngestionTests(unittest.TestCase):
    def test_maps_real_cfpb_csv_fields_and_pending_state(self) -> None:
        mapped = map_cfpb_csv_row(ROWS[0])

        self.assertIsNotNone(mapped)
        assert mapped is not None
        self.assertEqual(mapped["source_complaint_id"], "100")
        self.assertEqual(mapped["product"], "Credit card")
        self.assertEqual(mapped["ai_status"], "pending")

    def test_options_exclude_rows_without_narrative(self) -> None:
        options = FixtureService().load_options()

        self.assertEqual(options.source.label, "Private CFPB import source")
        self.assertNotIn("fixture-bucket", options.model_dump_json())
        self.assertEqual(options.scanned_rows, 4)
        self.assertEqual(options.eligible_rows, 3)
        self.assertEqual(options.products, ["Credit card", "Mortgage"])

    def test_preview_filters_product_and_respects_limit(self) -> None:
        result = FixtureService().preview(
            S3ComplaintImportFilters(product="Credit card", max_records=1)
        )

        self.assertEqual(result.matched_rows, 2)
        self.assertEqual(result.selected_rows, 1)
        self.assertEqual(result.items[0].complaint_id, "100")

    def test_import_selection_only_collects_requested_rows(self) -> None:
        selection = FixtureService().select_rows_for_import(
            S3ComplaintImportFilters(product="Credit card", max_records=1)
        )
        scanned, matched, skipped, rows = selection

        self.assertEqual(scanned, 1)
        self.assertEqual(matched, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual([row["source_complaint_id"] for row in rows], ["100"])


if __name__ == "__main__":
    unittest.main()
