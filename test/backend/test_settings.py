import unittest

from pydantic import ValidationError

from app.core.config import Settings


class SettingsTests(unittest.TestCase):
    def create_settings(self, **overrides: object) -> Settings:
        values: dict[str, object] = {
            "database_url": "postgresql://user:password@localhost:5432/customerpulse",
            "bedrock_api_key": "test-bedrock-key",
            "cors_origins": "http://localhost:5173, http://localhost:3000",
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_normalizes_database_url_and_cors_origins(self) -> None:
        settings = self.create_settings()

        self.assertEqual(
            settings.database_url,
            "postgresql+asyncpg://user:password@localhost:5432/customerpulse",
        )
        self.assertEqual(
            settings.parsed_cors_origins,
            ["http://localhost:5173", "http://localhost:3000"],
        )

    def test_marks_s3_import_configured_only_when_pair_is_provided(self) -> None:
        configured = self.create_settings(
            s3_bucket_name="complaints",
            cfpb_s3_key="raw/cfpb/complaints.csv",
        )

        self.assertTrue(configured.s3_import_configured)

        with self.assertRaises(ValidationError):
            self.create_settings(s3_bucket_name="complaints", cfpb_s3_key="")

    def test_rejects_missing_bedrock_credentials(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_settings(bedrock_api_key="")


if __name__ == "__main__":
    unittest.main()
