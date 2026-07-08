import asyncio
import email
import email.utils
from email.header import decode_header
import imaplib
import logging
import re
from datetime import datetime, timezone
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ProcessingTrigger
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintProcessRequest
from app.services.processing_service import ProcessingService

logger = logging.getLogger(__name__)


def decode_mime_header(header_value: str) -> str:
    if not header_value:
        return ""
    decoded_parts = []
    try:
        parts = decode_header(header_value)
        for part, encoding in parts:
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(encoding or "utf-8", errors="ignore"))
            else:
                decoded_parts.append(str(part))
    except Exception:
        return header_value.strip()
    return "".join(decoded_parts).strip()



def extract_domain_from_sender(sender: str) -> str | None:
    match = re.search(r'@([\w.-]+)', sender)
    if match:
        domain = match.group(1).strip()
        # Filter out common public email providers
        common_providers = {
            "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", 
            "aol.com", "icloud.com", "mail.com", "zoho.com", "yandex.com"
        }
        if domain.lower() not in common_providers:
            return domain
    return None


def extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        # First pass: try to find text/plain
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(part.get_content_charset() or "utf-8", errors="ignore").strip()
                except Exception:
                    pass
        
        # Second pass: fallback to text/html if plain text is not present
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                        # Strip HTML tags
                        text = re.sub(r'<[^>]+>', '', html)
                        # Clean multiple spaces and return
                        return re.sub(r'\s+', ' ', text).strip()
                except Exception:
                    pass
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                content = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore").strip()
                if content_type == "text/html":
                    text = re.sub(r'<[^>]+>', '', content)
                    return re.sub(r'\s+', ' ', text).strip()
                return content
        except Exception:
            pass
            
    return body


class EmailIntakeService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def sync_emails(self, db: AsyncSession) -> dict[str, int | str | None]:
        scanned_emails = 0
        imported_emails = 0
        skipped_emails = 0
        failed_emails = 0
        status = "success"
        error_message = None

        if not self.settings.email_intake_enabled:
            logger.info("Email intake is disabled. Skipping sync.")
            return {
                "status": "skipped",
                "scanned_emails": scanned_emails,
                "imported_emails": imported_emails,
                "skipped_emails": skipped_emails,
                "failed_emails": failed_emails,
                "error_message": "Email intake is disabled."
            }

        mail = None
        try:
            # Connect to IMAP Server
            mail = imaplib.IMAP4_SSL(
                self.settings.email_intake_imap_server,
                self.settings.email_intake_imap_port
            )
            mail.login(
                self.settings.email_intake_email,
                self.settings.email_intake_password
            )
            mail.select("inbox")

            # Search for UNSEEN emails
            search_status, search_data = mail.search(None, "UNSEEN")
            if search_status != "OK":
                logger.error("Failed to search UNSEEN emails: status=%s", search_status)
                return {
                    "status": "failed",
                    "scanned_emails": scanned_emails,
                    "imported_emails": imported_emails,
                    "skipped_emails": skipped_emails,
                    "failed_emails": failed_emails,
                    "error_message": f"Failed to search UNSEEN emails. IMAP status: {search_status}"
                }

            message_numbers = search_data[0].split()
            scanned_emails = len(message_numbers)

            processing_service = ProcessingService(self.settings)

            for num in message_numbers:
                try:
                    # Fetch email contents
                    fetch_status, fetch_data = mail.fetch(num, "(RFC822)")
                    if fetch_status != "OK" or not fetch_data or not isinstance(fetch_data, list):
                        logger.warning("Failed to fetch message number %s: status=%s", num, fetch_status)
                        failed_emails += 1
                        continue

                    # Parse message bytes
                    raw_email = fetch_data[0][1]
                    if not isinstance(raw_email, bytes):
                        logger.warning("Fetched content for message number %s is not bytes", num)
                        failed_emails += 1
                        continue
                        
                    msg = email.message_from_bytes(raw_email)

                    # Extract details
                    message_id = msg.get("Message-ID", "").strip()
                    # Fallback for message-id if missing
                    if not message_id:
                        message_id = f"fallback_{num.decode()}_{datetime.now(timezone.utc).timestamp()}"

                    # Construct unique complaint ID
                    # Trim/clean message-id characters to prevent illegal ID characters
                    clean_msg_id = re.sub(r'[^a-zA-Z0-9_\-@\.]', '', message_id)
                    complaint_id = f"email_{clean_msg_id}"[:128]

                    # Check for duplicates in database using complaint_id directly
                    stmt = select(Complaint).where(
                        or_(
                            Complaint.id == complaint_id,
                            Complaint.source_complaint_id == complaint_id
                        )
                    )
                    existing_result = await db.execute(stmt)
                    if existing_result.scalar_one_or_none():
                        logger.info("Complaint %s already exists in database. Skipping email ingestion.", complaint_id)
                        skipped_emails += 1
                        # Mark email read so we don't query it next time
                        mail.store(num, '+FLAGS', '\\Seen')
                        continue

                    # Decode subject, sender, date, body
                    subject = decode_mime_header(msg.get("Subject", "No Subject"))
                    sender = decode_mime_header(msg.get("From", "Unknown Sender"))
                    
                    date_str = msg.get("Date")
                    try:
                        if not date_str:
                            raise ValueError("Missing Date header")
                        date_received = email.utils.parsedate_to_datetime(date_str)
                    except Exception:
                        date_received = datetime.now(timezone.utc)

                    body = extract_body(msg)
                    if not body:
                        body = "[No body content found in the email]"

                    # Formulate complaint narrative
                    narrative = f"Subject: {subject}\nFrom: {sender}\nDate: {date_received.isoformat()}\n\n{body}"

                    # Auto-detect company domain
                    company = extract_domain_from_sender(sender)

                    # Instantiate ComplaintProcessRequest
                    complaint_request = ComplaintProcessRequest(
                        complaint_id=complaint_id,
                        narrative=narrative,
                        channel="email",
                        company=company,
                        date_received=date_received
                    )

                    # Process complaint using ProcessingService
                    await processing_service.process_complaint(
                        db=db,
                        complaint_request=complaint_request,
                        trigger=ProcessingTrigger.EMAIL_INTAKE,
                        initiated_by="email_worker"
                    )

                    imported_emails += 1

                    # Mark email as read
                    mail.store(num, '+FLAGS', '\\Seen')

                except Exception as message_exc:
                    logger.exception("Failed to process message number %s: %s", num, message_exc)
                    failed_emails += 1

            processing_service.close()

        except Exception as conn_exc:
            logger.exception("Email intake IMAP sync encountered a connection error: %s", conn_exc)
            status = "failed"
            error_message = str(conn_exc)

        finally:
            if mail:
                try:
                    mail.close()
                except Exception:
                    pass
                try:
                    mail.logout()
                except Exception:
                    pass

        return {
            "status": status,
            "scanned_emails": scanned_emails,
            "imported_emails": imported_emails,
            "skipped_emails": skipped_emails,
            "failed_emails": failed_emails,
            "error_message": error_message
        }
