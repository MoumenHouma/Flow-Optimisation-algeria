"""Cross-tenant validation helpers.

Guards against a caller referencing another company's users. Notably
``driver_user_id`` is accepted on vehicle + territory writes; without this check
a manager could point a resource at a foreign user, who would then read this
company's routes via the driver app.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import ValidationError
from routeopt.models.user import User


async def validate_driver(
    session: AsyncSession, company_id: str, driver_user_id: str | None
) -> uuid.UUID | None:
    """Return the UUID iff it is a live driver in this company, else raise."""
    if not driver_user_id:
        return None
    did = uuid.UUID(driver_user_id)
    user = await session.scalar(select(User).where(User.id == did))
    if (
        user is None
        or str(user.company_id) != company_id
        or user.role != "driver"
        or user.deleted_at is not None
    ):
        raise ValidationError("driver_user_id must be a driver in your company")
    return did
