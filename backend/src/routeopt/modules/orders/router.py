"""Orders endpoints — docs/ARCHITECTURE.md §2.2 (Order Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.modules.orders.schemas import BulkImportResponse, DeliveryOut
from routeopt.modules.orders.service import OrdersService

router = APIRouter(prefix="/orders", tags=["orders"])
service = OrdersService()


@router.post("/bulk", response_model=BulkImportResponse)
async def bulk_import(
    file: UploadFile,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> BulkImportResponse:
    """Import deliveries from CSV/Excel (F1)."""
    raise NotImplementedError("parse file -> service.bulk_import")


@router.get("/{delivery_id}", response_model=DeliveryOut)
async def get_delivery(
    delivery_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DeliveryOut:
    raise NotImplementedError("fetch delivery scoped to user.company_id")


@router.put("/{delivery_id}/status")
async def update_status(
    delivery_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    """Update delivery status (delivered/failed/...). Used by Driver PWA (F8)."""
    raise NotImplementedError("update status + append delivery_status_history")
