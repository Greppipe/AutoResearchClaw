from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyHttpUrl
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "SCI Research Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(min_length=32)
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:3000"])

    # Database
    DATABASE_URL: str = Field(alias="DATABASE_URL")
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_CACHE_TTL: int = 3600

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_WORKER_CONCURRENCY: int = 4

    # AI / Claude
    ANTHROPIC_API_KEY: str
    CLAUDE_WRITING_MODEL: str = "claude-opus-4-7"
    CLAUDE_FAST_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 8192
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "sci-research-platform"

    # Vector DB (Qdrant)
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "research_papers"

    # Object Storage (MinIO / S3)
    S3_ENDPOINT_URL: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_UPLOADS: str = "sci-uploads"
    S3_BUCKET_OUTPUTS: str = "sci-outputs"
    S3_REGION: str = "us-east-1"

    # Auth (Clerk)
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: str
    CLERK_JWKS_URL: str

    # External APIs
    TAVILY_API_KEY: str
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    SCITE_API_KEY: Optional[str] = None
    # Literature sources — all free, register at links below
    IEEE_XPLORE_API_KEY: Optional[str] = None      # developer.ieee.org — CS/EE/engineering
    SPRINGER_API_KEY: Optional[str] = None          # dev.springernature.com — Springer/Nature
    NCBI_API_KEY: Optional[str] = None              # ncbi.nlm.nih.gov/account — PubMed 10x rate
    ELSEVIER_API_KEY: Optional[str] = None          # dev.elsevier.com — Scopus citation database

    # Tesseract OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # Agent Settings
    MAX_PIPELINE_ITERATIONS: int = 10
    EDITOR_MIN_SCORE: float = 9.0
    MAX_PLAGIARISM_PERCENT: float = 15.0
    MAX_AI_DETECTION_PERCENT: float = 5.0

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # File Upload Limits
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "doc", "docx", "ppt", "pptx",
        "xls", "xlsx", "csv", "txt", "png",
        "jpg", "jpeg", "tiff", "bmp"
    ]

    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    GRAFANA_URL: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
