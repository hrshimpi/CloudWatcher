"""CLI for seeding local Postgres with synthetic GCP billing data.

Usage (from backend/, with the venv/poetry env active):

    poetry run seed-db
    poetry run seed-db --days 90 --seed 9
    poetry run seed-db --append   # don't truncate existing rows first
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import insert, text

from app.core.database import engine
from app.models.billing import BillingRecord, DailyServiceCost
from app.services.synthetic_billing import generate_synthetic_billing_data


async def seed(days: int, seed_value: int, reset: bool) -> None:
    billing_records, daily_service_costs, spikes = generate_synthetic_billing_data(
        days=days, seed=seed_value
    )

    async with engine.begin() as conn:
        if reset:
            await conn.execute(
                text("TRUNCATE TABLE billing_records, daily_service_costs RESTART IDENTITY")
            )

        await conn.execute(insert(BillingRecord.__table__), billing_records)
        await conn.execute(insert(DailyServiceCost.__table__), daily_service_costs)

    await engine.dispose()

    print(f"Inserted {len(billing_records)} billing_records rows")
    print(f"Inserted {len(daily_service_costs)} daily_service_costs rows")
    print(f"Date range: {daily_service_costs[0]['date']} -> {daily_service_costs[-1]['date']}")
    print()
    print("Weekly pattern: BigQuery runs ~3x its normal cost every Monday (expected, not anomalous).")
    print()
    print(f"Injected {len(spikes)} one-off spikes (these should be flagged as real anomalies):")
    for spike in sorted(spikes, key=lambda s: s.day):
        print(f"  {spike.day}  {spike.service:<16}  ~{spike.multiplier:.1f}x normal cost")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90, help="Number of days of history to generate")
    parser.add_argument("--seed", type=int, default=9, help="Random seed, for reproducible data")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing billing data instead of truncating first",
    )
    args = parser.parse_args()

    asyncio.run(seed(days=args.days, seed_value=args.seed, reset=not args.append))


if __name__ == "__main__":
    main()
