import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import email
from email.message import EmailMessage

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.constants import Role
from app.core.security import Principal, get_current_principal, require_roles
from app.db.session import get_db_session
from app.ingestion.email_intake import (
    EmailIntakeService,
    decode_mime_header,
    extract_body,
    extract_domain_from_sender,
)
from app.api.email_ingestion import router
from app.schemas.ingestion import EmailSyncResponse


class EmailIntakeTests(unittest.IsolatedAsyncioTestCase):
    def test_decode_mime_header(self) -> None:
        # Standard ASCII header
        self.assertEqual(decode_mime_header("Simple Subject"), "Simple Subject")
        # Encoded Subject UTF-8 Base64
        self.assertEqual(
            decode_mime_header("=?utf-8?B?VGVzdCBTdWJqZWN0?= "),
            "Test Subject"
        )
        # Empty header
        self.assertEqual(decode_mime_header(None), "")

    def test_extract_domain_from_sender(self) -> None:
        # Corporate domains
        self.assertEqual(extract_domain_from_sender("support@capitalone.com"), "capitalone.com")
        self.assertEqual(extract_domain_from_sender("Capital bank <alerts@capitalbank.co.uk>"), "capitalbank.co.uk")
        # Public domains (should filter out and return None)
        self.assertIsNone(extract_domain_from_sender("user@gmail.com"))
        self.assertIsNone(extract_domain_from_sender("Some Sender <user@yahoo.com>"))
        # Invalid email
        self.assertIsNone(extract_domain_from_sender("invalid_email"))

    def test_extract_body_plain_text(self) -> None:
        msg = EmailMessage()
        msg.set_content("This is plain text body.")
        self.assertEqual(extract_body(msg), "This is plain text body.")

    def test_extract_body_multipart(self) -> None:
        msg = EmailMessage()
        msg.set_content("This is plain text body.")
        msg.add_alternative("<p>This is HTML body.</p>", subtype="html")
        
        # Should prioritize plain text
        self.assertEqual(extract_body(msg), "This is plain text body.")

    def test_extract_body_html_fallback(self) -> None:
        msg = EmailMessage()
        # Create HTML only email
        msg.add_alternative("<p>Only HTML <b>body</b> exists.</p>", subtype="html")
        # HTML tag stripping
        self.assertEqual(extract_body(msg), "Only HTML body exists.")

    @patch("app.ingestion.email_intake.ProcessingService")
    @patch("imaplib.IMAP4_SSL")
    async def test_email_sync_success(self, mock_imap_class, mock_processing_service_class) -> None:
        # Mock IMAP client
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.search.return_value = ("OK", [b"12"])
        
        # Create a mock raw email
        msg = EmailMessage()
        msg["Subject"] = "=?utf-8?B?VGVzdCBFdmVudA==?="
        msg["From"] = "customer@corporate.com"
        msg["Message-ID"] = "<unique-message-id-123@mail.com>"
        msg["Date"] = "Tue, 30 Jun 2026 23:30:00 +0530"
        msg.set_content("Need help with fee charging.")
        
        mock_imap.fetch.return_value = ("OK", [(b"12 (RFC822)", msg.as_bytes())])
        mock_imap.store.return_value = ("OK", [b"12"])

        # Mock database session execution returning None (no duplicate found)
        mock_db = AsyncMock()
        mock_db_result = MagicMock()
        mock_db_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_db_result

        # Mock AI Pipeline processing
        mock_proc_service = MagicMock()
        mock_proc_service.process_complaint = AsyncMock()
        mock_processing_service_class.return_value = mock_proc_service

        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/customerpulse_test",
            bedrock_api_key="test-key",
            email_intake_enabled=True,
            email_intake_email="support.customerpulse@gmail.com",
            email_intake_password="app-password"
        )
        service = EmailIntakeService(settings)
        stats = await service.sync_emails(mock_db)

        # Assert stats
        self.assertEqual(stats["status"], "success")
        self.assertEqual(stats["scanned_emails"], 1)
        self.assertEqual(stats["imported_emails"], 1)
        self.assertEqual(stats["skipped_emails"], 0)
        self.assertEqual(stats["failed_emails"], 0)

        # Assert correct complaint_id deduplication key is used
        expected_complaint_id = "email_unique-message-id-123@mail.com"
        
        # Verify db checks for existing complaint ID
        mock_db.execute.assert_called_once()
        
        # Verify AI Processing is called with correct arguments
        mock_proc_service.process_complaint.assert_called_once()
        args, kwargs = mock_proc_service.process_complaint.call_args
        request = kwargs["complaint_request"]
        
        self.assertEqual(request.complaint_id, expected_complaint_id)
        self.assertEqual(request.channel, "email")
        self.assertEqual(request.company, "corporate.com")
        self.assertIn("Subject: Test Event", request.narrative)
        self.assertIn("Need help with fee charging.", request.narrative)

        # Verify message marked as Seen (read)
        mock_imap.store.assert_called_once_with(b"12", "+FLAGS", "\\Seen")

    @patch("app.ingestion.email_intake.ProcessingService")
    @patch("imaplib.IMAP4_SSL")
    async def test_email_sync_duplicate_skipped(self, mock_imap_class, mock_processing_service_class) -> None:
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.search.return_value = ("OK", [b"45"])
        
        msg = EmailMessage()
        msg["Message-ID"] = "<existing-message-id@mail.com>"
        msg.set_content("Hello.")
        mock_imap.fetch.return_value = ("OK", [(b"45 (RFC822)", msg.as_bytes())])
        mock_imap.store.return_value = ("OK", [b"45"])

        # Mock database session returning a mock complaint (duplicate exists)
        mock_db = AsyncMock()
        mock_db_result = MagicMock()
        mock_db_result.scalar_one_or_none.return_value = object()  # Represents existing complaint
        mock_db.execute.return_value = mock_db_result

        mock_proc_service = MagicMock()
        mock_processing_service_class.return_value = mock_proc_service

        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/customerpulse_test",
            bedrock_api_key="test-key",
            email_intake_enabled=True,
            email_intake_email="support.customerpulse@gmail.com",
            email_intake_password="app-password"
        )
        service = EmailIntakeService(settings)
        stats = await service.sync_emails(mock_db)

        # Assert skipped
        self.assertEqual(stats["scanned_emails"], 1)
        self.assertEqual(stats["imported_emails"], 0)
        self.assertEqual(stats["skipped_emails"], 1)

        # Verify process_complaint was NOT called
        mock_proc_service.process_complaint.assert_not_called()
        # Verify it was still marked Seen
        mock_imap.store.assert_called_once_with(b"45", "+FLAGS", "\\Seen")


class EmailSyncRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)

        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor="test-manager",
            role=Role.MANAGER,
        )
        
        self.settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/customerpulse_test",
            bedrock_api_key="test-key",
            email_intake_enabled=True,
            email_intake_email="support@pulse.com",
            email_intake_password="app-pass"
        )
        app.dependency_overrides[get_settings] = lambda: self.settings
        
        self.client = TestClient(app)


    @patch("app.api.email_ingestion.EmailIntakeService")
    def test_sync_endpoint_success(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.sync_emails = AsyncMock(return_value={
            "status": "success",
            "scanned_emails": 5,
            "imported_emails": 3,
            "skipped_emails": 2,
            "failed_emails": 0,
            "error_message": None
        })
        mock_service_class.return_value = mock_service

        response = self.client.post("/api/ingestion/email/sync")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["imported_emails"], 3)
        self.assertEqual(body["skipped_emails"], 2)



if __name__ == "__main__":
    unittest.main()
