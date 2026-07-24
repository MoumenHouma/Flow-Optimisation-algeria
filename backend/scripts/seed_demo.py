"""Seed a demo company so a fresh deployment is clickable, not an empty screen.

Idempotent: keyed on the demo manager's email, a second run changes nothing.
Builds a company on the `pro` plan (so demo quotas never bite), a manager + a
driver, one Alger depot, three vehicles, and ~15 real Alger deliveries (a few
carrying COD). It then submits one optimization through the normal service so a
running worker turns it into a completed route with real OSRM geometry.

The optimization is best-effort: if the worker/Redis/OSRM aren't up, the data is
still seeded and the script says to optimize from the UI — it never leaves a
half-written company behind.

    cd backend && python scripts/seed_demo.py

Honours the usual env (DB_URL, REDIS_URL, OSRM_URL). See docs/DEPLOYMENT.md.
"""

import asyncio
import sys
from datetime import UTC, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.security import hash_password
from routeopt.database import SessionLocal
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.depot import Depot
from routeopt.models.route import Route
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle
from routeopt.modules.billing.plans import PLAN_SPECS
from routeopt.modules.routes.schemas import OptimizeRequest
from routeopt.modules.routes.service import RoutesService

DEMO_MANAGER_EMAIL = "demo@routeopt.dz"
DEMO_MANAGER_PASSWORD = "demo-pass-123"
DEMO_DRIVER_EMAIL = "driver@routeopt.dz"
DEMO_DRIVER_PASSWORD = "driver-pass-123"

# Alger depot: Grande Poste, a landmark everyone recognises on the map.
DEPOT = {"lat": 36.7699, "lon": 3.0586, "address": "Grande Poste, Alger Centre"}

# Real Alger addresses with coords, so no geocoding round-trip is needed to seed.
# (address, lat, lon, weight_kg, window_start, window_end, cod_amount_da)
DELIVERIES = [
    ("Rue Didouche Mourad, Alger Centre", 36.7735, 3.0530, 4.0, time(9, 0), time(12, 0), 3500),
    ("Place des Martyrs, Alger", 36.7834, 3.0601, 2.5, None, None, None),
    ("Bab El Oued, Alger", 36.7912, 3.0503, 6.0, time(9, 0), time(11, 0), None),
    ("El Biar, Alger", 36.7681, 3.0341, 3.0, time(10, 0), time(13, 0), 1200),
    ("Bologhine, Alger", 36.8055, 3.0416, 5.5, None, None, None),
    ("Hydra, Alger", 36.7472, 3.0392, 2.0, time(14, 0), time(17, 0), None),
    ("Kouba, Alger", 36.7248, 3.0862, 4.5, time(9, 30), time(12, 30), 4800),
    ("Hussein Dey, Alger", 36.7396, 3.1050, 3.5, None, None, None),
    ("Bir Mourad Raïs, Alger", 36.7369, 3.0533, 2.0, time(10, 0), time(14, 0), None),
    ("El Harrach, Alger", 36.7176, 3.1355, 7.0, time(8, 0), time(11, 0), 2000),
    ("Bab Ezzouar, Alger", 36.7213, 3.1839, 5.0, None, None, None),
    ("Dely Ibrahim, Alger", 36.7539, 2.9962, 3.0, time(13, 0), time(16, 0), None),
    ("Chéraga, Alger", 36.7676, 2.9569, 4.0, time(9, 0), time(12, 0), 1500),
    ("Aïn Benian, Alger", 36.8022, 2.9235, 6.5, None, None, None),
    ("Birkhadem, Alger", 36.7139, 3.0453, 2.5, time(11, 0), time(15, 0), None),
]

VEHICLES = [
    # (name, plate, type, capacity_kg, fuel_range_km, fuel_type)
    ("Camionnette 1", "16-00001-116", "van", 800, 300, "diesel"),
    ("Camionnette 2", "16-00002-116", "van", 800, 250, "essence"),
    ("Moto 1", "16-00003-116", "motorcycle", 60, 180, "essence"),
]


async def _get_or_create_company_and_users(session: AsyncSession) -> tuple[Company, User]:
    manager = await session.scalar(select(User).where(User.email == DEMO_MANAGER_EMAIL))
    if manager is not None:
        company = await session.get(Company, manager.company_id)
        assert company is not None
        return company, manager

    pro = PLAN_SPECS["pro"]
    company = Company(
        name="Démo RouteOpt",
        plan="pro",
        max_vehicles=pro.max_vehicles,
        max_deliveries_per_day=pro.max_deliveries_per_day,
        locale="fr",
    )
    session.add(company)
    await session.flush()

    manager = User(
        company_id=company.id,
        email=DEMO_MANAGER_EMAIL,
        password_hash=hash_password(DEMO_MANAGER_PASSWORD),
        full_name="Gérant Démo",
        role="manager",
    )
    driver = User(
        company_id=company.id,
        email=DEMO_DRIVER_EMAIL,
        password_hash=hash_password(DEMO_DRIVER_PASSWORD),
        full_name="Livreur Démo",
        role="driver",
    )
    session.add_all([manager, driver])
    await session.flush()
    return company, manager


async def _seed_fleet_and_deliveries(session: AsyncSession, company: Company) -> int:
    """Create the depot, vehicles and deliveries if absent. Returns delivery count."""
    depot = await session.scalar(select(Depot).where(Depot.company_id == company.id))
    if depot is None:
        depot = Depot(
            company_id=company.id,
            name="Dépôt Alger Centre",
            lat=DEPOT["lat"],
            lon=DEPOT["lon"],
            address=DEPOT["address"],
        )
        session.add(depot)
        await session.flush()

    existing_vehicles = await session.scalar(
        select(Vehicle.id).where(Vehicle.company_id == company.id).limit(1)
    )
    if existing_vehicles is None:
        driver = await session.scalar(
            select(User).where(User.company_id == company.id, User.role == "driver")
        )
        for i, (name, plate, vtype, cap, frange, ftype) in enumerate(VEHICLES):
            session.add(
                Vehicle(
                    company_id=company.id,
                    depot_id=depot.id,
                    # Assign the demo driver to the first vehicle so the Driver PWA works.
                    driver_user_id=driver.id if i == 0 and driver else None,
                    name=name,
                    vehicle_type=vtype,
                    license_plate=plate,
                    capacity_weight=cap,
                    capacity_volume=10,
                    depot_lat=depot.lat,
                    depot_lon=depot.lon,
                    depot_address=depot.address,
                    fuel_range_km=frange,
                    fuel_type=ftype,
                )
            )

    existing_deliveries = await session.scalar(
        select(Delivery.id).where(Delivery.company_id == company.id).limit(1)
    )
    if existing_deliveries is None:
        for i, (addr, lat, lon, weight, tw_start, tw_end, cod) in enumerate(DELIVERIES):
            session.add(
                Delivery(
                    company_id=company.id,
                    order_id=f"DEMO-{i + 1:03d}",
                    address=addr,
                    lat=lat,
                    lon=lon,
                    geocoding_status="matched",
                    time_window_start=tw_start,
                    time_window_end=tw_end,
                    weight=weight,
                    priority=1,
                    status="geocoded",
                    cod_amount=cod,
                )
            )
    await session.flush()

    count = await session.scalar(select(Delivery.id).where(Delivery.company_id == company.id))
    all_deliveries = await session.scalars(
        select(Delivery.id).where(Delivery.company_id == company.id)
    )
    return len(list(all_deliveries)) if count else 0


async def _try_optimize(session: AsyncSession, company: Company, manager: User) -> str | None:
    """Enqueue an optimization and wait briefly for the worker. Never raises."""
    # Skip if this company already has a route (idempotent re-run).
    existing_route = await session.scalar(select(Route.id).where(Route.company_id == company.id))
    if existing_route is not None:
        return "already-optimized"

    service = RoutesService(session)
    try:
        job_id, _ = await service.submit_job(str(company.id), str(manager.id), OptimizeRequest())
        await session.commit()
    except Exception as exc:  # noqa: BLE001 - optimization is best-effort at seed time
        print(f"  ! could not enqueue optimization ({exc}); optimize from the UI instead")
        return None

    for _ in range(30):  # ~30s: OR-Tools + real OSRM matrix
        await asyncio.sleep(1)
        job = await service.get_job(str(company.id), job_id)
        if job.status == "completed":
            return "completed"
        if job.status == "failed":
            print("  ! optimization job failed; optimize from the UI instead")
            return None
    print("  ! worker didn't finish in 30s (is it running?); optimize from the UI instead")
    return None


async def main() -> None:
    async with SessionLocal() as session:
        company, manager = await _get_or_create_company_and_users(session)
        delivery_count = await _seed_fleet_and_deliveries(session, company)
        await session.commit()
        opt = await _try_optimize(session, company, manager)

    print("\n[OK] Demo data ready.")
    print(f"   Company : {company.name} (plan: {company.plan})")
    print(f"   Manager : {DEMO_MANAGER_EMAIL} / {DEMO_MANAGER_PASSWORD}")
    print(f"   Driver  : {DEMO_DRIVER_EMAIL} / {DEMO_DRIVER_PASSWORD}")
    print(f"   Fleet   : {len(VEHICLES)} vehicles, {delivery_count} deliveries (Alger)")
    if opt == "completed":
        print("   Route   : 1 optimized route with real OSRM geometry [OK]")
    elif opt == "already-optimized":
        print("   Route   : already present (re-run) [OK]")
    else:
        print("   Route   : none yet - log in and click 'Planifier une tournee'")
    print("\n   Seeded at:", datetime.now(UTC).isoformat(timespec="seconds"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
