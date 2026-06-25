"""
WebSocket endpoint for real-time pipeline progress streaming.
"""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Set
import structlog

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.core.database import get_db_context
from app.models.research import ResearchProject, PipelineStatus
from app.services.cache.redis import get_redis

router = APIRouter(tags=["websocket"])
logger = structlog.get_logger()

# In-memory connection registry (per process; use Redis pub/sub for multi-worker)
_connections: Dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/projects/{project_id}/progress")
async def pipeline_progress_ws(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
):
    await websocket.accept()

    if project_id not in _connections:
        _connections[project_id] = set()
    _connections[project_id].add(websocket)

    try:
        last_log_len = 0
        while True:
            async with get_db_context() as db:
                result = await db.execute(
                    select(ResearchProject).where(ResearchProject.id == project_id)
                )
                project = result.scalar_one_or_none()

            if not project:
                await websocket.send_json({"type": "error", "message": "Project not found"})
                break

            log = project.progress_log or []
            if len(log) > last_log_len:
                for entry in log[last_log_len:]:
                    await websocket.send_json({
                        "type": "progress",
                        "data": entry,
                    })
                last_log_len = len(log)

            if project.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED):
                await websocket.send_json({
                    "type": "complete",
                    "status": project.status.value,
                    "editor_score": project.editor_score,
                    "plagiarism_score": project.plagiarism_score,
                    "ai_detection_score": project.ai_detection_score,
                })
                break

            await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected", project_id=project_id)
    except Exception as e:
        logger.error("WebSocket error", project_id=project_id, error=str(e))
    finally:
        _connections.get(project_id, set()).discard(websocket)


async def broadcast_progress(project_id: str, event: dict) -> None:
    """Called from background tasks to push updates to connected clients."""
    connections = _connections.get(project_id, set())
    dead = set()
    for ws in connections:
        try:
            await ws.send_json({"type": "progress", "data": event})
        except Exception:
            dead.add(ws)
    connections -= dead
