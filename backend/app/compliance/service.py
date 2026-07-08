from datetime import datetime, timezone
from pathlib import Path
import re

from sqlalchemy.exc import SQLAlchemyError
from app.compliance.models import (
    ComplianceEvidenceRead,
    ComplianceEvidenceStoreRequest,
    ComplianceResult,
    ComplianceRuleDefinitionCreate,
    ComplianceRuleDefinitionListResponse,
    ComplianceRuleDefinitionRead,
    ComplianceRuleDefinitionUpdate,
    ReasonCodeCreate,
    ReasonCodeListResponse,
    ReasonCodeRead,
    RegulatoryDocumentCreate,
    RegulatoryDocumentListResponse,
    RegulatoryDocumentMarkdownFileRead,
    RegulatoryDocumentPageRead,
    RegulatoryChunkEmbeddingBackfillResult,
    RegulatoryDocumentProcessResult,
    RegulatoryDocumentRead,
    RegulatoryDocumentStatus,
    RegulatoryKnowledgeChunkRead,
    RegulatoryKnowledgeChunkListResponse,
    RegulatoryDocumentReviewRequest,
    RegulatoryDocumentReviewResult,
    RegulatoryKnowledgeSearchRequest,
    RegulatoryKnowledgeSearchResponse,
    RegulatoryKnowledgeSearchResult,
)
from app.compliance.rag.chunker import chunk_markdown_pages
from app.compliance.rag.document_converter import (
    RegulatoryDocumentConversionError,
    clean_extracted_text,
    convert_document_to_markdown,
    split_markdown_pages,
)
from app.compliance.repository import ComplianceEvidenceRepository, ComplianceKnowledgeBaseRepository
from app.services.embedding_service import EmbeddingService
from app.compliance.storage_models import (
    ComplianceEvidenceRecord,
    ComplianceRuleRecord,
    ReasonCodeRecord,
    RegulatoryDocumentMarkdownFileRecord,
    RegulatoryDocumentPageRecord,
    RegulatoryDocumentRecord,
    RegulatoryKnowledgeChunkRecord,
)


class ComplianceEvidenceNotFoundError(Exception):
    pass


class ComplianceRuleNotFoundError(Exception):
    pass


class ComplianceRuleVersionConflictError(Exception):
    pass


class ReasonCodeConflictError(Exception):
    pass


class RegulatoryDocumentConflictError(Exception):
    pass


class RegulatoryDocumentNotFoundError(Exception):
    pass


class RegulatoryDocumentProcessingError(Exception):
    pass


class ComplianceEvidenceService:
    def __init__(self, repository: ComplianceEvidenceRepository | None = None) -> None:
        self.repository = repository or ComplianceEvidenceRepository()

    async def store_result(
        self,
        db,
        result: ComplianceResult,
        notes: str | None = None,
    ) -> ComplianceEvidenceRead:
        values = self._build_record_values(result, notes)
        record = await self.repository.create_record(db, values)
        return self._to_read(record)

    async def store_request(
        self,
        db,
        payload: ComplianceEvidenceStoreRequest,
    ) -> ComplianceEvidenceRead:
        return await self.store_result(db, payload.result, payload.notes)

    async def get_record(
        self,
        db,
        record_id: str,
    ) -> ComplianceEvidenceRead:
        record = await self.repository.get_record(db, record_id)
        if record is None:
            raise ComplianceEvidenceNotFoundError(record_id)
        return self._to_read(record)

    async def list_records(
        self,
        db,
        limit: int,
        offset: int,
        complaint_id: str | None = None,
        risk_level: str | None = None,
        regulatory_flag: bool | None = None,
        product: str | None = None,
        company: str | None = None,
        channel: str | None = None,
    ) -> tuple[list[ComplianceEvidenceRead], int]:
        records, count = await self.repository.list_records(
            db,
            limit=limit,
            offset=offset,
            complaint_id=complaint_id,
            risk_level=risk_level,
            regulatory_flag=regulatory_flag,
            product=product,
            company=company,
            channel=channel,
        )
        return [self._to_read(record) for record in records], count

    async def delete_record(
        self,
        db,
        record_id: str,
    ) -> None:
        record = await self.repository.get_record(db, record_id)
        if record is None:
            raise ComplianceEvidenceNotFoundError(record_id)
        await self.repository.delete_record(db, record)

    def _build_record_values(self, result: ComplianceResult, notes: str | None) -> dict:
        triggered_rules = [rule.model_dump(mode="json") for rule in result.triggered_rules]
        required_actions = [action.model_dump(mode="json") for action in result.required_actions]
        evidence_snippets = [
            snippet
            for rule in result.triggered_rules
            for snippet in rule.evidence
        ]
        required_action = required_actions[0]["action_type"] if required_actions else None
        regulatory_flag = self._has_regulatory_flag(result)

        return {
            "complaint_id": result.complaint_id,
            "source_complaint_id": result.source_complaint_id,
            "risk_level": result.compliance_risk_level,
            "required_action": required_action,
            "regulatory_flag": regulatory_flag,
            "regulatory_interpretation": result.sla_reading.regulatory_interpretation,
            "triggered_rules": triggered_rules,
            "evidence_snippets": evidence_snippets,
            "required_actions": required_actions,
            "reason_codes": result.reason_codes,
            "result_payload": result.model_dump(mode="json"),
            "notes": notes,
            "evaluated_at": result.evaluated_at,
        }

    def _has_regulatory_flag(self, result: ComplianceResult) -> bool:
        if result.sla_reading.regulatory_interpretation != "no_regulatory_sla_exception":
            return True
        return any(action.action_type == "notify_regulator" for action in result.required_actions)

    def _to_read(self, record: ComplianceEvidenceRecord) -> ComplianceEvidenceRead:
        return ComplianceEvidenceRead(
            id=record.id,
            complaint_id=record.complaint_id,
            source_complaint_id=record.source_complaint_id,
            risk_level=record.risk_level,
            required_action=record.required_action,
            regulatory_flag=record.regulatory_flag,
            regulatory_interpretation=record.regulatory_interpretation,
            triggered_rules=record.triggered_rules,
            evidence_snippets=record.evidence_snippets,
            required_actions=record.required_actions,
            reason_codes=record.reason_codes,
            result=ComplianceResult.model_validate(record.result_payload),
            notes=record.notes,
            evaluated_at=record.evaluated_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ComplianceKnowledgeBaseService:
    def __init__(self, repository: ComplianceKnowledgeBaseRepository | None = None) -> None:
        self.repository = repository or ComplianceKnowledgeBaseRepository()

    async def create_rule(self, db, payload: ComplianceRuleDefinitionCreate) -> ComplianceRuleDefinitionRead:
        existing = await self.repository.get_rule_by_identity(db, payload.rule_id, payload.version)
        if existing is not None:
            raise ComplianceRuleVersionConflictError(payload.rule_id)
        record = await self.repository.create_rule(db, payload.model_dump(mode="python"))
        return self._rule_to_read(record)

    async def update_rule_version(
        self,
        db,
        record_id: str,
        payload: ComplianceRuleDefinitionUpdate,
    ) -> ComplianceRuleDefinitionRead:
        previous = await self.repository.get_rule(db, record_id)
        if previous is None:
            raise ComplianceRuleNotFoundError(record_id)
        if payload.rule_id == previous.rule_id and payload.version == previous.version:
            raise ComplianceRuleVersionConflictError(payload.rule_id)
        existing = await self.repository.get_rule_by_identity(db, payload.rule_id, payload.version)
        if existing is not None:
            raise ComplianceRuleVersionConflictError(payload.rule_id)
        record = await self.repository.create_rule_version(db, previous, payload.model_dump(mode="python"))
        return self._rule_to_read(record)

    async def get_rule(self, db, record_id: str) -> ComplianceRuleDefinitionRead:
        record = await self.repository.get_rule(db, record_id)
        if record is None:
            raise ComplianceRuleNotFoundError(record_id)
        return self._rule_to_read(record)

    async def list_rules(
        self,
        db,
        limit: int,
        offset: int,
        regulator: str | None = None,
        domain: str | None = None,
        status: str | None = None,
        active_on: datetime | None = None,
    ) -> ComplianceRuleDefinitionListResponse:
        records, count = await self.repository.list_rules(
            db,
            limit=limit,
            offset=offset,
            regulator=regulator,
            domain=domain,
            status=status,
            active_on=active_on,
        )
        return ComplianceRuleDefinitionListResponse(
            items=[self._rule_to_read(record) for record in records],
            limit=limit,
            offset=offset,
            count=count,
        )

    async def load_active_rules(
        self,
        db,
        regulator: str | None = None,
        domain: str | None = None,
        active_on: datetime | None = None,
    ) -> list[ComplianceRuleDefinitionRead]:
        response = await self.list_rules(
            db,
            limit=500,
            offset=0,
            regulator=regulator,
            domain=domain,
            active_on=active_on or datetime.now(timezone.utc),
        )
        return response.items

    async def create_reason_code(self, db, payload: ReasonCodeCreate) -> ReasonCodeRead:
        existing = await self.repository.get_reason_code(db, payload.code)
        if existing is not None:
            raise ReasonCodeConflictError(payload.code)
        record = await self.repository.create_reason_code(db, payload.model_dump(mode="python"))
        return self._reason_code_to_read(record)

    async def list_reason_codes(
        self,
        db,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> ReasonCodeListResponse:
        records, count = await self.repository.list_reason_codes(db, limit=limit, offset=offset, status=status)
        return ReasonCodeListResponse(
            items=[self._reason_code_to_read(record) for record in records],
            limit=limit,
            offset=offset,
            count=count,
        )

    def _rule_to_read(self, record: ComplianceRuleRecord) -> ComplianceRuleDefinitionRead:
        return ComplianceRuleDefinitionRead(
            id=record.id,
            rule_id=record.rule_id,
            rule_name=record.rule_name,
            regulator=record.regulator,
            domain=record.domain,
            version=record.version,
            status=record.status,
            description=record.description,
            evaluation_type=record.evaluation_type,
            severity=record.severity,
            reason_code=record.reason_code,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            supersedes_rule_record_id=record.supersedes_rule_record_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _reason_code_to_read(self, record: ReasonCodeRecord) -> ReasonCodeRead:
        return ReasonCodeRead(
            id=record.id,
            code=record.code,
            description=record.description,
            severity=record.severity,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create_uploaded_regulatory_document(
        self,
        db,
        *,
        regulator: str,
        document_title: str,
        version: str,
        source_filename: str,
        file_bytes: bytes,
        effective_from: datetime | None = None,
        effective_to: datetime | None = None,
        uploaded_by: str | None = None,
    ) -> RegulatoryDocumentRead:
        safe_name = self._safe_filename(source_filename)
        suffix = Path(safe_name).suffix.lower()
        document_type = self._document_type_from_suffix(suffix)
        year = (effective_from or datetime.now(timezone.utc)).year
        storage_path = (
            Path("storage")
            / "regulations"
            / regulator
            / str(year)
            / "original"
            / safe_name
        )
        absolute_path = self._resolve_storage_path(str(storage_path))
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(file_bytes)
        payload = RegulatoryDocumentCreate(
            regulator=regulator,
            document_title=document_title,
            document_type=document_type,
            source_filename=safe_name,
            source_url=None,
            storage_path=str(storage_path),
            version=version,
            effective_from=effective_from,
            effective_to=effective_to,
            uploaded_by=uploaded_by,
        )
        return await self.create_regulatory_document(db, payload, uploaded_by=uploaded_by)

    async def create_regulatory_document(
        self,
        db,
        payload: RegulatoryDocumentCreate,
        *,
        uploaded_by: str | None = None,
    ) -> RegulatoryDocumentRead:
        existing = await self.repository.get_regulatory_document_by_identity(
            db,
            payload.regulator,
            payload.document_title,
            payload.version,
        )
        if existing is not None:
            raise RegulatoryDocumentConflictError(payload.document_title)
        values = payload.model_dump(mode="python")
        if uploaded_by and not values.get("uploaded_by"):
            values["uploaded_by"] = uploaded_by
        record = await self.repository.create_regulatory_document(db, values)
        return self._regulatory_document_to_read(record)

    async def get_regulatory_document(self, db, document_id: str) -> RegulatoryDocumentRead:
        record = await self.repository.get_regulatory_document(db, document_id)
        if record is None:
            raise RegulatoryDocumentNotFoundError(document_id)
        return self._regulatory_document_to_read(record)

    async def list_regulatory_documents(
        self,
        db,
        limit: int,
        offset: int,
        regulator: str | None = None,
        status: str | None = None,
        document_type: str | None = None,
    ) -> RegulatoryDocumentListResponse:
        records, count = await self.repository.list_regulatory_documents(
            db,
            limit=limit,
            offset=offset,
            regulator=regulator,
            status=status,
            document_type=document_type,
        )
        return RegulatoryDocumentListResponse(
            items=[self._regulatory_document_to_read(record) for record in records],
            limit=limit,
            offset=offset,
            count=count,
        )

    async def mark_regulatory_document_processing(
        self,
        db,
        document_id: str,
    ) -> RegulatoryDocumentRead:
        record = await self.repository.get_regulatory_document(db, document_id)
        if record is None:
            raise RegulatoryDocumentNotFoundError(document_id)
        updated = await self.repository.update_regulatory_document_status(
            db,
            record,
            RegulatoryDocumentStatus.PROCESSING.value,
        )
        return self._regulatory_document_to_read(updated)

    async def process_regulatory_document(
        self,
        db,
        document_id: str,
    ) -> RegulatoryDocumentProcessResult:
        record = await self.repository.get_regulatory_document(db, document_id)
        if record is None:
            raise RegulatoryDocumentNotFoundError(document_id)

        await self.repository.update_regulatory_document_status(
            db,
            record,
            RegulatoryDocumentStatus.PROCESSING.value,
        )

        try:
            source_path = self._resolve_storage_path(record.storage_path)
            converted = convert_document_to_markdown(source_path)
            pages = split_markdown_pages(converted.markdown)
            if not pages:
                raise RegulatoryDocumentProcessingError("Converted document did not contain extractable text.")

            markdown_path = self._markdown_path(source_path, record)
            await self.repository.delete_regulatory_document_outputs(db, record.id)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(converted.markdown, encoding="utf-8")

            page_records = await self.repository.create_regulatory_pages(
                db,
                [
                    {
                        "document_id": record.id,
                        "page_number": index,
                        "raw_text": page,
                        "cleaned_text": clean_extracted_text(page),
                        "markdown_text": page,
                        "extraction_status": "extracted",
                    }
                    for index, page in enumerate(pages, start=1)
                ],
            )
            markdown_record = await self.repository.create_regulatory_markdown_file(
                db,
                {
                    "document_id": record.id,
                    "markdown_path": str(markdown_path),
                    "conversion_tool": converted.conversion_tool,
                    "conversion_status": "converted",
                    "conversion_warnings": converted.warnings,
                },
            )
            chunks = chunk_markdown_pages(pages)
            chunk_records = await self.repository.create_regulatory_chunks(
                db,
                [
                    {
                        "document_id": record.id,
                        "chunk_index": chunk.chunk_index,
                        "regulator": record.regulator,
                        "domain": "unknown",
                        "section_reference": chunk.section_reference,
                        "page_start": chunk.page_start,
                        "page_end": chunk.page_end,
                        "chunk_text": chunk.chunk_text,
                        "summary": None,
                        "keywords": chunk.keywords,
                        "effective_from": record.effective_from,
                        "effective_to": record.effective_to,
                        "status": "draft",
                        "embedding_model": None,
                        "embedding": None,
                    }
                    for chunk in chunks
                ],
            )
            record.status = RegulatoryDocumentStatus.INDEXED.value
            result = RegulatoryDocumentProcessResult(
                document=self._regulatory_document_to_read(record),
                markdown_file=self._markdown_file_to_read(markdown_record),
                pages_created=len(page_records),
                chunks_created=len(chunk_records),
                warnings=converted.warnings,
            )
            await self.repository.commit_processing_outputs(db)
            return result
        except (OSError, RegulatoryDocumentConversionError, RegulatoryDocumentProcessingError) as exc:
            await self.repository.update_regulatory_document_status(
                db,
                record,
                RegulatoryDocumentStatus.FAILED.value,
            )
            raise RegulatoryDocumentProcessingError(str(exc)) from exc
        except SQLAlchemyError as exc:
            await db.rollback()
            failed_record = await self.repository.get_regulatory_document(db, document_id)
            if failed_record is not None:
                await self.repository.update_regulatory_document_status(
                    db,
                    failed_record,
                    RegulatoryDocumentStatus.FAILED.value,
                )
            raise RegulatoryDocumentProcessingError(
                "Unable to persist regulatory document processing outputs. "
                "Retry processing after the backend has restarted with a backend-only reload directory."
            ) from exc


    async def list_regulatory_document_chunks(
        self,
        db,
        document_id: str,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> RegulatoryKnowledgeChunkListResponse:
        document = await self.repository.get_regulatory_document(db, document_id)
        if document is None:
            raise RegulatoryDocumentNotFoundError(document_id)
        records, count = await self.repository.list_regulatory_chunks(
            db,
            document_id=document_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        return RegulatoryKnowledgeChunkListResponse(
            items=[self._chunk_to_read(record) for record in records],
            limit=limit,
            offset=offset,
            count=count,
        )

    async def review_regulatory_document(
        self,
        db,
        document_id: str,
        payload: RegulatoryDocumentReviewRequest,
    ) -> RegulatoryDocumentReviewResult:
        document = await self.repository.get_regulatory_document(db, document_id)
        if document is None:
            raise RegulatoryDocumentNotFoundError(document_id)
        if payload.action == "activate":
            document_status = RegulatoryDocumentStatus.ACTIVE.value
            chunk_status = "active"
        elif payload.action == "archive":
            document_status = RegulatoryDocumentStatus.ARCHIVED.value
            chunk_status = "archived"
        else:
            document_status = RegulatoryDocumentStatus.REVIEW_REQUIRED.value
            chunk_status = "draft"

        chunks_updated = await self.repository.update_regulatory_chunk_statuses(
            db,
            document_id=document_id,
            status=chunk_status,
        )
        document.status = document_status
        await db.commit()
        await db.refresh(document)
        return RegulatoryDocumentReviewResult(
            document=self._regulatory_document_to_read(document),
            chunks_updated=chunks_updated,
            chunk_status=chunk_status,
            notes=payload.notes,
        )

    async def embed_regulatory_chunks(
        self,
        db,
        *,
        settings,
        document_id: str | None = None,
        limit: int = 100,
    ) -> RegulatoryChunkEmbeddingBackfillResult:
        chunks = await self.repository.list_chunks_for_embedding(
            db,
            document_id=document_id,
            limit=limit,
        )
        if not chunks:
            return RegulatoryChunkEmbeddingBackfillResult(
                document_id=document_id,
                embedding_model=settings.embedding_model,
                embedded_count=0,
                skipped_count=0,
            )
        embeddings = await EmbeddingService(
            settings.embedding_model,
            local_files_only=settings.embedding_local_files_only,
        ).embed_many([chunk.chunk_text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding
            chunk.embedding_model = settings.embedding_model
        await self.repository.commit_chunk_embeddings(db)
        return RegulatoryChunkEmbeddingBackfillResult(
            document_id=document_id,
            embedding_model=settings.embedding_model,
            embedded_count=len(chunks),
            skipped_count=0,
        )

    async def search_regulatory_knowledge(
        self,
        db,
        payload: RegulatoryKnowledgeSearchRequest,
        *,
        settings,
    ) -> RegulatoryKnowledgeSearchResponse:
        query_embedding = await EmbeddingService(
            settings.embedding_model,
            local_files_only=settings.embedding_local_files_only,
        ).embed_text(payload.query)
        rows = await self.repository.search_regulatory_chunks(
            db,
            query_embedding=query_embedding,
            limit=payload.limit,
            min_similarity=payload.min_similarity,
            regulator=payload.regulator,
            domain=payload.domain,
            status=payload.status,
            effective_on=payload.effective_on,
        )
        return RegulatoryKnowledgeSearchResponse(
            query=payload.query,
            embedding_model=settings.embedding_model,
            results=[
                RegulatoryKnowledgeSearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=document.document_title if document else None,
                    regulator=chunk.regulator,
                    domain=chunk.domain,
                    section_reference=chunk.section_reference,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    similarity_score=round(max(0.0, min(1.0, score)), 4),
                    chunk_text=chunk.chunk_text,
                    keywords=chunk.keywords,
                    effective_from=chunk.effective_from,
                    effective_to=chunk.effective_to,
                )
                for chunk, document, score in rows
            ],
        )

    def _resolve_storage_path(self, storage_path: str) -> Path:
        path = Path(storage_path)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[3] / storage_path

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip()
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        if not safe or safe in {".", ".."}:
            raise RegulatoryDocumentProcessingError("Uploaded file name is invalid.")
        return safe

    def _document_type_from_suffix(self, suffix: str) -> str:
        mapping = {
            ".pdf": "pdf",
            ".doc": "docx",
            ".docx": "docx",
            ".txt": "txt",
            ".md": "markdown",
        }
        try:
            return mapping[suffix.lower()]
        except KeyError as exc:
            raise RegulatoryDocumentProcessingError(
                "Unsupported upload type. Use PDF, DOC, DOCX, TXT, or MD."
            ) from exc

    def _markdown_path(self, source_path: Path, record: RegulatoryDocumentRecord) -> Path:
        if source_path.suffix.lower() == ".md":
            return source_path
        markdown_dir = source_path.parent.parent / "markdown"
        return markdown_dir / f"{source_path.stem}_{record.version}.md"

    def _regulatory_document_to_read(
        self,
        record: RegulatoryDocumentRecord,
    ) -> RegulatoryDocumentRead:
        return RegulatoryDocumentRead(
            id=record.id,
            regulator=record.regulator,
            document_title=record.document_title,
            document_type=record.document_type,
            source_filename=record.source_filename,
            source_url=record.source_url,
            storage_path=record.storage_path,
            version=record.version,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            status=record.status,
            uploaded_by=record.uploaded_by,
            uploaded_at=record.uploaded_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _page_to_read(self, record: RegulatoryDocumentPageRecord) -> RegulatoryDocumentPageRead:
        return RegulatoryDocumentPageRead(
            id=record.id,
            document_id=record.document_id,
            page_number=record.page_number,
            raw_text=record.raw_text,
            cleaned_text=record.cleaned_text,
            markdown_text=record.markdown_text,
            extraction_status=record.extraction_status,
            created_at=record.created_at,
        )

    def _markdown_file_to_read(
        self,
        record: RegulatoryDocumentMarkdownFileRecord,
    ) -> RegulatoryDocumentMarkdownFileRead:
        return RegulatoryDocumentMarkdownFileRead(
            id=record.id,
            document_id=record.document_id,
            markdown_path=record.markdown_path,
            conversion_tool=record.conversion_tool,
            conversion_status=record.conversion_status,
            conversion_warnings=record.conversion_warnings,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _chunk_to_read(self, record: RegulatoryKnowledgeChunkRecord) -> RegulatoryKnowledgeChunkRead:
        return RegulatoryKnowledgeChunkRead(
            id=record.id,
            document_id=record.document_id,
            chunk_index=record.chunk_index,
            regulator=record.regulator,
            domain=record.domain,
            section_reference=record.section_reference,
            page_start=record.page_start,
            page_end=record.page_end,
            chunk_text=record.chunk_text,
            summary=record.summary,
            keywords=record.keywords,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            status=record.status,
            embedding_model=record.embedding_model,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )






