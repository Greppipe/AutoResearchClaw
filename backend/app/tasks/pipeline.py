"""
Celery pipeline task — wraps LangGraph execution.
Properly initialises ALL ResearchState fields to avoid TypedDict errors.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
import structlog

from celery import shared_task
from sqlalchemy import update

from app.core.database import get_db_context
from app.models.research import ResearchProject, PipelineStatus
from app.agents.orchestrator.graph import pipeline_graph, ResearchState

logger = structlog.get_logger()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=3600,
    time_limit=3900,
    name="tasks.run_research_pipeline",
    acks_late=True,
)
def run_research_pipeline(self, project_id: str, initial_state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Pipeline task started", project_id=project_id, task_id=self.request.id)

    async def _execute():
        async with get_db_context() as db:
            await db.execute(
                update(ResearchProject)
                .where(ResearchProject.id == project_id)
                .values(status=PipelineStatus.EXTRACTING, celery_task_id=self.request.id)
            )

        # Build fully initialised state — every field must be present
        state: ResearchState = {
            # Project context from caller
            "project_id": initial_state["project_id"],
            "user_id": initial_state["user_id"],
            "title": initial_state["title"],
            "domain": initial_state["domain"],
            "keywords": initial_state["keywords"],
            "objectives": initial_state["objectives"],
            "problem_statement": initial_state["problem_statement"],
            "research_gap": initial_state.get("research_gap", ""),
            "hypothesis": initial_state.get("hypothesis", ""),
            "novel_contribution": initial_state.get("novel_contribution", ""),
            "scope": initial_state.get("scope", ""),
            "study_type": initial_state.get("study_type", "experimental"),
            "journal_type": initial_state["journal_type"],
            "citation_style": initial_state["citation_style"],
            "preferred_word_count": initial_state["preferred_word_count"],
            "writing_tone": initial_state["writing_tone"],
            "additional_instructions": initial_state.get("additional_instructions", ""),
            # Author & ethics metadata
            "author_name": initial_state.get("author_name", ""),
            "author_affiliation": initial_state.get("author_affiliation", ""),
            "all_authors": initial_state.get("all_authors", []),
            "funding_source": initial_state.get("funding_source", ""),
            "conflicts_of_interest_input": initial_state.get("conflicts_of_interest_input", ""),
            "ethics_statement_input": initial_state.get("ethics_statement_input", ""),
            "methodology_description": initial_state.get("methodology_description", ""),
            "dataset_description": initial_state.get("dataset_description", ""),
            "analysis_methods": initial_state.get("analysis_methods", ""),
            "tools_used": initial_state.get("tools_used", ""),
            "expected_findings": initial_state.get("expected_findings", ""),
            "research_significance": initial_state.get("research_significance", ""),
            # Files — {s3_key, filename, file_type} — extraction agent downloads from S3
            "uploaded_files_content": initial_state.get("uploaded_files_content", []),
            # All agent outputs start empty
            "extracted_data": {},
            "paper_sections": {},
            "suggested_figures": [],
            "suggested_tables": [],
            "references": [],
            "figures": [],
            "tables": [],
            "toc": [],
            "bibtex": None,
            # New visualisation fields
            "chart_data": [],
            "table_data": [],
            "methodology_visuals": [],
            "discussion_visuals": [],
            # DDI fields
            "ddi_brief": {},
            "ddi_chunks": 0,
            "ddi_grounded": False,
            # Module 0: populated by JournalIntelligenceAgent before any drafting
            "journal_constraints": {},
            # Module 1.5: populated by EvidenceMapperAgent before ResearchAgent writes
            "evidence_anchors": [],
            # Top-1% paper metadata
            "materials_and_methods": "",
            "author_contributions": "",
            "funding_disclosure": "",
            "conflicts_of_interest": "",
            "ethics_statement": "",
            "supplementary_notes": "",
            "plagiarism_score": 0.0,
            "ai_detection_score": 0.0,
            "trust_score": 0.0,
            "novelty_score": 0.0,
            "editor_score": 0.0,
            "editor_report": {},
            "modules_to_retry": [],
            # Structured repair instructions from EditorAgent — injected into agents on retry
            "repair_jobs": [],
            "iteration": 0,
            "current_step": "starting",
            "pipeline_complete": False,
            "error": None,
            "output_docx_key": None,
            "output_cover_letter_key": None,
            "output_reviewer_key": None,
            "output_report_key": None,
            "output_bibtex_key": None,
            "progress_log": [],
            "messages": [],
        }

        try:
            final_state = await pipeline_graph.ainvoke(
                state,
                config={"recursion_limit": 80},
            )

            async with get_db_context() as db:
                await db.execute(
                    update(ResearchProject)
                    .where(ResearchProject.id == project_id)
                    .values(
                        status=PipelineStatus.COMPLETED,
                        abstract=final_state["paper_sections"].get("abstract"),
                        introduction=final_state["paper_sections"].get("introduction"),
                        literature_review=final_state["paper_sections"].get("literature_review"),
                        methodology=(
                            final_state["paper_sections"].get("materials_and_methods")
                            or final_state["paper_sections"].get("methodology")
                        ),
                        results=final_state["paper_sections"].get("results"),
                        discussion=final_state["paper_sections"].get("discussion"),
                        conclusion=final_state["paper_sections"].get("conclusion"),
                        references_data=final_state.get("references", []),
                        figures_data=final_state.get("figures", []),
                        tables_data=final_state.get("tables", []),
                        chart_data=final_state.get("chart_data", []),
                        table_data=final_state.get("table_data", []),
                        methodology_visuals=final_state.get("methodology_visuals", []),
                        discussion_visuals=final_state.get("discussion_visuals", []),
                        plagiarism_score=final_state.get("plagiarism_score"),
                        ai_detection_score=final_state.get("ai_detection_score"),
                        trust_score=final_state.get("trust_score"),
                        novelty_score=final_state.get("novelty_score"),
                        editor_score=final_state.get("editor_score"),
                        editor_feedback=final_state.get("editor_report"),
                        pipeline_iteration=final_state.get("iteration", 0),
                        output_docx_key=final_state.get("output_docx_key"),
                        output_cover_letter_key=final_state.get("output_cover_letter_key"),
                        output_reviewer_key=final_state.get("output_reviewer_key"),
                        output_report_key=final_state.get("output_report_key"),
                        progress_log=final_state.get("progress_log", []),
                        completed_at=datetime.now(timezone.utc),
                    )
                )

            logger.info("Pipeline completed", project_id=project_id, score=final_state.get("editor_score"))
            return {"status": "completed", "project_id": project_id}

        except Exception as e:
            logger.error("Pipeline failed", project_id=project_id, error=str(e), exc_info=True)
            async with get_db_context() as db:
                await db.execute(
                    update(ResearchProject)
                    .where(ResearchProject.id == project_id)
                    .values(
                        status=PipelineStatus.FAILED,
                        error_log=[{"error": str(e), "timestamp": datetime.utcnow().isoformat()}],
                    )
                )
            raise self.retry(exc=e, countdown=60)

    return _run_async(_execute())
