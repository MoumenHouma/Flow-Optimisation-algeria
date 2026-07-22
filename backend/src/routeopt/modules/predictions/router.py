"""Prediction endpoints (F13) — train + inspect the service-time model."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, require_roles
from routeopt.database import get_session
from routeopt.modules.predictions.schemas import ModelSummary
from routeopt.modules.predictions.service import ServiceTimeService

router = APIRouter(prefix="/predictions", tags=["predictions"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/service-time/train", response_model=ModelSummary)
async def train_service_time(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> ModelSummary:
    """(Re)train the service-time model from delivery history."""
    model = await ServiceTimeService(session).train(user.company_id)
    return ModelSummary.from_model(model)


@router.get("/service-time", response_model=ModelSummary)
async def service_time_summary(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> ModelSummary:
    """Summary of the current service-time model (or an untrained placeholder)."""
    model = await ServiceTimeService(session).get_model(user.company_id)
    return ModelSummary.from_model(model)
