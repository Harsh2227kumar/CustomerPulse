import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.compliance.models import RegulatoryDocumentCreate, RegulatoryKnowledgeSearchRequest
from app.compliance.rag.chunker import chunk_markdown_pages
from app.compliance.rag.document_converter import convert_document_to_markdown, split_markdown_pages
from app.compliance.service import (
    ComplianceKnowledgeBaseService,
    RegulatoryDocumentConflictError,
)
from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session
from app.main import app

BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def document_record(**overrides):
    values = {
        "id": "document-1",
        "regulator": "RBI",
        "document_title": "RBI Master Direction",
        "document_type": "pdf",
        "source_filename": "rbi_master_direction.pdf",
        "source_url": "https://example.test/rbi_master_direction.pdf",
        "storage_path": "storage/regulations/RBI/2026/original/rbi_master_direction.pdf",
        "version": "2026.1",
        "effective_from": BASE_DATE,
        "effective_to": None,
        "status": "uploaded",
        "uploaded_by": "manager-1",
        "uploaded_at": BASE_DATE,
        "created_at": BASE_DATE,
        "updated_at": BASE_DATE,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def document_payload(**overrides):
    values = {
        "regulator": "RBI",
        "document_title": "RBI Master Direction",
        "document_type": "pdf",
        "source_filename": "rbi_master_direction.pdf",
        "source_url": "https://example.test/rbi_master_direction.pdf",
        "storage_path": "storage/regulations/RBI/2026/original/rbi_master_direction.pdf",
        "version": "2026.1",
        "effective_from": BASE_DATE,
        "effective_to": None,
        "status": "uploaded",
    }
    values.update(overrides)
    return RegulatoryDocumentCreate(**values)




def page_record(**overrides):
    values = {
        "id": "page-1",
        "document_id": "document-1",
        "page_number": 1,
        "raw_text": "# Section 1\nComplaint handling text.",
        "cleaned_text": "# Section 1\nComplaint handling text.",
        "markdown_text": "# Section 1\nComplaint handling text.",
        "extraction_status": "extracted",
        "created_at": BASE_DATE,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def markdown_record(**overrides):
    values = {
        "id": "markdown-1",
        "document_id": "document-1",
        "markdown_path": "storage/regulations/RBI/2026/markdown/rbi_master_direction.md",
        "conversion_tool": "plain-text",
        "conversion_status": "converted",
        "conversion_warnings": [],
        "created_at": BASE_DATE,
        "updated_at": BASE_DATE,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def settings_stub(**overrides):
    values = {
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_local_files_only": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def chunk_record(**overrides):
    values = {
        "id": "chunk-1",
        "document_id": "document-1",
        "chunk_index": 0,
        "regulator": "RBI",
        "domain": "unknown",
        "section_reference": "Section 1",
        "page_start": 1,
        "page_end": 1,
        "chunk_text": "# Section 1\nComplaint handling text.",
        "summary": None,
        "keywords": ["complaint", "handling"],
        "effective_from": BASE_DATE,
        "effective_to": None,
        "status": "draft",
        "embedding_model": None,
        "created_at": BASE_DATE,
        "updated_at": BASE_DATE,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class RegulatoryDocumentConverterTests(unittest.TestCase):
    def test_txt_conversion_and_page_split(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "guideline.txt"
            source.write_text("Section 1\nComplaint handling must be tracked.", encoding="utf-8")

            converted = convert_document_to_markdown(source)
            pages = split_markdown_pages(converted.markdown)

        self.assertEqual(converted.conversion_tool, "plain-text")
        self.assertEqual(len(pages), 1)
        self.assertIn("Complaint handling", pages[0])

    def test_chunker_preserves_heading_and_keywords(self) -> None:
        chunks = chunk_markdown_pages(["# Section 1\nComplaint handling must be tracked.\n\nEvidence must be stored."])

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].section_reference, "Section 1")
        self.assertIn("complaint", chunks[0].keywords)

    def test_pdf_conversion_preserves_page_boundaries(self) -> None:
        from reportlab.pdfgen import canvas

        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "guideline.pdf"
            pdf = canvas.Canvas(str(source))
            pdf.drawString(72, 720, "Page one complaint handling text.")
            pdf.showPage()
            pdf.drawString(72, 720, "Page two evidence storage text.")
            pdf.save()

            converted = convert_document_to_markdown(source)
            pages = split_markdown_pages(converted.markdown)

        self.assertEqual(converted.conversion_tool, "pymupdf-page-text")
        self.assertEqual(len(pages), 2)
        self.assertIn("Page one", pages[0])
        self.assertIn("Page two", pages[1])
    def test_pdf_converter_dependency_is_available(self) -> None:
        import pymupdf4llm

        self.assertTrue(hasattr(pymupdf4llm, "to_markdown"))

    def test_docx_converter_dependency_is_available(self) -> None:
        import mammoth

        self.assertTrue(hasattr(mammoth, "convert_to_markdown"))

class RegulatoryDocumentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_document_persists_metadata_and_actor(self) -> None:
        repository = SimpleNamespace(
            get_regulatory_document_by_identity=AsyncMock(return_value=None),
            create_regulatory_document=AsyncMock(return_value=document_record(uploaded_by="admin-1")),
        )
        service = ComplianceKnowledgeBaseService(repository)

        result = await service.create_regulatory_document(
            object(),
            document_payload(),
            uploaded_by="admin-1",
        )

        repository.create_regulatory_document.assert_awaited_once()
        values = repository.create_regulatory_document.await_args.args[1]
        self.assertEqual(values["regulator"], "RBI")
        self.assertEqual(values["document_type"], "pdf")
        self.assertEqual(values["uploaded_by"], "admin-1")
        self.assertEqual(result.document_title, "RBI Master Direction")

    async def test_create_document_rejects_duplicate_version(self) -> None:
        repository = SimpleNamespace(
            get_regulatory_document_by_identity=AsyncMock(return_value=document_record()),
        )
        service = ComplianceKnowledgeBaseService(repository)

        with self.assertRaises(RegulatoryDocumentConflictError):
            await service.create_regulatory_document(object(), document_payload())

    async def test_mark_document_processing_updates_status(self) -> None:
        record = document_record()
        repository = SimpleNamespace(
            get_regulatory_document=AsyncMock(return_value=record),
            update_regulatory_document_status=AsyncMock(
                return_value=document_record(status="processing")
            ),
        )
        service = ComplianceKnowledgeBaseService(repository)

        result = await service.mark_regulatory_document_processing(object(), "document-1")

        repository.update_regulatory_document_status.assert_awaited_once()
        self.assertEqual(repository.update_regulatory_document_status.await_args.args[2], "processing")
        self.assertEqual(result.status, "processing")

    async def test_process_txt_document_creates_pages_markdown_and_chunks(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "original" / "rbi_guideline.txt"
            source.parent.mkdir(parents=True)
            source.write_text("# Section 1\nComplaint handling must be tracked.\n\nEvidence must be stored.", encoding="utf-8")
            record = document_record(storage_path=str(source), document_type="txt")
            repository = SimpleNamespace(
                get_regulatory_document=AsyncMock(return_value=record),
                update_regulatory_document_status=AsyncMock(return_value=record),
                delete_regulatory_document_outputs=AsyncMock(return_value=None),
                create_regulatory_pages=AsyncMock(return_value=[page_record()]),
                create_regulatory_markdown_file=AsyncMock(return_value=markdown_record()),
                create_regulatory_chunks=AsyncMock(return_value=[chunk_record()]),
                commit_processing_outputs=AsyncMock(return_value=None),
            )
            service = ComplianceKnowledgeBaseService(repository)

            result = await service.process_regulatory_document(object(), "document-1")

        self.assertEqual(result.document.status, "indexed")
        self.assertEqual(result.pages_created, 1)
        self.assertEqual(result.chunks_created, 1)
        repository.delete_regulatory_document_outputs.assert_awaited_once()
        self.assertEqual(repository.delete_regulatory_document_outputs.await_args.args[1], "document-1")
        repository.create_regulatory_pages.assert_awaited_once()
        repository.create_regulatory_markdown_file.assert_awaited_once()
        repository.create_regulatory_chunks.assert_awaited_once()

    async def test_embedding_backfill_updates_chunks_with_existing_embedding_service_contract(self) -> None:
        chunk = chunk_record()
        repository = SimpleNamespace(
            list_chunks_for_embedding=AsyncMock(return_value=[chunk]),
            commit_chunk_embeddings=AsyncMock(return_value=None),
        )
        service = ComplianceKnowledgeBaseService(repository)

        with patch("app.compliance.service.EmbeddingService") as embedding_cls:
            embedding_cls.return_value.embed_many = AsyncMock(return_value=[[0.1] * 384])
            result = await service.embed_regulatory_chunks(
                object(),
                settings=settings_stub(),
                document_id="document-1",
                limit=25,
            )

        self.assertEqual(result.embedded_count, 1)
        self.assertEqual(chunk.embedding_model, "all-MiniLM-L6-v2")
        self.assertEqual(len(chunk.embedding), 384)
        repository.commit_chunk_embeddings.assert_awaited_once()

    async def test_regulatory_search_maps_similarity_results_with_document_title(self) -> None:
        repository = SimpleNamespace(
            search_regulatory_chunks=AsyncMock(
                return_value=[(chunk_record(), document_record(), 0.87654)]
            ),
        )
        service = ComplianceKnowledgeBaseService(repository)
        payload = RegulatoryKnowledgeSearchRequest(
            query="complaint handling evidence",
            regulator="RBI",
            domain="unknown",
            limit=3,
            min_similarity=0.5,
        )

        with patch("app.compliance.service.EmbeddingService") as embedding_cls:
            embedding_cls.return_value.embed_text = AsyncMock(return_value=[0.1] * 384)
            result = await service.search_regulatory_knowledge(
                object(),
                payload,
                settings=settings_stub(),
            )

        self.assertEqual(result.embedding_model, "all-MiniLM-L6-v2")
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].document_title, "RBI Master Direction")
        self.assertEqual(result.results[0].similarity_score, 0.8765)
        repository.search_regulatory_chunks.assert_awaited_once()


class RegulatoryDocumentEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor="admin-1",
            role=Role.ADMIN,
        )

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_agent_cannot_access_regulatory_document_create_endpoint(self) -> None:
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor="agent-1",
            role=Role.AGENT,
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/compliance/regulatory-documents",
                json=document_payload().model_dump(mode="json"),
            )

        self.assertEqual(response.status_code, 403)

    async def test_upload_regulatory_document_endpoint_accepts_file_metadata(self) -> None:
        response_model = ComplianceKnowledgeBaseService()._regulatory_document_to_read(
            document_record(
                uploaded_by="admin-1",
                source_filename="guideline.txt",
                storage_path="storage/regulations/RBI/2026/original/guideline.txt",
                document_type="txt",
            )
        )
        service = SimpleNamespace(
            create_uploaded_regulatory_document=AsyncMock(return_value=response_model),
        )

        with patch("app.compliance.router.ComplianceKnowledgeBaseService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/compliance/regulatory-documents/upload",
                    data={
                        "regulator": "RBI",
                        "document_title": "RBI Upload Guideline",
                        "version": "2026.2",
                        "effective_from": "2026-01-01T00:00:00+00:00",
                    },
                    files={"file": ("guideline.txt", b"# Section 1\nComplaint evidence.", "text/plain")},
                )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["source_filename"], "guideline.txt")
        service.create_uploaded_regulatory_document.assert_awaited_once()
        kwargs = service.create_uploaded_regulatory_document.await_args.kwargs
        self.assertEqual(kwargs["uploaded_by"], "admin-1")
        self.assertEqual(kwargs["source_filename"], "guideline.txt")
        self.assertIn(b"Complaint evidence", kwargs["file_bytes"])

    async def test_create_regulatory_document_endpoint_returns_created_record(self) -> None:
        response_model = ComplianceKnowledgeBaseService()._regulatory_document_to_read(
            document_record()
        )
        service = SimpleNamespace(
            create_regulatory_document=AsyncMock(return_value=response_model),
        )

        with patch("app.compliance.router.ComplianceKnowledgeBaseService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/compliance/regulatory-documents",
                    json=document_payload().model_dump(mode="json"),
                )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["document_title"], "RBI Master Direction")
        service.create_regulatory_document.assert_awaited_once()
        self.assertEqual(service.create_regulatory_document.await_args.kwargs["uploaded_by"], "admin-1")

    async def test_process_regulatory_document_endpoint_marks_processing(self) -> None:
        response_model = {
            "document": ComplianceKnowledgeBaseService()._regulatory_document_to_read(
                document_record(status="indexed")
            ),
            "markdown_file": ComplianceKnowledgeBaseService()._markdown_file_to_read(markdown_record()),
            "pages_created": 1,
            "chunks_created": 1,
            "warnings": [],
        }
        service = SimpleNamespace(
            process_regulatory_document=AsyncMock(return_value=response_model),
        )

        with patch("app.compliance.router.ComplianceKnowledgeBaseService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/compliance/regulatory-documents/document-1/process")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["document"]["status"], "indexed")
        self.assertEqual(response.json()["chunks_created"], 1)

    async def test_regulatory_search_endpoint_returns_results(self) -> None:
        response_model = {
            "query": "complaint handling",
            "embedding_model": "all-MiniLM-L6-v2",
            "results": [
                {
                    "chunk_id": "chunk-1",
                    "document_id": "document-1",
                    "document_title": "RBI Master Direction",
                    "regulator": "RBI",
                    "domain": "unknown",
                    "section_reference": "Section 1",
                    "page_start": 1,
                    "page_end": 1,
                    "similarity_score": 0.87,
                    "chunk_text": "Complaint handling text.",
                    "keywords": ["complaint"],
                    "effective_from": BASE_DATE.isoformat(),
                    "effective_to": None,
                }
            ],
        }
        service = SimpleNamespace(
            search_regulatory_knowledge=AsyncMock(return_value=response_model),
        )

        with patch("app.compliance.router.ComplianceKnowledgeBaseService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/compliance/regulatory-search",
                    json={"query": "complaint handling", "regulator": "RBI"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["chunk_id"], "chunk-1")


if __name__ == "__main__":
    unittest.main()
