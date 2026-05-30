import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.duplicates.schemas import DuplicateDetectRequest, DuplicateMergeRequest, DuplicateRejectRequest
from app.duplicates.service import DuplicateService


def _group(status: str = "detected", canonical: str = "pk-1") -> SimpleNamespace:
    return SimpleNamespace(
        id="group-1",
        detection_type="near",
        status=status,
        exact_hash="hash-1",
        similarity_threshold=0.85,
        canonical_complaint_pk=canonical,
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        merged_at=None,
        rejected_at=None,
        notes=None,
    )


def _member(complaint_pk: str, similarity: float, primary: bool = False) -> SimpleNamespace:
    complaint = SimpleNamespace(
        id=complaint_pk,
        source_complaint_id=f"SRC-{complaint_pk}",
        channel="Web",
        product="Credit card",
        issue="Billing dispute",
        company="Test Bank",
        narrative="Duplicated charge on account.",
    )
    member = SimpleNamespace(
        complaint_pk=complaint_pk,
        similarity_score=similarity,
        is_primary=primary,
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )
    return member, complaint, complaint.source_complaint_id


class DuplicateTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_duplicate_detected_by_narrative_hash(self) -> None:
        repository = SimpleNamespace(
            clear_open_groups=AsyncMock(),
            find_exact_duplicate_clusters=AsyncMock(
                return_value=[
                    {
                        "exact_hash": "hash-1",
                        "members": [
                            {"complaint_pk": "pk-1", "similarity_score": 1.0},
                            {"complaint_pk": "pk-2", "similarity_score": 1.0},
                        ],
                    }
                ]
            ),
            find_near_duplicate_clusters=AsyncMock(return_value=[]),
            create_group=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        result = await DuplicateService(repository).detect_duplicates(
            object(),
            DuplicateDetectRequest(exact_enabled=True, near_enabled=False),
        )

        self.assertEqual(result.exact_groups_created, 1)
        self.assertEqual(repository.create_group.await_args.kwargs["exact_hash"], "hash-1")

    async def test_near_duplicate_detected_above_similarity_threshold(self) -> None:
        repository = SimpleNamespace(
            clear_open_groups=AsyncMock(),
            find_exact_duplicate_clusters=AsyncMock(return_value=[]),
            find_near_duplicate_clusters=AsyncMock(
                return_value=[
                    {
                        "similarity_threshold": 0.92,
                        "members": [
                            {"complaint_pk": "pk-1", "similarity_score": 0.95},
                            {"complaint_pk": "pk-2", "similarity_score": 0.95},
                        ],
                    }
                ]
            ),
            create_group=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        result = await DuplicateService(repository).detect_duplicates(
            object(),
            DuplicateDetectRequest(exact_enabled=False, near_enabled=True, near_threshold=0.92),
        )

        self.assertEqual(result.near_groups_created, 1)
        self.assertEqual(repository.find_near_duplicate_clusters.await_args.args[1], 0.92)

    async def test_near_duplicate_not_detected_below_threshold(self) -> None:
        repository = SimpleNamespace(
            clear_open_groups=AsyncMock(),
            find_exact_duplicate_clusters=AsyncMock(return_value=[]),
            find_near_duplicate_clusters=AsyncMock(return_value=[]),
            create_group=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        result = await DuplicateService(repository).detect_duplicates(
            object(),
            DuplicateDetectRequest(exact_enabled=False, near_enabled=True, near_threshold=0.95),
        )

        self.assertEqual(result.near_groups_created, 0)
        repository.create_group.assert_not_awaited()

    async def test_duplicate_group_creation(self) -> None:
        repository = SimpleNamespace(
            clear_open_groups=AsyncMock(),
            find_exact_duplicate_clusters=AsyncMock(
                return_value=[
                    {
                        "exact_hash": "hash-1",
                        "members": [{"complaint_pk": "pk-1", "similarity_score": 1.0}],
                    }
                ]
            ),
            find_near_duplicate_clusters=AsyncMock(return_value=[]),
            create_group=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        await DuplicateService(repository).detect_duplicates(object(), DuplicateDetectRequest())
        self.assertEqual(repository.create_group.await_count, 1)

    async def test_merge_action_marks_complaints_correctly(self) -> None:
        member_rows = [_member("pk-1", 0.95, True), _member("pk-2", 0.95, False)]
        merged_group = _group(status="merged", canonical="pk-2")
        repository = SimpleNamespace(
            get_group=AsyncMock(side_effect=[(_group(), "SRC-pk-1", member_rows), (merged_group, "SRC-pk-2", [_member("pk-1", 0.95, False), _member("pk-2", 0.95, True)])]),
            resolve_complaint_pk=AsyncMock(return_value="pk-2"),
            update_group_merge=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        result = await DuplicateService(repository).merge_group(
            object(),
            "group-1",
            DuplicateMergeRequest(canonical_complaint_id="SRC-pk-2", notes="Keep second complaint."),
        )

        self.assertEqual(result.status, "merged")
        self.assertEqual(result.canonical_complaint_id, "SRC-pk-2")
        self.assertTrue(result.members[0].is_primary is False or result.members[1].is_primary)

    async def test_reject_action_dismisses_group(self) -> None:
        member_rows = [_member("pk-1", 0.95, True), _member("pk-2", 0.95, False)]
        rejected_group = SimpleNamespace(**{**_group(status="rejected").__dict__, "rejected_at": datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc)})
        repository = SimpleNamespace(
            get_group=AsyncMock(side_effect=[(_group(), "SRC-pk-1", member_rows), (rejected_group, "SRC-pk-1", member_rows)]),
            update_group_reject=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        result = await DuplicateService(repository).reject_group(
            object(),
            "group-1",
            DuplicateRejectRequest(notes="Reviewed and dismissed."),
        )

        self.assertEqual(result.status, "rejected")
        repository.update_group_reject.assert_awaited_once()

    async def test_similarity_threshold_boundary_at_0_85(self) -> None:
        repository = SimpleNamespace(
            clear_open_groups=AsyncMock(),
            find_exact_duplicate_clusters=AsyncMock(return_value=[]),
            find_near_duplicate_clusters=AsyncMock(return_value=[]),
            create_group=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        await DuplicateService(repository).detect_duplicates(
            object(),
            DuplicateDetectRequest(exact_enabled=False, near_enabled=True, near_threshold=0.85),
        )

        self.assertEqual(repository.find_near_duplicate_clusters.await_args.args[1], 0.85)

    async def test_duplicate_detection_ignores_different_channels(self) -> None:
        repository = SimpleNamespace(
            clear_open_groups=AsyncMock(),
            find_exact_duplicate_clusters=AsyncMock(return_value=[]),
            find_near_duplicate_clusters=AsyncMock(return_value=[]),
            create_group=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

        result = await DuplicateService(repository).detect_duplicates(
            object(),
            DuplicateDetectRequest(exact_enabled=True, near_enabled=True),
        )

        self.assertEqual(result.total_groups_created, 0)
