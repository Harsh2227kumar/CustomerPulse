from collections import defaultdict
from collections.abc import Sequence
from itertools import combinations

from sqlalchemy import and_, case, delete, distinct, func, literal_column, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.duplicates.models import DuplicateGroup, DuplicateMember
from app.models.complaint import Complaint


class DuplicateRepository:
    async def clear_open_groups(self, db: AsyncSession) -> None:
        await db.execute(
            delete(DuplicateGroup).where(
                DuplicateGroup.status.in_(("detected", "rejected"))
            )
        )

    async def find_exact_duplicate_clusters(
        self,
        db: AsyncSession,
    ) -> list[dict[str, object]]:
        narrative_hash = func.md5(func.lower(func.trim(Complaint.narrative)))
        grouped_stmt = (
            select(
                narrative_hash.label("exact_hash"),
                func.array_agg(Complaint.id).label("complaint_pks"),
            )
            .where(Complaint.narrative.is_not(None))
            .group_by(narrative_hash)
            .having(func.count(Complaint.id) > 1)
        )
        rows = (await db.execute(grouped_stmt)).all()
        return [
            {
                "exact_hash": exact_hash,
                "similarity_threshold": None,
                "members": [{"complaint_pk": complaint_pk, "similarity_score": 1.0} for complaint_pk in complaint_pks],
            }
            for exact_hash, complaint_pks in rows
        ]

    async def find_near_duplicate_clusters(
        self,
        db: AsyncSession,
        threshold: float,
    ) -> list[dict[str, object]]:
        complaints_table = Complaint.__table__
        c1 = complaints_table.alias("c1")
        c2 = complaints_table.alias("c2")
        similarity_expr = 1 - c1.c.embedding.op("<=>")(c2.c.embedding)
        stmt = (
            select(
                c1.c.id.label("left_id"),
                c2.c.id.label("right_id"),
                similarity_expr.label("similarity_score"),
            )
            .where(
                and_(
                    c1.c.id < c2.c.id,
                    c1.c.embedding.is_not(None),
                    c2.c.embedding.is_not(None),
                    similarity_expr >= threshold,
                )
            )
        )
        rows = (await db.execute(stmt)).all()
        if not rows:
            return []

        graph: dict[str, set[str]] = defaultdict(set)
        edge_scores: dict[tuple[str, str], float] = {}
        for left_id, right_id, similarity_score in rows:
            graph[left_id].add(right_id)
            graph[right_id].add(left_id)
            edge_scores[(left_id, right_id)] = float(similarity_score)
            edge_scores[(right_id, left_id)] = float(similarity_score)

        clusters: list[list[str]] = []
        visited: set[str] = set()
        for node in graph:
            if node in visited:
                continue
            stack = [node]
            component: list[str] = []
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                stack.extend(graph[current] - visited)
            if len(component) > 1:
                clusters.append(sorted(component))

        results: list[dict[str, object]] = []
        for component in clusters:
            members = []
            for complaint_pk in component:
                scores = [
                    edge_scores[(complaint_pk, other_pk)]
                    for other_pk in component
                    if other_pk != complaint_pk and (complaint_pk, other_pk) in edge_scores
                ]
                members.append(
                    {
                        "complaint_pk": complaint_pk,
                        "similarity_score": max(scores) if scores else 1.0,
                    }
                )
            results.append(
                {
                    "exact_hash": None,
                    "similarity_threshold": threshold,
                    "members": members,
                }
            )
        return results

    async def create_group(
        self,
        db: AsyncSession,
        *,
        detection_type: str,
        exact_hash: str | None,
        similarity_threshold: float | None,
        members: Sequence[dict[str, object]],
    ) -> DuplicateGroup:
        canonical_complaint_pk = sorted(
            (str(member["complaint_pk"]) for member in members),
            key=str,
        )[0]
        group = DuplicateGroup(
            detection_type=detection_type,
            status="detected",
            exact_hash=exact_hash,
            similarity_threshold=similarity_threshold,
            canonical_complaint_pk=canonical_complaint_pk,
        )
        db.add(group)
        await db.flush()

        for member in members:
            complaint_pk = str(member["complaint_pk"])
            db.add(
                DuplicateMember(
                    group_id=group.id,
                    complaint_pk=complaint_pk,
                    similarity_score=float(member["similarity_score"]) if member["similarity_score"] is not None else None,
                    is_primary=complaint_pk == canonical_complaint_pk,
                )
            )

        await db.flush()
        return group

    async def commit(self, db: AsyncSession) -> None:
        await db.commit()

    async def rollback(self, db: AsyncSession) -> None:
        await db.rollback()

    async def list_groups(
        self,
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
        detection_type: str | None,
        status: str | None,
    ) -> tuple[Sequence[tuple[DuplicateGroup, int, str | None, str | None]], int]:
        canonical = Complaint.__table__.alias("canonical")
        member_count = func.count(DuplicateMember.id)
        canonical_identifier = case(
            (canonical.c.source_complaint_id.is_not(None), canonical.c.source_complaint_id),
            else_=canonical.c.id,
        )
        stmt = (
            select(
                DuplicateGroup,
                member_count.label("member_count"),
                canonical_identifier.label("canonical_id"),
                canonical.c.id.label("canonical_pk"),
            )
            .join(DuplicateMember, DuplicateMember.group_id == DuplicateGroup.id)
            .join(canonical, canonical.c.id == DuplicateGroup.canonical_complaint_pk, isouter=True)
            .group_by(DuplicateGroup.id, canonical.c.source_complaint_id, canonical.c.id)
            .order_by(DuplicateGroup.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(DuplicateGroup)
        if detection_type:
            stmt = stmt.where(DuplicateGroup.detection_type == detection_type)
            count_stmt = count_stmt.where(DuplicateGroup.detection_type == detection_type)
        if status:
            stmt = stmt.where(DuplicateGroup.status == status)
            count_stmt = count_stmt.where(DuplicateGroup.status == status)

        rows = (await db.execute(stmt)).all()
        count = (await db.execute(count_stmt)).scalar_one()
        return rows, count

    async def get_group(
        self,
        db: AsyncSession,
        group_id: str,
    ) -> tuple[DuplicateGroup, str | None, Sequence[tuple[DuplicateMember, Complaint, str]]] | None:
        canonical = Complaint.__table__.alias("canonical")
        canonical_stmt = (
            select(
                DuplicateGroup,
                case(
                    (canonical.c.source_complaint_id.is_not(None), canonical.c.source_complaint_id),
                    else_=canonical.c.id,
                ).label("canonical_id"),
            )
            .join(canonical, canonical.c.id == DuplicateGroup.canonical_complaint_pk, isouter=True)
            .where(DuplicateGroup.id == group_id)
        )
        group_row = (await db.execute(canonical_stmt)).one_or_none()
        if group_row is None:
            return None
        group, canonical_id = group_row

        member_identifier = case(
            (Complaint.source_complaint_id.is_not(None), Complaint.source_complaint_id),
            else_=Complaint.id,
        )
        members_stmt = (
            select(DuplicateMember, Complaint, member_identifier.label("complaint_id"))
            .join(Complaint, Complaint.id == DuplicateMember.complaint_pk)
            .where(DuplicateMember.group_id == group_id)
            .order_by(DuplicateMember.is_primary.desc(), DuplicateMember.created_at.asc())
        )
        member_rows = (await db.execute(members_stmt)).all()
        return group, canonical_id, member_rows

    async def resolve_complaint_pk(
        self,
        db: AsyncSession,
        complaint_id: str,
    ) -> str | None:
        stmt = select(Complaint.id).where(
            (Complaint.id == complaint_id) | (Complaint.source_complaint_id == complaint_id)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def update_group_merge(
        self,
        db: AsyncSession,
        group_id: str,
        canonical_complaint_pk: str,
        notes: str | None,
    ) -> None:
        await db.execute(
            update(DuplicateGroup)
            .where(DuplicateGroup.id == group_id)
            .values(
                status="merged",
                canonical_complaint_pk=canonical_complaint_pk,
                merged_at=func.now(),
                rejected_at=None,
                notes=notes,
                updated_at=func.now(),
            )
        )
        await db.execute(
            update(DuplicateMember)
            .where(DuplicateMember.group_id == group_id)
            .values(
                is_primary=case(
                    (DuplicateMember.complaint_pk == canonical_complaint_pk, True),
                    else_=False,
                )
            )
        )

    async def update_group_reject(
        self,
        db: AsyncSession,
        group_id: str,
        notes: str | None,
    ) -> None:
        await db.execute(
            update(DuplicateGroup)
            .where(DuplicateGroup.id == group_id)
            .values(
                status="rejected",
                rejected_at=func.now(),
                merged_at=None,
                notes=notes,
                updated_at=func.now(),
            )
        )

    async def channel_comparison(
        self,
        db: AsyncSession,
    ) -> list[dict[str, object]]:
        group_rows = (
            await db.execute(
                select(DuplicateGroup.id, DuplicateMember.complaint_pk, Complaint.channel)
                .join(DuplicateMember, DuplicateMember.group_id == DuplicateGroup.id)
                .join(Complaint, Complaint.id == DuplicateMember.complaint_pk)
                .where(DuplicateGroup.status == "detected")
                .order_by(DuplicateGroup.id)
            )
        ).all()
        grouped_channels: dict[str, list[str]] = defaultdict(list)
        for group_id, _complaint_pk, channel in group_rows:
            grouped_channels[group_id].append(channel or "Unknown")

        comparisons: dict[tuple[str, str], dict[str, int]] = {}
        for channels in grouped_channels.values():
            unique_channels = sorted(set(channels))
            for channel_a, channel_b in combinations(unique_channels, 2):
                key = (channel_a, channel_b)
                entry = comparisons.setdefault(key, {"group_count": 0, "complaint_count": 0})
                entry["group_count"] += 1
                entry["complaint_count"] += sum(
                    1 for channel in channels if channel in {channel_a, channel_b}
                )
            if len(unique_channels) == 1:
                key = (unique_channels[0], unique_channels[0])
                entry = comparisons.setdefault(key, {"group_count": 0, "complaint_count": 0})
                entry["group_count"] += 1
                entry["complaint_count"] += len(channels)

        return [
            {
                "channel_a": channel_a,
                "channel_b": channel_b,
                "group_count": values["group_count"],
                "complaint_count": values["complaint_count"],
            }
            for (channel_a, channel_b), values in sorted(comparisons.items())
        ]
