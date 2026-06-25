"""
Research Project API — CRUD + pipeline trigger + file upload + downloads.
"""
from __future__ import annotations

import re
import uuid
import magic
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import structlog

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.core.database import get_db
from app.core.security import verify_clerk_token, get_user_id
from app.core.config import settings
from app.models.research import ResearchProject, UploadedFile, PipelineStatus
from app.schemas.research import (
    ResearchProjectCreate,
    ResearchProjectResponse,
    ResearchProjectDetail,
    FileUploadResponse,
    ProjectListResponse,
    DownloadLinkResponse,
)
from app.services.storage.s3 import S3Service
from app.tasks.pipeline import run_research_pipeline

router = APIRouter(prefix="/research", tags=["research"])
logger = structlog.get_logger()
s3_service = S3Service()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
}


@router.post("/projects", response_model=ResearchProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ResearchProjectCreate,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    user_id = get_user_id(token)
    project = ResearchProject(
        id=uuid.uuid4(),
        user_id=user_id,
        title=payload.title,
        domain=payload.domain,
        keywords=payload.keywords,
        objectives=payload.objectives,
        problem_statement=payload.problem_statement,
        scope=payload.scope or "",
        journal_type=payload.journal_type,
        citation_style=payload.citation_style,
        preferred_word_count=payload.preferred_word_count,
        writing_tone=payload.writing_tone.value,
        status=PipelineStatus.PENDING,
        progress_log=[],
        error_log=[],
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    logger.info("Project created", project_id=str(project.id), user_id=user_id)
    return project


@router.post("/projects/{project_id}/files", response_model=List[FileUploadResponse])
async def upload_files(
    project_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    user_id = get_user_id(token)
    project = await _get_project_or_404(db, project_id, user_id)

    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    responses = []

    for upload_file in files:
        content = await upload_file.read()

        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File {upload_file.filename} exceeds {settings.MAX_FILE_SIZE_MB}MB limit",
            )

        # Validate MIME type using python-magic (magic bytes, not filename)
        detected_mime = magic.from_buffer(content, mime=True)
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File type {detected_mime} not supported",
            )

        file_id = uuid.uuid4()
        ext = Path(upload_file.filename).suffix.lower()
        s3_key = f"uploads/{project_id}/{file_id}{ext}"

        await s3_service.upload_bytes(content, s3_key, detected_mime, bucket=settings.S3_BUCKET_UPLOADS)

        db_file = UploadedFile(
            id=file_id,
            project_id=project_id,
            user_id=user_id,
            original_filename=upload_file.filename,
            file_type=ext.lstrip("."),
            mime_type=detected_mime,
            file_size_bytes=len(content),
            s3_key=s3_key,
            extraction_status="pending",
        )
        db.add(db_file)
        responses.append(FileUploadResponse(
            file_id=file_id,
            filename=upload_file.filename,
            file_type=ext.lstrip("."),
            size_bytes=len(content),
            extraction_status="pending",
        ))

    await db.flush()
    logger.info("Files uploaded", project_id=str(project_id), count=len(files))
    return responses


@router.post("/projects/{project_id}/start", response_model=ResearchProjectResponse)
async def start_pipeline(
    project_id: uuid.UUID,
    additional_instructions: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    user_id = get_user_id(token)
    project = await _get_project_or_404(db, project_id, user_id)

    if project.status not in (PipelineStatus.PENDING, PipelineStatus.FAILED):
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already in status: {project.status.value}",
        )

    # Load files for pipeline context
    files_result = await db.execute(
        select(UploadedFile).where(UploadedFile.project_id == project_id)
    )
    uploaded_files = files_result.scalars().all()

    # Prepare initial state (file content loaded by extraction agent from S3)
    initial_state = {
        "project_id": str(project_id),
        "user_id": user_id,
        "title": project.title,
        "domain": project.domain,
        "keywords": project.keywords,
        "objectives": project.objectives,
        "problem_statement": project.problem_statement,
        "scope": project.scope or "",
        "journal_type": project.journal_type.value,
        "citation_style": project.citation_style.value,
        "preferred_word_count": project.preferred_word_count,
        "writing_tone": project.writing_tone,
        "additional_instructions": additional_instructions or "",
        "uploaded_files_content": [
            {"s3_key": f.s3_key, "filename": f.original_filename, "file_type": f.file_type}
            for f in uploaded_files
        ],
        "current_step": "starting",
    }

    # Dispatch Celery task
    task = run_research_pipeline.delay(str(project_id), initial_state)

    await db.execute(
        update(ResearchProject)
        .where(ResearchProject.id == project_id)
        .values(status=PipelineStatus.EXTRACTING, celery_task_id=task.id)
    )

    logger.info("Pipeline started", project_id=str(project_id), task_id=task.id)
    await db.refresh(project)
    return project


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    user_id = get_user_id(token)
    query = select(ResearchProject).where(ResearchProject.user_id == user_id)

    if status_filter:
        try:
            query = query.where(ResearchProject.status == PipelineStatus(status_filter))
        except ValueError:
            pass

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(ResearchProject.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        items=projects,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/projects/{project_id}", response_model=ResearchProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    user_id = get_user_id(token)
    return await _get_project_or_404(db, project_id, user_id)


@router.get("/projects/{project_id}/download", response_model=DownloadLinkResponse)
async def get_download_links(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    user_id = get_user_id(token)
    project = await _get_project_or_404(db, project_id, user_id)

    if project.status != PipelineStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Project not yet completed")

    expiry = 3600
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiry)

    docx_url = await s3_service.generate_presigned_url(project.output_docx_key, expiry=expiry) if project.output_docx_key else None
    cover_url = await s3_service.generate_presigned_url(project.output_cover_letter_key, expiry=expiry) if project.output_cover_letter_key else None
    reviewer_url = await s3_service.generate_presigned_url(project.output_reviewer_key, expiry=expiry) if project.output_reviewer_key else None
    report_url = await s3_service.generate_presigned_url(project.output_report_key, expiry=expiry) if project.output_report_key else None

    return DownloadLinkResponse(
        docx_url=docx_url,
        cover_letter_url=cover_url,
        reviewer_response_url=reviewer_url,
        report_url=report_url,
        expires_at=expires_at,
    )



# ─── LaTeX export ─────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/latex")
async def download_latex(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    """Return a publication-ready .tex file for the completed project."""
    from fastapi.responses import Response
    from app.utils.latex_export import generate_latex
    user_id = get_user_id(token)
    project = await _get_project_or_404(db, project_id, user_id)
    if project.status.value != "completed":
        raise HTTPException(status_code=400, detail="Paper not completed yet")
    project_dict = {c.name: getattr(project, c.name) for c in project.__table__.columns}
    project_dict["references_data"] = project.references_data or []
    tex = generate_latex(project_dict)
    filename = re.sub(r"[^\w\-]", "_", (project.title or "paper")[:60]) + ".tex"
    return Response(
        content=tex,
        media_type="application/x-tex",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── BibTeX export ────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/bibtex")
async def download_bibtex(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    """Return a .bib file with all references for Zotero/Mendeley/EndNote."""
    from fastapi.responses import Response
    from app.utils.latex_export import generate_bibtex
    user_id = get_user_id(token)
    project = await _get_project_or_404(db, project_id, user_id)
    if project.status.value != "completed":
        raise HTTPException(status_code=400, detail="Paper not completed yet")
    refs = project.references_data or []
    bib = generate_bibtex(refs)
    filename = re.sub(r"[^\w\-]", "_", (project.title or "references")[:60]) + ".bib"
    return Response(
        content=bib,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Journal recommendations ──────────────────────────────────────────────

_DOMAIN_JOURNALS: dict = {
    "computer science": [
        {"name": "Nature Machine Intelligence", "issn": "2522-5839", "impact_factor": 25.9, "quartile": "Q1", "publisher": "Nature"},
        {"name": "IEEE Transactions on Neural Networks and Learning Systems", "issn": "2162-237X", "impact_factor": 14.3, "quartile": "Q1", "publisher": "IEEE"},
        {"name": "Information Fusion", "issn": "1566-2535", "impact_factor": 18.6, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "Expert Systems with Applications", "issn": "0957-4174", "impact_factor": 8.5, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "Computers & Electrical Engineering", "issn": "0045-7906", "impact_factor": 4.3, "quartile": "Q2", "publisher": "Elsevier"},
    ],
    "machine learning": [
        {"name": "Journal of Machine Learning Research", "issn": "1532-4435", "impact_factor": 6.0, "quartile": "Q1", "publisher": "JMLR"},
        {"name": "Neural Networks", "issn": "0893-6080", "impact_factor": 7.8, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "Pattern Recognition", "issn": "0031-3203", "impact_factor": 8.0, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "issn": "0162-8828", "impact_factor": 23.6, "quartile": "Q1", "publisher": "IEEE"},
        {"name": "Knowledge-Based Systems", "issn": "0950-7051", "impact_factor": 8.8, "quartile": "Q1", "publisher": "Elsevier"},
    ],
    "medicine": [
        {"name": "The Lancet", "issn": "0140-6736", "impact_factor": 202.7, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "JAMA Internal Medicine", "issn": "2168-6106", "impact_factor": 39.0, "quartile": "Q1", "publisher": "AMA"},
        {"name": "BMJ", "issn": "0959-8138", "impact_factor": 105.7, "quartile": "Q1", "publisher": "BMJ"},
        {"name": "PLOS Medicine", "issn": "1549-1277", "impact_factor": 15.8, "quartile": "Q1", "publisher": "PLOS"},
        {"name": "Journal of Clinical Investigation", "issn": "0021-9738", "impact_factor": 15.9, "quartile": "Q1", "publisher": "JCI"},
    ],
    "biology": [
        {"name": "Nature Methods", "issn": "1548-7105", "impact_factor": 48.0, "quartile": "Q1", "publisher": "Nature"},
        {"name": "PLOS Biology", "issn": "1544-9173", "impact_factor": 9.8, "quartile": "Q1", "publisher": "PLOS"},
        {"name": "Cell Reports", "issn": "2211-1247", "impact_factor": 9.1, "quartile": "Q1", "publisher": "Cell Press"},
        {"name": "iScience", "issn": "2589-0042", "impact_factor": 6.1, "quartile": "Q1", "publisher": "Cell Press"},
        {"name": "BMC Biology", "issn": "1741-7007", "impact_factor": 7.0, "quartile": "Q1", "publisher": "BMC"},
    ],
    "chemistry": [
        {"name": "Journal of the American Chemical Society", "issn": "0002-7863", "impact_factor": 16.4, "quartile": "Q1", "publisher": "ACS"},
        {"name": "Angewandte Chemie", "issn": "0570-0833", "impact_factor": 16.8, "quartile": "Q1", "publisher": "Wiley"},
        {"name": "Chemical Science", "issn": "2041-6520", "impact_factor": 8.4, "quartile": "Q1", "publisher": "RSC"},
        {"name": "ACS Applied Materials & Interfaces", "issn": "1944-8244", "impact_factor": 10.4, "quartile": "Q1", "publisher": "ACS"},
        {"name": "Molecules", "issn": "1420-3049", "impact_factor": 4.6, "quartile": "Q2", "publisher": "MDPI"},
    ],
    "engineering": [
        {"name": "Engineering Applications of Artificial Intelligence", "issn": "0952-1976", "impact_factor": 8.0, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "Applied Soft Computing", "issn": "1568-4946", "impact_factor": 8.7, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "Reliability Engineering & System Safety", "issn": "0951-8320", "impact_factor": 9.4, "quartile": "Q1", "publisher": "Elsevier"},
        {"name": "IEEE Access", "issn": "2169-3536", "impact_factor": 3.9, "quartile": "Q2", "publisher": "IEEE"},
        {"name": "International Journal of Engineering Science", "issn": "0020-7225", "impact_factor": 12.1, "quartile": "Q1", "publisher": "Elsevier"},
    ],
    "physics": [
        {"name": "Physical Review Letters", "issn": "0031-9007", "impact_factor": 8.6, "quartile": "Q1", "publisher": "APS"},
        {"name": "npj Computational Materials", "issn": "2057-3960", "impact_factor": 12.2, "quartile": "Q1", "publisher": "Nature"},
        {"name": "Journal of Physics D: Applied Physics", "issn": "0022-3727", "impact_factor": 4.0, "quartile": "Q2", "publisher": "IOP"},
        {"name": "Scientific Reports", "issn": "2045-2322", "impact_factor": 4.6, "quartile": "Q2", "publisher": "Nature"},
        {"name": "Results in Physics", "issn": "2211-3797", "impact_factor": 5.3, "quartile": "Q2", "publisher": "Elsevier"},
    ],
    "psychology": [
        {"name": "Psychological Science", "issn": "0956-7976", "impact_factor": 7.7, "quartile": "Q1", "publisher": "Sage"},
        {"name": "Journal of Abnormal Psychology", "issn": "0021-843X", "impact_factor": 6.1, "quartile": "Q1", "publisher": "APA"},
        {"name": "Frontiers in Psychology", "issn": "1664-1078", "impact_factor": 4.2, "quartile": "Q2", "publisher": "Frontiers"},
        {"name": "PLOS ONE", "issn": "1932-6203", "impact_factor": 3.7, "quartile": "Q2", "publisher": "PLOS"},
        {"name": "Heliyon", "issn": "2405-8440", "impact_factor": 4.0, "quartile": "Q2", "publisher": "Cell Press"},
    ],
    "default": [
        {"name": "Scientific Reports", "issn": "2045-2322", "impact_factor": 4.6, "quartile": "Q2", "publisher": "Nature"},
        {"name": "PLOS ONE", "issn": "1932-6203", "impact_factor": 3.7, "quartile": "Q2", "publisher": "PLOS"},
        {"name": "Heliyon", "issn": "2405-8440", "impact_factor": 4.0, "quartile": "Q2", "publisher": "Cell Press"},
        {"name": "IEEE Access", "issn": "2169-3536", "impact_factor": 3.9, "quartile": "Q2", "publisher": "IEEE"},
        {"name": "Frontiers in Research", "issn": "2673-6853", "impact_factor": 3.2, "quartile": "Q2", "publisher": "Frontiers"},
    ],
}


@router.get("/projects/{project_id}/journal-recommendations")
async def journal_recommendations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(verify_clerk_token),
):
    """Return top 5 journal recommendations based on domain + keywords."""
    user_id = get_user_id(token)
    project = await _get_project_or_404(db, project_id, user_id)
    domain_lower = (project.domain or "").lower()

    # Fuzzy match domain
    matched = None
    for key in _DOMAIN_JOURNALS:
        if key == "default":
            continue
        if key in domain_lower or any(word in domain_lower for word in key.split()):
            matched = key
            break

    journals = _DOMAIN_JOURNALS.get(matched or "default")
    return {
        "domain": project.domain,
        "matched_category": matched or "general",
        "recommendations": journals,
        "advice": (
            f"Based on your domain '{project.domain}', we recommend targeting Q1 journals "
            f"with impact factors above 5.0 for maximum visibility. "
            f"Consider Open Access options for wider readership."
        ),
    }


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID, user_id: str) -> ResearchProject:
    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.user_id == user_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
