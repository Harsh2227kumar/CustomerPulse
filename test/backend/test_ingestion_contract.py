import unittest
from datetime import UTC, datetime

from pydantic import ValidationError

from app.ingestion.cfpb_s3 import map_cfpb_csv_row
from app.schemas.ingestion import S3ComplaintImportFilters


class IngestionContractTests(unittest.TestCase):
    def test_accepts_normalized_csv_fields_and_parses_source_values(self) -> None:
        mapped = map_cfpb_csv_row(
            {
                "complaint_id": "case-1",
                "consumer_complaint_narrative": "A disputed transaction remains unresolved.",
                "submitted_via": "Email",
                "timely_response": "false",
                "date_received": "2026-05-20T14:10:00Z",
            }
        )

        self.assertIsNotNone(mapped)
        assert mapped is not None
        self.assertEqual(mapped["source_complaint_id"], "case-1")
        self.assertFalse(mapped["timely_response"])
        self.assertEqual(mapped["date_received"], datetime(2026, 5, 20, 14, 10, tzinfo=UTC))

    def test_rejects_reversed_import_date_range(self) -> None:
        with self.assertRaises(ValidationError):
            S3ComplaintImportFilters(
                date_received_min="2026-05-21",
                date_received_max="2026-05-20",
            )


if __name__ == "__main__":
    unittest.main()
