"""Fleet logic: vehicle CRUD, quota enforcement against company plan (SCHEMA §3.1)."""


class FleetService:
    async def list_vehicles(self, company_id: str) -> list:
        raise NotImplementedError("list vehicles scoped to company_id")

    async def add_vehicle(self, company_id: str, payload) -> object:  # noqa: ANN001
        # TODO: enforce company.max_vehicles quota before insert.
        raise NotImplementedError("add vehicle with quota check")

    async def update_vehicle(
        self, company_id: str, vehicle_id: str, payload
    ) -> object:  # noqa: ANN001
        raise NotImplementedError("update vehicle scoped to company_id")
