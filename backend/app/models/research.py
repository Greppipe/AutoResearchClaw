from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, Boolean,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class PipelineStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    RESEARCHING = "researching"
    AUTHENTICATING = "authenticating"
    PLAGIARISM_CHECK = "plagiarism_check"
    HUMANIZING = "humanizing"
    AUDITING = "auditing"
    EDITOR_REVIEW = "editor_review"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CitationStyle(str, enum.Enum):
    APA = "apa"
    MLA = "mla"
    IEEE = "ieee"
    CHICAGO = "chicago"
    HARVARD = "harvard"
    VANCOUVER = "vancouver"
    NATURE = "nature"
    ACS = "acs"


class JournalType(str, enum.Enum):
    SCI = "sci"
    SCOPUS = "scopus"
    WEB_OF_SCIENCE = "web_of_science"
    IEEE = "ieee"
    NATURE = "nature"
    ELSEVIER = "elsevier"
    SPRINGER = "springer"
    PLOS = "plos"


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)

    # Research Inputs
    title = Column(String(500), nullable=False)
    domain = Column(String(255), nullable=False)
    keywords = Column(JSONB, default=list)
    objectives = Column(Text)
    problem_statement = Column(Text)
    scope = Column(Text)
    journal_type = Column(SAEnum(JournalType), default=JournalType.SCI)
    citation_style = Column(SAEnum(CitationStyle), default=CitationStyle.IEEE)
    preferred_word_count = Column(Integer, default=8000)
    writing_tone = Column(String(100), default="academic")

    # Pipeline State
    status = Column(SAEnum(PipelineStatus), default=PipelineStatus.PENDING, index=True)
    celery_task_id = Column(String(255), nullable=True)
    pipeline_iteration = Column(Integer, default=0)
    editor_score = Column(Float, nullable=True)
    editor_feedback = Column(JSONB, nullable=True)

    # Generated Content (structured sections)
    abstract = Column(Text, nullable=True)
    introduction = Column(Text, nullable=True)
    literature_review = Column(Text, nullable=True)
    methodology = Column(Text, nullable=True)
    results = Column(Text, nullable=True)
    discussion = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    references_data = Column(JSONB, default=list)
    figures_data = Column(JSONB, default=list)
    tables_data = Column(JSONB, default=list)

    # Visualisation data (persisted for API and preview)
    chart_data = Column(JSONB, default=list)
    table_data = Column(JSONB, default=list)
    methodology_visuals = Column(JSONB, default=list)
    discussion_visuals = Column(JSONB, default=list)

    # Validation Scores
    plagiarism_score = Column(Float, nullable=True)
    ai_detection_score = Column(Float, nullable=True)
    trust_score = Column(Float, nullable=True)
    novelty_score = Column(Float, nullable=True)

    # Output Files
    output_docx_key = Column(String(500), nullable=True)
    output_cover_letter_key = Column(String(500), nullable=True)
    output_reviewer_key = Column(String(500), nullable=True)
    output_report_key = Column(String(500), nullable=True)

    # Progress Tracking
    progress_log = Column(JSONB, default=list)
    error_log = Column(JSONB, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    uploaded_files = relationship("UploadedFile", back_populates="project", cascade="all, delete-orphan")
    pipeline_steps = relationship("PipelineStep", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_projects_user_status", "user_id", "status"),
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False)

    original_filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    s3_key = Column(String(500), nullable=False)

    # Extraction Results
    extracted_text = Column(Text, nullable=True)
    extracted_metadata = Column(JSONB, nullable=True)
    extraction_status = Column(String(50), default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("ResearchProject", back_populates="uploaded_files")


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)

    step_name = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)
    iteration = Column(Integer, default=0)
    status = Column(String(50), default="pending")

    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    score = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("ResearchProject", back_populates="pipeline_steps")

    __table_args__ = (
        Index("ix_pipeline_steps_project_step", "project_id", "step_name"),
    )


class Reference(Base):
    __tablename__ = "references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)

    doi = Column(String(255), nullable=True, index=True)
    title = Column(Text, nullable=False)
    authors = Column(JSONB, default=list)
    journal = Column(String(500), nullable=True)
    year = Column(Integer, nullable=True)
    volume = Column(String(50), nullable=True)
    issue = Column(String(50), nullable=True)
    pages = Column(String(100), nullable=True)
    url = Column(String(1000), nullable=True)

    verified = Column(Boolean, default=False)
    verification_source = Column(String(100), nullable=True)
    citation_count = Column(Integer, nullable=True)
    trust_score = Column(Float, nullable=True)

    formatted_apa = Column(Text, nullable=True)
    formatted_ieee = Column(Text, nullable=True)
    formatted_mla = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
