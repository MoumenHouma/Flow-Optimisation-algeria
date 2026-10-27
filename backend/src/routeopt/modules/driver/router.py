"""Driver endpoints (F8) — the delivery-runtime API for the Driver PWA."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core import audit
from routeopt.core.audit import client_ip
from routeopt.core.dependencies import CurrentUser, get_current_user
from routeopt.core.exceptions import ValidationError
from routeopt.core.storage import Storage, get_storage
from routeopt.database import get_session
from routeopt.modules.driver.schemas import DriverRouteOut, ProofOut, StatusUpdate
from routeopt.modules.driver.service import DriverService
from routeopt.modules.orders.schemas import DeliveryOut
from routeopt.modules.tracking.schemas import PositionIn

router = APIRouter(prefix="/driver", tags=["driver"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
StorageDep = Annotated[Storage, Depends(get_storage)]

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per file


@router.get("/route", response_model=DriverRouteOut | None)
async def my_route(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DriverRouteOut | None:
    """The active route for the vehicle assigned to me (null if none today)."""
    return await DriverService(session).my_route(user.user_id, user.company_id)


@router.post("/location", status_code=204)
async def record_location(
    payload: PositionIn,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    """Report the driver's current GPS position for live tracking (F18)."""
    await DriverService(session).record_location(
        user.user_id, user.company_id, payload.lat, payload.lon
    )


@router.put("/deliveries/{delivery_id}/status", response_model=DeliveryOut)
async def update_delivery_status(
    delivery_id: str,
    payload: StatusUpdate,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DeliveryOut:
    """Mark a stop en_route / delivered / failed (records history + position)."""
    delivery = await DriverService(session).update_status(
        user.user_id, user.company_id, delivery_id, payload
    )
    return DeliveryOut.from_model(delivery)


async def _read_image(upload: UploadFile | None) -> tuple[bytes, str] | None:
    if upload is None:
        return None
    content_type = (upload.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise ValidationError(f"Unsupported file type: {content_type or 'unknown'}")
    data = await upload.read()
    if not data:
        return None
    if len(data) > _MAX_FILE_BYTES:
        raise ValidationError("File too large (max 10 MB)")
    return data, content_type


@router.post("/deliveries/{delivery_id}/proof", response_model=ProofOut, status_code=201)
async def upload_proof(
    delivery_id: str,
    session: SessionDep,
    storage: StorageDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    photo: Annotated[UploadFile | None, File()] = None,
    signature: Annotated[UploadFile | None, File()] = None,
    lat: Annotated[float | None, Form()] = None,
    lon: Annotated[float | None, Form()] = None,
) -> ProofOut:
    """Upload proof of delivery (photo and/or signature) — one per delivery."""
    return await DriverService(session).save_proof(
        user.user_id,
        user.company_id,
        delivery_id,
        await _read_image(photo),
        await _read_image(signature),
        lat,
        lon,
        storage,
    )


@router.get("/deliveries/{delivery_id}/proof", response_model=ProofOut | None)
async def get_proof(
    delivery_id: str,
    session: SessionDep,
    storage: StorageDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    request: Request,
) -> ProofOut | None:
    """Fetch the stored proof for a delivery with presigned URLs (null if none)."""
    proof = await DriverService(session).get_proof(
        user.user_id, user.company_id, delivery_id, storage
    )
    if proof is not None:
        # Accessing proof media (photo/signature of the recipient) is auditable (H2).
        await audit.record(
            session,
            action="proof.accessed",
            resource_type="delivery",
            company_id=user.company_id,
            actor_user_id=user.user_id,
            resource_id=delivery_id,
            ip_address=client_ip(request),
        )
        await session.commit()
    return proof
