import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

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


class CfpbS3IngestionTests(unittest.IsolatedAsyncioTestCase):
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

    def test_import_filters_rejects_greater_than_50(self) -> None:
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            S3ComplaintImportFilters(max_records=51)

    def test_date_parsing_fallback(self) -> None:
        from app.ingestion.cfpb_s3 import _datetime
        # ISO format
        self.assertEqual(_datetime("2026-01-10").date(), datetime(2026, 1, 10, tzinfo=timezone.utc).date())
        # MM/DD/YYYY format
        self.assertEqual(_datetime("01/10/2026").date(), datetime(2026, 1, 10, tzinfo=timezone.utc).date())
        # YYYY/MM/DD format
        self.assertEqual(_datetime("2026/01/10").date(), datetime(2026, 1, 10, tzinfo=timezone.utc).date())
        # Invalid format returns None
        self.assertIsNone(_datetime("invalid-date"))

    def test_channel_normalization(self) -> None:
        from app.ingestion.cfpb_s3 import normalize_channel
        self.assertEqual(normalize_channel("Web"), "web")
        self.assertEqual(normalize_channel("Submitted via Web"), "web")
        self.assertEqual(normalize_channel("Phone"), "phone")
        self.assertEqual(normalize_channel("Call Center"), "phone")
        self.assertEqual(normalize_channel("Email"), "email")
        self.assertEqual(normalize_channel("Chat"), "chat")
        self.assertEqual(normalize_channel("SMS"), "chat")
        self.assertEqual(normalize_channel("Postal mail"), "manual")
        self.assertEqual(normalize_channel("Fax"), "manual")
        self.assertEqual(normalize_channel("Referral"), "manual")

    @patch("app.ingestion.mock_timeline.TimelineService.add_event", new_callable=AsyncMock)
    async def test_api_import_triggers_timeline_events(self, mock_add_event) -> None:
        from app.api.ingestion import import_complaints
        from app.schemas.ingestion import S3ComplaintImportFilters
        from app.core.security import Principal
        from tests.conftest import FakeAsyncDB

        filters = S3ComplaintImportFilters(max_records=5)
        db = FakeAsyncDB()
        db.add = lambda x: None
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        principal = Principal(actor="test-manager", role="manager")
        
        with patch("app.api.ingestion.CfpbS3IngestionService") as MockService:
            mock_inst = MockService.return_value
            mock_inst.select_rows_for_import.return_value = (
                4, 1, 0,
                [
                    {
                        "id": "cfpb-100",
                        "source_complaint_id": "100",
                        "channel": "web",
                        "date_received": datetime(2026, 1, 10, tzinfo=timezone.utc),
                        "product": "Credit card",
                        "narrative": "Dispute details."
                    }
                ]
            )
            mock_inst.last_execution_id = "exec-123"
            
            from app.schemas.ingestion import S3ImportResponse, S3SourceSummary, S3ImportLog
            mock_inst.import_rows = AsyncMock(return_value=S3ImportResponse(
                status="success",
                source=S3SourceSummary(label="Test Source"),
                scanned_rows=4,
                matched_rows=1,
                imported_rows=1,
                skipped_rows=0,
                logs=[S3ImportLog(level="success", message="Imported")]
            ))
            
            res = await import_complaints(filters, db=db, principal=principal)
            
            self.assertEqual(res.status, "success")
            mock_add_event.assert_called_once_with(
                db=db,
                complaint_id="cfpb-100",
                event_type="cfpb_import",
                actor="test-manager",
                payload={
                    "source_complaint_id": "100",
                    "channel": "web",
                    "date_received": "2026-01-10T00:00:00+00:00"
                }
            )



if __name__ == "__main__":
    unittest.main()
