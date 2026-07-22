"""Company + white-label branding (F16)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError
from routeopt.models.company import Company
from routeopt.modules.company.schemas import Branding


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_company(self, company_id: str) -> Company:
        company = await self.session.get(Company, uuid.UUID(company_id))
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Company not found")
        return company

    async def update_branding(self, company_id: str, branding: Branding) -> Company:
        company = await self.get_company(company_id)
        # Merge: only overwrite provided keys, keep the rest.
        current = dict(company.branding or {})
        current.update(branding.model_dump(exclude_none=True))
        company.branding = current or None
        await self.session.commit()
        await self.session.refresh(company)
        return company
