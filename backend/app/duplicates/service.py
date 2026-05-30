from sqlalchemy.ext.asyncio import AsyncSession

from app.duplicates.models import DuplicateGroup
from app.duplicates.repository import DuplicateRepository
from app.duplicates.schemas import (
    ChannelComparisonResponse,
    DuplicateDetectRequest,
    DuplicateDetectResponse,
    DuplicateGroupListQuery,
    DuplicateGroupListResponse,
    DuplicateGroupRead,
    DuplicateGroupSummary,
    DuplicateMemberRead,
    DuplicateMergeRequest,
    DuplicateRejectRequest,
)
from app.models.complaint import Complaint


class DuplicateGroupNotFoundError(LookupError):
    pass


class DuplicateComplaintNotFoundError(LookupError):
    pass


class DuplicateComplaintNotInGroupError(LookupError):
    pass


class DuplicateService:
    def __init__(self, repository: DuplicateRepository | None = None) -> None:
        self.repository = repository or DuplicateRepository()

    async def detect_duplicates(
        self,
        db: AsyncSession,
        payload: DuplicateDetectRequest,
    ) -> DuplicateDetectResponse:
        exact_groups_created = 0
        near_groups_created = 0
        try:
            await self.repository.clear_open_groups(db)
            if payload.exact_enabled:
                exact_clusters = await self.repository.find_exact_duplicate_clusters(db)
                for cluster in exact_clusters:
                    await self.repository.create_group(
                        db,
                        detection_type="exact",
                        exact_hash=str(cluster["exact_hash"]) if cluster["exact_hash"] is not None else None,
                        similarity_threshold=None,
                        members=cluster["members"],
                    )
                exact_groups_created = len(exact_clusters)

            if payload.near_enabled:
                near_clusters = await self.repository.find_near_duplicate_clusters(
                    db,
                    payload.near_threshold,
                )
                for cluster in near_clusters:
                    await self.repository.create_group(
                        db,
                        detection_type="near",
                        exact_hash=None,
                        similarity_threshold=float(cluster["similarity_threshold"]),
                        members=cluster["members"],
                    )
                near_groups_created = len(near_clusters)

            await self.repository.commit(db)
        except Exception:
            await self.repository.rollback(db)
            raise

        return DuplicateDetectResponse(
            exact_groups_created=exact_groups_created,
            near_groups_created=near_groups_created,
            total_groups_created=exact_groups_created + near_groups_created,
        )

    async def list_groups(
        self,
        db: AsyncSession,
        filters: DuplicateGroupListQuery,
    ) -> DuplicateGroupListResponse:
        rows, count = await self.repository.list_groups(
            db,
            limit=filters.limit,
            offset=filters.offset,
            detection_type=filters.detection_type.value if filters.detection_type else None,
            status=filters.status.value if filters.status else None,
        )
        return DuplicateGroupListResponse(
            items=[
                DuplicateGroupSummary(
                    group_id=group.id,
                    detection_type=group.detection_type,
                    status=group.status,
                    exact_hash=group.exact_hash,
                    similarity_threshold=group.similarity_threshold,
                    canonical_complaint_id=canonical_id or canonical_pk,
                    member_count=member_count,
                    created_at=group.created_at,
                    updated_at=group.updated_at,
                )
                for group, member_count, canonical_id, canonical_pk in rows
            ],
            limit=filters.limit,
            offset=filters.offset,
            count=count,
        )

    async def get_group(
        self,
        db: AsyncSession,
        group_id: str,
    ) -> DuplicateGroupRead:
        result = await self.repository.get_group(db, group_id)
        if result is None:
            raise DuplicateGroupNotFoundError(group_id)
        group, canonical_id, member_rows = result
        return self._to_group_read(group, canonical_id, member_rows)

    async def merge_group(
        self,
        db: AsyncSession,
        group_id: str,
        payload: DuplicateMergeRequest,
    ) -> DuplicateGroupRead:
        result = await self.repository.get_group(db, group_id)
        if result is None:
            raise DuplicateGroupNotFoundError(group_id)
        group, _canonical_id, member_rows = result

        canonical_pk = await self.repository.resolve_complaint_pk(db, payload.canonical_complaint_id)
        if canonical_pk is None:
            raise DuplicateComplaintNotFoundError(payload.canonical_complaint_id)
        if canonical_pk not in {member.complaint_pk for member, _complaint, _complaint_id in member_rows}:
            raise DuplicateComplaintNotInGroupError(payload.canonical_complaint_id)

        try:
            await self.repository.update_group_merge(db, group.id, canonical_pk, payload.notes)
            await self.repository.commit(db)
        except Exception:
            await self.repository.rollback(db)
            raise
        return await self.get_group(db, group_id)

    async def reject_group(
        self,
        db: AsyncSession,
        group_id: str,
        payload: DuplicateRejectRequest,
    ) -> DuplicateGroupRead:
        result = await self.repository.get_group(db, group_id)
        if result is None:
            raise DuplicateGroupNotFoundError(group_id)
        try:
            await self.repository.update_group_reject(db, group_id, payload.notes)
            await self.repository.commit(db)
        except Exception:
            await self.repository.rollback(db)
            raise
        return await self.get_group(db, group_id)

    async def channel_comparison(
        self,
        db: AsyncSession,
    ) -> ChannelComparisonResponse:
        return ChannelComparisonResponse(items=await self.repository.channel_comparison(db))

    def _to_group_read(
        self,
        group: DuplicateGroup,
        canonical_id: str | None,
        member_rows: list[tuple[object, Complaint, str]] | tuple[tuple[object, Complaint, str], ...],
    ) -> DuplicateGroupRead:
        members = [
            DuplicateMemberRead(
                complaint_id=complaint_id,
                complaint_pk=complaint.id,
                channel=complaint.channel,
                product=complaint.product,
                issue=complaint.issue,
                company=complaint.company,
                narrative=complaint.narrative,
                similarity_score=member.similarity_score,
                is_primary=member.is_primary,
            )
            for member, complaint, complaint_id in member_rows
        ]
        return DuplicateGroupRead(
            group_id=group.id,
            detection_type=group.detection_type,
            status=group.status,
            exact_hash=group.exact_hash,
            similarity_threshold=group.similarity_threshold,
            canonical_complaint_id=canonical_id or group.canonical_complaint_pk,
            member_count=len(members),
            created_at=group.created_at,
            updated_at=group.updated_at,
            merged_at=group.merged_at,
            rejected_at=group.rejected_at,
            notes=group.notes,
            members=members,
        )
