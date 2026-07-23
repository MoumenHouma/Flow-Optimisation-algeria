"""Tracking endpoints (F18): dispatcher live stream + public customer tracking.

The stream is Server-Sent Events over a plain StreamingResponse (no extra deps).
It reads Redis only — never holds a DB session for the life of the connection —
and stops as soon as the client disconnects.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, require_roles
from routeopt.core.exceptions import NotFoundError
from routeopt.database import get_session
from routeopt.modules.tracking.schemas import TrackOut
from routeopt.modules.tracking.service import TrackingService, read_positions
from routeopt.redis_client import redis_client

router = APIRouter(tags=["tracking"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ManagerDep = Annotated[CurrentUser, Depends(require_roles("admin", "manager"))]

_STREAM_INTERVAL_S = 3.0


@router.get("/tracking/stream")
async def stream(request: Request, user: ManagerDep) -> StreamingResponse:
    """SSE stream of the company's live vehicle positions (dispatcher map)."""

    async def events() -> AsyncIterator[str]:
        while True:
            if await request.is_disconnected():
                break
            positions = await read_positions(redis_client, user.company_id)
            yield f"data: {json.dumps([p.model_dump() for p in positions])}\n\n"
            await asyncio.sleep(_STREAM_INTERVAL_S)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/track/{token}", response_model=TrackOut)
async def public_track(token: str, session: SessionDep) -> TrackOut:
    """Public, unauthenticated delivery status for a signed tracking link."""
    result = await TrackingService(session, redis_client).public_track(token)
    if result is None:
        raise NotFoundError("Invalid or expired tracking link")
    return result
