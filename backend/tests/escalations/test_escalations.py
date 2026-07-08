import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.escalations.schemas import EscalationCreateRequest, EscalationResolveRequest
from app.escalations.service import (
    EscalationAlreadyOpenError,
    EscalationService,
)
from app.core.constants import ChurnRisk


NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def _complaint(
    *,
    pk: str = "pk-1",
    source_id: str = "SRC-1",
    urgency: int = 50,
    churn: str | ChurnRisk = ChurnRisk.LOW,
    ai_confidence: float = 0.85,
    ai_status: str = "completed",
    human_review_reason: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=pk,
        source_complaint_id=source_id,
        urgency_score=urgency,
        churn_risk=churn,
        ai_confidence=ai_confidence,
        ai_status=ai_status,
        human_review_reason=human_review_reason,
    )


def _escalation(
    *,
    esc_id: str = "esc-1",
    complaint_pk: str = "pk-1",
    status: str = "open",
    trigger_type: str = "manual",
    reason: str = "test reason",
    escalated_by: str | None = "agent-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=esc_id,
        complaint_pk=complaint_pk,
        status=status,
        trigger_type=trigger_type,
        reason=reason,
        urgency_score_snapshot=75,
        churn_risk_snapshot="High",
        ai_confidence_snapshot=0.85,
        escalated_by=escalated_by,
        escalated_at=NOW,
        resolved_by=None,
        resolved_at=None,
        resolution_notes=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _fake_db() -> SimpleNamespace:
    """Minimal fake AsyncSession used where the service calls db.commit / db.refresh / db.get."""
    return SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
        rollback=AsyncMock(),
        get=AsyncMock(return_value=_complaint()),
        execute=AsyncMock(),
    )


class EscalationManualTests(unittest.IsolatedAsyncioTestCase):
    async def test_escalate_manual_raises_when_open_escalation_exists(self) -> None:
        repository = SimpleNamespace(
            get_open_for_complaint=AsyncMock(return_value=_escalation()),
            create=AsyncMock(),
        )
        service = EscalationService(repository=repository)
        service._resolve_complaint = AsyncMock(return_value=_complaint())

        with self.assertRaises(EscalationAlreadyOpenError):
            await service.escalate_manual(
                _fake_db(),
                "SRC-1",
                EscalationCreateRequest(reason="Needs attention"),
                actor="agent-1",
            )
        repository.create.assert_not_awaited()

    async def test_escalate_manual_calls_add_escalation_note_once(self) -> None:
        created_esc = _escalation()
        repository = SimpleNamespace(
            get_open_for_complaint=AsyncMock(return_value=None),
            create=AsyncMock(return_value=created_esc),
        )
        service = EscalationService(repository=repository)
        service._resolve_complaint = AsyncMock(return_value=_complaint())

        mock_note = AsyncMock()
        with patch(
            "app.communications.service.CommunicationService"
        ) as MockCommSvc:
            MockCommSvc.return_value.add_escalation_note = mock_note
            result = await service.escalate_manual(
                _fake_db(),
                "SRC-1",
                EscalationCreateRequest(reason="Needs attention"),
                actor="agent-1",
            )

        mock_note.assert_awaited_once()
        call_kwargs = mock_note.await_args.kwargs
        self.assertIn("Escalated by agent-1", call_kwargs["message"])
        self.assertIn("Needs attention", call_kwargs["message"])
        self.assertEqual(call_kwargs["actor"], "agent-1")
        self.assertEqual(result.trigger_type, "manual")


class EscalationResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_sets_status_and_logs_note(self) -> None:
        open_esc = _escalation(status="open")
        resolved_esc = _escalation(status="resolved")
        resolved_esc.resolved_by = "manager-1"
        resolved_esc.resolution_notes = "Fixed"
        resolved_esc.resolved_at = NOW

        repository = SimpleNamespace(
            get=AsyncMock(return_value=open_esc),
            resolve=AsyncMock(return_value=resolved_esc),
        )
        service = EscalationService(repository=repository)
        db = _fake_db()

        mock_note = AsyncMock()
        with patch(
            "app.communications.service.CommunicationService"
        ) as MockCommSvc:
            MockCommSvc.return_value.add_escalation_note = mock_note
            result = await service.resolve(
                db,
                "esc-1",
                EscalationResolveRequest(resolution_notes="Fixed"),
                actor="manager-1",
            )

        self.assertEqual(result.status, "resolved")
        mock_note.assert_awaited_once()
        call_kwargs = mock_note.await_args.kwargs
        self.assertIn("resolved by manager-1", call_kwargs["message"])


class EscalationAutoTests(unittest.IsolatedAsyncioTestCase):
    def _service_with_repo(self, open_for_complaint=None, created_esc=None):
        repository = SimpleNamespace(
            get_open_for_complaint=AsyncMock(return_value=open_for_complaint),
            create=AsyncMock(return_value=created_esc or _escalation(trigger_type="auto", escalated_by=None)),
        )
        return EscalationService(repository=repository), repository

    async def test_returns_none_when_all_signals_clean(self) -> None:
        service, repo = self._service_with_repo()
        complaint = _complaint(urgency=40, churn="Low", ai_status="completed")

        with patch("app.escalations.service.SLAService") as MockSLA:
            MockSLA.return_value.is_breach_risk = AsyncMock(return_value=False)
            result = await service.evaluate_auto_escalation(_fake_db(), complaint)

        self.assertIsNone(result)
        repo.create.assert_not_awaited()

    async def test_returns_escalation_when_high_urgency_and_high_churn(self) -> None:
        auto_esc = _escalation(trigger_type="auto", escalated_by=None)
        service, repo = self._service_with_repo(created_esc=auto_esc)
        complaint = _complaint(urgency=85, churn="High", ai_status="completed")

        mock_note = AsyncMock()
        with (
            patch("app.escalations.service.SLAService") as MockSLA,
            patch("app.communications.service.CommunicationService") as MockComm,
        ):
            MockSLA.return_value.is_breach_risk = AsyncMock(return_value=False)
            MockComm.return_value.add_escalation_note = mock_note
            result = await service.evaluate_auto_escalation(_fake_db(), complaint)

        self.assertIsNotNone(result)
        self.assertEqual(result.trigger_type, "auto")
        self.assertIn("urgency 85 with High churn risk", repo.create.await_args.kwargs["reason"])

    async def test_returns_none_when_open_escalation_exists(self) -> None:
        existing = _escalation()
        service, repo = self._service_with_repo(open_for_complaint=existing)
        complaint = _complaint(urgency=85, churn="High", ai_status="completed")

        with patch("app.escalations.service.SLAService") as MockSLA:
            MockSLA.return_value.is_breach_risk = AsyncMock(return_value=False)
            result = await service.evaluate_auto_escalation(_fake_db(), complaint)

        self.assertIsNone(result)
        repo.create.assert_not_awaited()

    async def test_returns_none_when_status_is_pending(self) -> None:
        service, repo = self._service_with_repo()
        complaint = _complaint(urgency=85, churn="High", ai_status="pending")

        result = await service.evaluate_auto_escalation(_fake_db(), complaint)

        self.assertIsNone(result)
        repo.create.assert_not_awaited()
