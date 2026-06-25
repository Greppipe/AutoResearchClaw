"""
Admin API endpoints — dashboard stats, user management, system config.
Requires 'admin' role via Clerk.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import structlog

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.security import require_role
from app.models.research import ResearchProject, UploadedFile, PipelineStatus
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])
logger = structlog.get_logger()


class SystemStats(BaseModel):
    total_projects: int
    completed_projects: int
    failed_projects: int
    in_progress_projects: int
    total_users: int
    avg_editor_score: float
    avg_plagiarism_score: float
    avg_ai_detection_score: float
    avg_pipeline_iterations: float
    total_files_uploaded: int
    projects_today: int
    projects_this_week: int


class ProjectAdminItem(BaseModel):
    id: str
    user_id: str
    title: str
    domain: str
    status: str
    editor_score: Optional[float]
    plagiarism_score: Optional[float]
    ai_detection_score: Optional[float]
    pipeline_iteration: int
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DomainStats(BaseModel):
    domain: str
    count: int
    avg_score: float


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_role("admin")),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    total = (await db.execute(select(func.count()).select_from(ResearchProject))).scalar_one()
    completed = (await db.execute(select(func.count()).select_from(ResearchProject).where(ResearchProject.status == PipelineStatus.COMPLETED))).scalar_one()
    failed = (await db.execute(select(func.count()).select_from(ResearchProject).where(ResearchProject.status == PipelineStatus.FAILED))).scalar_one()
    in_progress = total - completed - failed - (await db.execute(select(func.count()).select_from(ResearchProject).where(ResearchProject.status == PipelineStatus.PENDING))).scalar_one()
    unique_users = (await db.execute(select(func.count(func.distinct(ResearchProject.user_id))))).scalar_one()

    def _avg(col):
        return select(func.avg(col)).select_from(ResearchProject).where(col.isnot(None))

    avg_score = (await db.execute(_avg(ResearchProject.editor_score))).scalar_one() or 0.0
    avg_plag = (await db.execute(_avg(ResearchProject.plagiarism_score))).scalar_one() or 0.0
    avg_ai = (await db.execute(_avg(ResearchProject.ai_detection_score))).scalar_one() or 0.0
    avg_iter = (await db.execute(select(func.avg(ResearchProject.pipeline_iteration)))).scalar_one() or 0.0
    total_files = (await db.execute(select(func.count()).select_from(UploadedFile))).scalar_one()
    today_count = (await db.execute(select(func.count()).select_from(ResearchProject).where(ResearchProject.created_at >= today_start))).scalar_one()
    week_count = (await db.execute(select(func.count()).select_from(ResearchProject).where(ResearchProject.created_at >= week_start))).scalar_one()

    return SystemStats(
        total_projects=total,
        completed_projects=completed,
        failed_projects=failed,
        in_progress_projects=in_progress,
        total_users=unique_users,
        avg_editor_score=round(avg_score, 2),
        avg_plagiarism_score=round(avg_plag, 2),
        avg_ai_detection_score=round(avg_ai, 2),
        avg_pipeline_iterations=round(avg_iter, 2),
        total_files_uploaded=total_files,
        projects_today=today_count,
        projects_this_week=week_count,
    )


@router.get("/projects", response_model=List[ProjectAdminItem])
async def list_all_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status_filter: Optional[str] = None,
    user_id_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_role("admin")),
):
    query = select(ResearchProject)
    if status_filter:
        try:
            query = query.where(ResearchProject.status == PipelineStatus(status_filter))
        except ValueError:
            pass
    if user_id_filter:
        query = query.where(ResearchProject.user_id == user_id_filter)

    query = query.order_by(ResearchProject.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/domain-stats", response_model=List[DomainStats])
async def get_domain_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_role("admin")),
):
    result = await db.execute(
        select(
            ResearchProject.domain,
            func.count(ResearchProject.id).label("count"),
            func.avg(ResearchProject.editor_score).label("avg_score"),
        )
        .group_by(ResearchProject.domain)
        .order_by(func.count(ResearchProject.id).desc())
        .limit(20)
    )
    return [
        DomainStats(domain=row.domain, count=row.count, avg_score=round(row.avg_score or 0.0, 2))
        for row in result.all()
    ]
