from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.ai.embeddings import cosine_similarity, create_embedding
from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db import crud
from app.db.models import EntityRelationship, Record
from app.metrics import metrics

router = APIRouter(tags=["intelligence"])
logger = structlog.get_logger()


class MergeArtistsRequest(BaseModel):
    primary_id: str
    secondary_id: str


class AskRequest(BaseModel):
    query: str
    limit: int = 5


class DuplicateDecisionRequest(BaseModel):
    left_id: str
    right_id: str
    decision: str
    reviewer: str | None = None
    primary_id: str | None = None


def _parse_json(payload: str | None) -> dict:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token for token in value.lower().replace("-", " ").split() if token}


def _name_similarity(left: str | None, right: str | None) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens.intersection(right_tokens))
    union = len(left_tokens.union(right_tokens))
    return intersection / union if union else 0.0


def _shared_link_similarity(left: Record, right: Record) -> float:
    left_links = {item for item in [left.website_url, left.instagram_url, left.source_url] if item}
    right_links = {item for item in [right.website_url, right.instagram_url, right.source_url] if item}
    if not left_links or not right_links:
        return 0.0
    return 1.0 if left_links.intersection(right_links) else 0.0


def _related_overlap(left: Record, right: Record) -> float:
    left_payload = _parse_json(left.raw_data)
    right_payload = _parse_json(right.raw_data)
    left_related = left_payload.get("related", {}) if isinstance(left_payload.get("related"), dict) else {}
    right_related = right_payload.get("related", {}) if isinstance(right_payload.get("related"), dict) else {}

    overlap_score = 0.0
    for key in ("exhibitions", "articles", "press"):
        left_titles = {item.get("title", "").strip().lower() for item in left_related.get(key, []) if isinstance(item, dict)}
        right_titles = {item.get("title", "").strip().lower() for item in right_related.get(key, []) if isinstance(item, dict)}
        if left_titles and right_titles:
            union = left_titles.union(right_titles)
            if union:
                overlap_score += len(left_titles.intersection(right_titles)) / len(union)
    return min(overlap_score / 3, 1.0)


def _location_similarity(left: Record, right: Record) -> float:
    left_location = " ".join(part for part in [left.city, left.country, left.nationality] if part).lower()
    right_location = " ".join(part for part in [right.city, right.country, right.nationality] if part).lower()
    if not left_location or not right_location:
        return 0.0
    return 1.0 if left_location == right_location else 0.5 if left.country and left.country == right.country else 0.0


def _relationship_counts(relationships: list[EntityRelationship], artist_ids: set[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for rel in relationships:
        if rel.from_record_id in artist_ids and rel.to_record_id in artist_ids:
            counter[rel.from_record_id] += 1
            counter[rel.to_record_id] += 1
    return counter


def _score_duplicate_candidate(left: Record, right: Record) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    name_score = _name_similarity(left.title, right.title)
    score += name_score * 0.35
    if name_score > 0.55:
        reasons.append("name similarity")

    embedding_score = crud.embedding_similarity(left, right)
    score += embedding_score * 0.4
    if embedding_score > 0.7:
        reasons.append("embedding similarity")

    link_score = _shared_link_similarity(left, right)
    score += link_score * 0.15
    if link_score > 0:
        reasons.append("shared links")

    overlap_score = _related_overlap(left, right)
    score += overlap_score * 0.1
    if overlap_score > 0:
        reasons.append("overlapping exhibitions/articles")

    return score, reasons


@router.get("/semantic/artists")
async def semantic_artists(
    q: str,
    location: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    metrics.increment("semantic_queries")
    query_embedding = create_embedding(q)
    records = await crud.search_records(
        db,
        record_type="artist",
        location=location,
        sort_by="completeness",
        skip=0,
        limit=1000,
    )

    ranked: list[tuple[Record, float]] = []
    for record in records:
        score = cosine_similarity(query_embedding, crud.parse_embedding(record.embedding_vector))
        ranking_boost = (record.completeness_score / 1000) + min(record.confidence_score / 1000, 0.1)
        ranked.append((record, round(score + ranking_boost, 6)))

    ranked.sort(key=lambda item: item[1], reverse=True)
    items = [
        {
            "id": record.id,
            "source_id": record.source_id,
            "name": record.title,
            "bio": record.bio,
            "semantic_score": score,
            "completeness_score": record.completeness_score,
            "relationships": record.relationship_count if hasattr(record, "relationship_count") else None,
        }
        for record, score in ranked[skip : skip + limit]
    ]
    return {"items": items, "total": len(ranked), "skip": skip, "limit": limit}


@router.get("/semantic/exhibitions")
async def semantic_exhibitions(
    q: str,
    location: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    metrics.increment("semantic_queries")
    query_embedding = create_embedding(q)
    records = await crud.search_records(
        db,
        record_type="exhibition",
        location=location,
        sort_by="completeness",
        skip=0,
        limit=1000,
    )
    ranked = []
    for record in records:
        score = cosine_similarity(query_embedding, crud.parse_embedding(record.embedding_vector))
        recency_bonus = 0.05 if record.created_at and (datetime.now(UTC) - record.created_at).days < 120 else 0.0
        ranked.append((record, round(score + recency_bonus + (record.completeness_score / 1000), 6)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    items = [
        {
            "id": record.id,
            "source_id": record.source_id,
            "title": record.title,
            "description": record.description,
            "semantic_score": score,
            "venue_name": record.venue_name,
            "completeness_score": record.completeness_score,
        }
        for record, score in ranked[skip : skip + limit]
    ]
    return {"items": items, "total": len(ranked), "skip": skip, "limit": limit}


@router.get("/related/artists/{artist_id}")
async def related_artists(
    artist_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    anchor = await crud.get_record(db, artist_id)
    if anchor is None or anchor.record_type != "artist":
        raise HTTPException(status_code=404, detail="Artist not found")

    artist_records = await crud.search_records(db, record_type="artist", skip=0, limit=1000)
    candidates: list[tuple[Record, float, dict[str, float]]] = []
    for candidate in artist_records:
        if candidate.id == anchor.id:
            continue
        bio_score = crud.embedding_similarity(anchor, candidate)
        exhibition_overlap = _related_overlap(anchor, candidate)
        location_score = _location_similarity(anchor, candidate)
        score = round((bio_score * 0.6) + (exhibition_overlap * 0.25) + (location_score * 0.15), 6)
        if score <= 0:
            continue
        candidates.append(
            (
                candidate,
                score,
                {
                    "bio_similarity": round(bio_score, 6),
                    "exhibition_overlap": round(exhibition_overlap, 6),
                    "location_proximity": round(location_score, 6),
                },
            )
        )

    candidates.sort(key=lambda item: item[1], reverse=True)
    return {
        "artist_id": anchor.id,
        "items": [
            {
                "id": record.id,
                "name": record.title,
                "score": score,
                "signals": signals,
            }
            for record, score, signals in candidates[:limit]
        ],
    }


@router.get("/suggest/duplicates")
async def suggest_duplicates(
    min_score: float = 0.7,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    artist_records = await crud.search_records(db, record_type="artist", skip=0, limit=1000)
    candidates: list[dict[str, object]] = []

    for index, left in enumerate(artist_records):
        for right in artist_records[index + 1 :]:
            score, reasons = _score_duplicate_candidate(left, right)
            if score < min_score:
                continue
            reason = ", ".join(reasons) if reasons else "multi-signal similarity"
            review = await crud.upsert_duplicate_review(
                db,
                left_record_id=left.id,
                right_record_id=right.id,
                similarity_score=int(round(score * 100)),
                reason=reason,
            )
            candidates.append(
                {
                    "review_id": review.id,
                    "left_id": left.id,
                    "left_name": left.title,
                    "right_id": right.id,
                    "right_name": right.title,
                    "similarity_score": round(score, 6),
                    "reason": reason,
                    "review_status": review.status,
                    "reviewed_by": review.reviewed_by,
                }
            )

    candidates.sort(key=lambda item: float(item["similarity_score"]), reverse=True)
    return {"items": candidates[:limit], "total": len(candidates)}


@router.get("/duplicates/reviews")
async def list_duplicate_reviews(
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    try:
        reviews = await crud.list_duplicate_reviews(db, status=status, skip=skip, limit=limit)
        total = await crud.count_duplicate_reviews(db, status=status)
        items: list[dict[str, object]] = []
        for review in reviews:
            left = await crud.get_record(db, review.left_record_id)
            right = await crud.get_record(db, review.right_record_id)
            items.append(
                {
                    "id": review.id,
                    "left_id": review.left_record_id,
                    "left_name": left.title if left else None,
                    "right_id": review.right_record_id,
                    "right_name": right.title if right else None,
                    "similarity_score": review.similarity_score / 100,
                    "reason": review.reason,
                    "status": review.status,
                    "reviewed_by": review.reviewed_by,
                    "reviewed_at": review.reviewed_at,
                    "merge_target_id": review.merge_target_id,
                }
            )
        return {"items": items, "total": total, "skip": skip, "limit": limit}
    except SQLAlchemyError as exc:
        logger.error(
            "duplicate_reviews_db_error",
            status=status,
            skip=skip,
            limit=limit,
            error=str(exc),
        )
        return {"items": [], "total": 0, "skip": skip, "limit": limit}


@router.post("/merge/artists")
async def merge_artists(
    payload: MergeArtistsRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("merge")),
):
    primary = await crud.get_record(db, payload.primary_id)
    secondary = await crud.get_record(db, payload.secondary_id)
    if primary is None or secondary is None:
        raise HTTPException(status_code=404, detail="Artist record not found")
    if primary.record_type != "artist" or secondary.record_type != "artist":
        raise HTTPException(status_code=400, detail="Only artist records can be merged")
    if primary.id == secondary.id:
        raise HTTPException(status_code=400, detail="Cannot merge identical records")

    merged_values = {
        "title": primary.title or secondary.title,
        "description": primary.description or secondary.description,
        "bio": primary.bio or secondary.bio,
        "nationality": primary.nationality or secondary.nationality,
        "city": primary.city or secondary.city,
        "country": primary.country or secondary.country,
        "website_url": primary.website_url or secondary.website_url,
        "instagram_url": primary.instagram_url or secondary.instagram_url,
        "source_url": primary.source_url or secondary.source_url,
        "confidence_score": max(primary.confidence_score, secondary.confidence_score),
        "completeness_score": max(primary.completeness_score, secondary.completeness_score),
    }

    primary_raw = _parse_json(primary.raw_data)
    secondary_raw = _parse_json(secondary.raw_data)
    merged_from = primary_raw.get("merged_from", [])
    if secondary.id not in merged_from:
        merged_from.append(secondary.id)
    raw_data = {
        **secondary_raw,
        **primary_raw,
        "merged_from": merged_from,
        "merge_timestamp": datetime.now(UTC).isoformat(),
        "provenance": {
            "primary_source_id": primary.source_id,
            "secondary_source_id": secondary.source_id,
        },
    }
    merged_values["raw_data"] = json.dumps(raw_data)

    merged_record = await crud.update_record(db, primary.id, **merged_values)

    relationships = await crud.list_relationships_for_record(
        db,
        source_id=secondary.source_id,
        record_id=secondary.id,
    )
    relationships_snapshot = [
        {
            "source_id": rel.source_id,
            "from_record_id": rel.from_record_id,
            "to_record_id": rel.to_record_id,
            "relationship_type": rel.relationship_type,
            "metadata_json": _parse_json(rel.metadata_json),
        }
        for rel in relationships
    ]
    merge_history = await crud.create_merge_history(
        db,
        primary_record=primary,
        secondary_record=secondary,
        relationships_snapshot=relationships_snapshot,
    )
    for rel in relationships:
        from_id = merged_record.id if rel.from_record_id == secondary.id else rel.from_record_id
        to_id = merged_record.id if rel.to_record_id == secondary.id else rel.to_record_id
        if from_id == to_id:
            continue
        await crud.upsert_entity_relationship(
            db,
            source_id=rel.source_id,
            from_record_id=from_id,
            to_record_id=to_id,
            relationship_type=rel.relationship_type,
            metadata=_parse_json(rel.metadata_json),
        )

    await db.delete(secondary)
    await db.commit()

    metrics.increment("merge_actions")
    await crud.create_audit_action(
        db,
        action_type="merge",
        source_id=merged_record.source_id,
        record_id=merged_record.id,
        affected_record_ids=[merged_record.id, payload.secondary_id],
        details={"primary_id": payload.primary_id, "secondary_id": payload.secondary_id},
    )

    return {
        "merge_id": merge_history.id,
        "merged_id": merged_record.id,
        "removed_id": payload.secondary_id,
        "status": "merged",
    }


@router.post("/duplicates/decision")
async def decide_duplicate(
    payload: DuplicateDecisionRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("merge")),
):
    allowed_decisions = {"merge", "ignore", "not_duplicate", "reviewed"}
    if payload.decision not in allowed_decisions:
        raise HTTPException(status_code=400, detail="Invalid decision")

    review = await crud.get_duplicate_review_by_pair(
        db,
        left_record_id=payload.left_id,
        right_record_id=payload.right_id,
    )
    if review is None:
        review = await crud.upsert_duplicate_review(
            db,
            left_record_id=payload.left_id,
            right_record_id=payload.right_id,
            similarity_score=0,
            reason="manual review",
        )

    merge_target_id = payload.primary_id if payload.decision == "merge" else None
    review = await crud.set_duplicate_review_status(
        db,
        review_id=review.id,
        status=payload.decision,
        reviewed_by=payload.reviewer,
        merge_target_id=merge_target_id,
    )

    if payload.decision == "merge":
        primary_id = payload.primary_id or payload.left_id
        secondary_id = payload.right_id if primary_id == payload.left_id else payload.left_id
        await merge_artists(MergeArtistsRequest(primary_id=primary_id, secondary_id=secondary_id), db)

    await crud.create_audit_action(
        db,
        action_type=f"duplicate_{payload.decision}",
        user_id=payload.reviewer,
        record_id=review.left_record_id,
        affected_record_ids=[review.left_record_id, review.right_record_id],
        details={"review_id": review.id, "merge_target_id": merge_target_id},
    )

    return {
        "id": review.id,
        "status": review.status,
        "reviewed_by": review.reviewed_by,
        "reviewed_at": review.reviewed_at,
        "merge_target_id": review.merge_target_id,
    }


@router.post("/ask")
async def ask(payload: AskRequest, db: AsyncSession = Depends(get_db)):
    metrics.increment("semantic_queries")

    query = payload.query.lower()
    location = None
    if " in " in query:
        location = payload.query.rsplit(" in ", 1)[-1].strip()

    semantic = await semantic_artists(
        q=payload.query,
        location=location,
        skip=0,
        limit=payload.limit,
        db=db,
    )

    return {
        "query": payload.query,
        "intent": "artist_similarity" if "similar" in query else "semantic_lookup",
        "results": semantic["items"],
    }
