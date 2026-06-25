from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class CitationStyle(str, Enum):
    APA = "apa"
    MLA = "mla"
    IEEE = "ieee"
    CHICAGO = "chicago"
    HARVARD = "harvard"
    VANCOUVER = "vancouver"
    NATURE = "nature"
    ACS = "acs"


class JournalType(str, Enum):
    SCI = "sci"
    SCOPUS = "scopus"
    WEB_OF_SCIENCE = "web_of_science"
    IEEE = "ieee"
    NATURE = "nature"
    ELSEVIER = "elsevier"
    SPRINGER = "springer"
    PLOS = "plos"


class WritingTone(str, Enum):
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    REVIEW = "review"
    CLINICAL = "clinical"
    ENGINEERING = "engineering"


class ResearchProjectCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=500, description="Research paper title")
    domain: str = Field(..., min_length=3, max_length=255)
    keywords: List[str] = Field(..., min_length=3, max_length=20)
    objectives: str = Field(..., min_length=50)
    problem_statement: str = Field(..., min_length=50)
    scope: Optional[str] = None
    journal_type: JournalType = JournalType.SCI
    citation_style: CitationStyle = CitationStyle.IEEE
    preferred_word_count: int = Field(default=8000, ge=3000, le=20000)
    writing_tone: WritingTone = WritingTone.ACADEMIC
    additional_instructions: Optional[str] = Field(None, max_length=2000)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        cleaned = [k.strip() for k in v if k.strip()]
        if len(cleaned) < 3:
            raise ValueError("At least 3 keywords required")
        return cleaned


class ResearchProjectResponse(BaseModel):
    id: UUID
    user_id: str
    title: str
    domain: str
    keywords: List[str]
    status: str
    pipeline_iteration: int
    editor_score: Optional[float]
    plagiarism_score: Optional[float]
    ai_detection_score: Optional[float]
    trust_score: Optional[float]
    novelty_score: Optional[float]
    progress_log: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchProjectDetail(ResearchProjectResponse):
    abstract: Optional[str]
    introduction: Optional[str]
    literature_review: Optional[str]
    methodology: Optional[str]
    results: Optional[str]
    discussion: Optional[str]
    conclusion: Optional[str]
    references_data: List[Dict[str, Any]] = Field(default_factory=list)
    figures_data: List[Dict[str, Any]] = Field(default_factory=list)
    tables_data: List[Dict[str, Any]] = Field(default_factory=list)
    chart_data: List[Dict[str, Any]] = Field(default_factory=list)
    table_data: List[Dict[str, Any]] = Field(default_factory=list)
    methodology_visuals: List[Dict[str, Any]] = Field(default_factory=list)
    discussion_visuals: List[Dict[str, Any]] = Field(default_factory=list)
    editor_feedback: Optional[Dict[str, Any]] = None
    output_docx_key: Optional[str] = None
    output_cover_letter_key: Optional[str] = None
    output_reviewer_key: Optional[str] = None
    output_report_key: Optional[str] = None
    completed_at: Optional[datetime] = None

    @field_validator(
        "references_data", "figures_data", "tables_data",
        "chart_data", "table_data", "methodology_visuals", "discussion_visuals",
        mode="before",
    )
    @classmethod
    def coerce_none_to_list(cls, v: Any) -> List:
        return v if v is not None else []


class PipelineProgressEvent(BaseModel):
    project_id: str
    step: str
    status: str
    message: str
    progress_percent: float
    iteration: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class EditorScoreReport(BaseModel):
    overall_score: float
    novelty_score: float
    methodology_score: float
    clarity_score: float
    literature_score: float = 0.0
    results_score: float = 0.0
    technical_depth_score: float = 0.0
    journal_readiness_score: float
    acceptance_probability: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    modules_to_retry: List[str]
    pass_threshold: bool


class ReferenceCreate(BaseModel):
    doi: Optional[str] = None
    title: str
    authors: List[str]
    journal: Optional[str] = None
    year: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    url: Optional[str] = None


class ReferenceResponse(ReferenceCreate):
    id: UUID
    verified: bool
    verification_source: Optional[str]
    citation_count: Optional[int]
    trust_score: Optional[float]
    formatted_ieee: Optional[str]
    formatted_apa: Optional[str]

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    file_id: UUID
    filename: str
    file_type: str
    size_bytes: int
    extraction_status: str


class ProjectListResponse(BaseModel):
    items: List[ResearchProjectResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class DownloadLinkResponse(BaseModel):
    docx_url: Optional[str]
    cover_letter_url: Optional[str]
    reviewer_response_url: Optional[str]
    report_url: Optional[str]
    expires_at: datetime
