from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.similarity import cosine_similarity_score
from app.models.complaint import Complaint


async def find_similar_complaints(
    db: AsyncSession,
    embedding: list[float],
    limit: int = 5,
) -> list[tuple[Complaint, float]]:
    stmt = (
        select(Complaint, Complaint.embedding.cosine_distance(embedding).label("distance"))
        .where(Complaint.embedding.is_not(None))
        .order_by("distance")
        .limit(limit)
    )
    rows = await db.execute(stmt)
    return [(complaint, cosine_similarity_score(distance)) for complaint, distance in rows.all()]
