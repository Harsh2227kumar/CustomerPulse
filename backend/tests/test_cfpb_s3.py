import unittest

from app.ingestion.cfpb_s3 import (
    CfpbS3IngestionService,
    S3SourceUnavailableError,
    map_cfpb_csv_row,
)
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


class AthenaFixtureService(CfpbS3IngestionService):
    mode = "athena"
    athena_database = "customerpulse_data"
    athena_table = "cfpb_parquet"

    def __init__(self) -> None:
        self.queries: list[str] = []

    def _run_athena(self, query: str):
        self.queries.append(query)
        if "min(date_received)" in query:
            return [{"min_date": "2019-12-26", "max_date": "2026-02-01"}]
        if "DISTINCT product" in query:
            return [{"value": "Credit card or prepaid card"}]
        if "DISTINCT timely_response" in query:
            return [{"value": "true"}, {"value": "false"}]
        if "DISTINCT" in query:
            return []
        return [
            {
                "complaint_id": "101",
                "consumer_complaint_narrative": "Unexpected charge.",
                "product": "Credit card or prepaid card",
                "submitted_via": "Web",
                "timely_response": "true",
                "date_received": "2019-12-26",
            }
        ]


class UnavailableAthenaFixtureService(AthenaFixtureService):
    def _run_athena(self, query: str):
        raise S3SourceUnavailableError("AWS credentials cannot run Athena queries.")


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
        self.assertEqual(options.timely_responses, [False, True])
        self.assertEqual(str(options.date_received_min), "2026-01-10")
        self.assertEqual(str(options.date_received_max), "2026-02-01")

    def test_preview_filters_product_and_respects_limit(self) -> None:
        result = FixtureService().preview(
            S3ComplaintImportFilters(product="Credit card", max_records=1)
        )

        self.assertEqual(result.query_mode, "csv")
        self.assertEqual(result.matched_rows, 1)
        self.assertEqual(result.selected_rows, 1)
        self.assertTrue(result.result_limited)
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

    def test_athena_options_and_preview_use_query_backed_values(self) -> None:
        service = AthenaFixtureService()
        options = service.load_options()
        preview = service.preview(
            S3ComplaintImportFilters(product="Credit card or prepaid card", max_records=1)
        )

        self.assertEqual(options.query_mode, "athena")
        self.assertEqual(options.products, ["Credit card or prepaid card"])
        self.assertEqual(options.timely_responses, [False, True])
        self.assertEqual(preview.items[0].complaint_id, "101")
        self.assertTrue(any("product_partition" in query for query in service.queries))

    def test_athena_permission_failure_returns_unavailable_options(self) -> None:
        options = UnavailableAthenaFixtureService().load_options()

        self.assertFalse(options.available)
        self.assertEqual(options.query_mode, "athena")
        self.assertEqual(options.products, [])
        self.assertEqual(options.unavailable_reason, "AWS credentials cannot run Athena queries.")


if __name__ == "__main__":
    unittest.main()
