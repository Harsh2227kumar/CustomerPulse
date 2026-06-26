"""
Tests for CommunicationService — exercised entirely through a SimpleNamespace-based
fake repository; no real database or HTTP layer involved.
"""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.communications.schemas import CommunicationEntryCreate, CommunicationEntryRead, TimelineResponse
from app.communications.service import CommunicationComplaintNotFoundError, CommunicationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(
    id: str = "entry-1",
    complaint_pk: str = "pk-1",
    entry_type: str = "note",
    event_code=None,
    message: str = "Test message",
    actor=None,
    context=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        complaint_pk=complaint_pk,
        entry_type=entry_type,
        event_code=event_code,
        message=message,
        actor=actor,
        context=context,
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )


def _fake_repo(*, create_entry=None, list_for_complaint=None) -> SimpleNamespace:
    """Return a SimpleNamespace repo with AsyncMock defaults for every method."""
    return SimpleNamespace(
        create_entry=create_entry or AsyncMock(return_value=_entry()),
        list_for_complaint=list_for_complaint or AsyncMock(return_value=[]),
    )


def _fake_db(*, scalar_one_or_none=None) -> SimpleNamespace:
    """Minimal fake DB that supports `db.execute(...).scalar_one_or_none()`."""
    execute_result = SimpleNamespace(scalar_one_or_none=lambda: scalar_one_or_none)
    return SimpleNamespace(
        execute=AsyncMock(return_value=execute_result),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class CommunicationServiceTests(unittest.IsolatedAsyncioTestCase):

    # ── add_note ─────────────────────────────────────────────────────────

    async def test_add_note_creates_entry_with_correct_entry_type_and_actor(self) -> None:
        """add_note() must persist entry_type='note' and pass through the actor."""
        created = _entry(entry_type="note", actor="agent-007", message="Hello")
        repo = _fake_repo(create_entry=AsyncMock(return_value=created))

        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "pk-1")),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            refresh=AsyncMock(),
        )

        result = await CommunicationService(repo).add_note(
            db,
            "complaint-123",
            CommunicationEntryCreate(message="Hello"),
            actor="agent-007",
        )

        repo.create_entry.assert_awaited_once()
        call_kwargs = repo.create_entry.call_args.kwargs
        self.assertEqual(call_kwargs["entry_type"], "note")
        self.assertEqual(call_kwargs["actor"], "agent-007")
        self.assertEqual(call_kwargs["message"], "Hello")
        self.assertIsNone(call_kwargs["event_code"])

        self.assertIsInstance(result, CommunicationEntryRead)
        self.assertEqual(result.entry_type, "note")
        self.assertEqual(result.actor, "agent-007")

    async def test_add_note_passes_complaint_id_through_to_read_schema(self) -> None:
        """The returned CommunicationEntryRead.complaint_id must match the public ID."""
        created = _entry(complaint_pk="pk-99")
        repo = _fake_repo(create_entry=AsyncMock(return_value=created))
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "pk-99")),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            refresh=AsyncMock(),
        )

        result = await CommunicationService(repo).add_note(
            db,
            "SRC-complaint-99",
            CommunicationEntryCreate(message="Check this"),
            actor="manager",
        )

        self.assertEqual(result.complaint_id, "SRC-complaint-99")

    # ── record_system_event ───────────────────────────────────────────────

    async def test_record_system_event_swallows_repository_exception(self) -> None:
        """record_system_event() must never propagate an exception from the repo."""
        repo = _fake_repo(create_entry=AsyncMock(side_effect=RuntimeError("DB exploded")))
        db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        # Must not raise even though create_entry raises
        await CommunicationService(repo).record_system_event(
            db,
            complaint_pk="pk-boom",
            event_code="processing_started",
            message="Processing started",
            context=None,
        )

        repo.create_entry.assert_awaited_once()
        db.rollback.assert_awaited_once()

    async def test_record_system_event_calls_create_entry_with_system_type(self) -> None:
        """record_system_event() must always use entry_type='system' and actor='system'."""
        repo = _fake_repo()
        db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        await CommunicationService(repo).record_system_event(
            db,
            complaint_pk="pk-1",
            event_code="saved",
            message="Saved successfully",
            context={"ai_status": "completed"},
        )

        call_kwargs = repo.create_entry.call_args.kwargs
        self.assertEqual(call_kwargs["entry_type"], "system")
        self.assertEqual(call_kwargs["actor"], "system")
        self.assertEqual(call_kwargs["event_code"], "saved")
        self.assertEqual(call_kwargs["context"], {"ai_status": "completed"})

    async def test_record_system_event_commits_on_success(self) -> None:
        """record_system_event() commits when no exception is raised."""
        repo = _fake_repo()
        db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        await CommunicationService(repo).record_system_event(
            db, "pk-1", event_code="local_ml", message="Local ML done"
        )

        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()

    # ── get_timeline ──────────────────────────────────────────────────────

    async def test_get_timeline_returns_entries_in_repository_order(self) -> None:
        """get_timeline() must preserve the ordering returned by the repository."""
        entries = [
            _entry(id="e-1", message="First", entry_type="system"),
            _entry(id="e-2", message="Second", entry_type="note"),
            _entry(id="e-3", message="Third", entry_type="escalation"),
        ]
        repo = _fake_repo(list_for_complaint=AsyncMock(return_value=entries))
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "pk-1")),
        )

        result = await CommunicationService(repo).get_timeline(db, "complaint-abc")

        self.assertIsInstance(result, TimelineResponse)
        self.assertEqual(len(result.items), 3)
        self.assertEqual(result.items[0].id, "e-1")
        self.assertEqual(result.items[1].id, "e-2")
        self.assertEqual(result.items[2].id, "e-3")
        self.assertEqual(result.items[1].entry_type, "note")

    async def test_get_timeline_empty_returns_empty_items_list(self) -> None:
        """get_timeline() with no entries must return an empty items list."""
        repo = _fake_repo(list_for_complaint=AsyncMock(return_value=[]))
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "pk-1")),
        )

        result = await CommunicationService(repo).get_timeline(db, "complaint-xyz")

        self.assertEqual(result.items, [])
        self.assertEqual(result.complaint_id, "complaint-xyz")

    # ── resolve_complaint_pk ──────────────────────────────────────────────

    async def test_resolve_complaint_pk_raises_when_complaint_not_found(self) -> None:
        """resolve_complaint_pk() must raise CommunicationComplaintNotFoundError for unknown IDs."""
        repo = _fake_repo()
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)),
        )

        with self.assertRaises(CommunicationComplaintNotFoundError):
            await CommunicationService(repo).resolve_complaint_pk(db, "no-such-complaint")

    async def test_resolve_complaint_pk_returns_pk_when_found(self) -> None:
        """resolve_complaint_pk() must return the database primary key string on success."""
        repo = _fake_repo()
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "pk-42")),
        )

        result = await CommunicationService(repo).resolve_complaint_pk(db, "SRC-42")

        self.assertEqual(result, "pk-42")
