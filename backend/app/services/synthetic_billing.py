"""Generates a synthetic GCP-style billing dataset for local development.

There's no live GCP billing export wired up yet, so this stands in for one: it
produces daily costs across a handful of services with realistic noise, a
recurring weekly pattern on one service (to test that seasonal decomposition
doesn't flag it), and a handful of injected one-off spikes (which should be
flagged as real anomalies).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

PROVIDER = "gcp"
ACCOUNT_ID = "cloudwatcher-demo-482913"
CURRENCY = "USD"

# Average daily cost and day-to-day noise (as a fraction of the average) per service.
SERVICE_PROFILES: dict[str, dict[str, float]] = {
    "Compute Engine": {"baseline": 420.0, "noise": 0.10},
    "Cloud Storage": {"baseline": 85.0, "noise": 0.06},
    "BigQuery": {"baseline": 150.0, "noise": 0.12},
    "Cloud SQL": {"baseline": 110.0, "noise": 0.05},
    "Cloud Run": {"baseline": 60.0, "noise": 0.15},
    "Networking": {"baseline": 95.0, "noise": 0.08},
    "Cloud Functions": {"baseline": 30.0, "noise": 0.18},
    "Pub/Sub": {"baseline": 20.0, "noise": 0.14},
}

# Representative SKUs used to split each service's daily total into billing_records rows.
SERVICE_SKUS: dict[str, list[str]] = {
    "Compute Engine": [
        "N2 Instance Core running in Americas",
        "N2 Instance Ram running in Americas",
        "Storage PD Capacity",
    ],
    "Cloud Storage": [
        "Standard Storage US Multi-region",
        "Class A Operations",
        "Class B Operations",
    ],
    "BigQuery": [
        "Analysis (on-demand query)",
        "Active Storage",
        "Streaming Inserts",
    ],
    "Cloud SQL": [
        "SQL vCPU time",
        "SQL RAM time",
        "SQL Storage PD SSD",
    ],
    "Cloud Run": [
        "CPU Allocation Time",
        "Memory Allocation Time",
        "Requests",
    ],
    "Networking": [
        "Network Egress via Internet",
        "Network Load Balancing",
        "Cloud NAT",
    ],
    "Cloud Functions": [
        "Invocations",
        "Compute Time (GB-second)",
        "Networking Egress",
    ],
    "Pub/Sub": [
        "Message Delivery Basic",
        "Message Delivery Ordering",
    ],
}

# The service with a deliberate weekly pattern: ~3x heavier every Monday,
# simulating a nightly/weekly batch reprocessing job.
WEEKLY_PATTERN_SERVICE = "BigQuery"
WEEKLY_PATTERN_DAY = 0  # Monday (date.weekday() == 0)
WEEKLY_PATTERN_MULTIPLIER = 3.0

# Number of one-off spikes to inject, and the multiplier range applied to that
# service's normal cost on that day.
SPIKE_COUNT_RANGE = (3, 4)
SPIKE_MULTIPLIER_RANGE = (4.0, 9.0)


@dataclass(frozen=True)
class InjectedSpike:
    service: str
    day: date
    multiplier: float


def _round_money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _daily_service_cost(
    rng: random.Random,
    service: str,
    day: date,
    spikes_by_day: dict[date, dict[str, float]],
) -> float:
    profile = SERVICE_PROFILES[service]
    baseline = profile["baseline"]
    noise = profile["noise"]

    cost = baseline * rng.gauss(1.0, noise)

    if service == WEEKLY_PATTERN_SERVICE and day.weekday() == WEEKLY_PATTERN_DAY:
        cost *= WEEKLY_PATTERN_MULTIPLIER

    spike_multiplier = spikes_by_day.get(day, {}).get(service)
    if spike_multiplier is not None:
        cost *= spike_multiplier

    return max(cost, 1.0)


def _pick_spikes(rng: random.Random, days: list[date]) -> list[InjectedSpike]:
    spike_count = rng.randint(*SPIKE_COUNT_RANGE)
    services = list(SERVICE_PROFILES.keys())

    # Avoid spiking the weekly-pattern service on its own pattern day, so the
    # two "should be treated differently" signals stay cleanly separable.
    eligible_days = [d for d in days if not (d.weekday() == WEEKLY_PATTERN_DAY)]

    chosen_days = rng.sample(eligible_days, k=min(spike_count, len(eligible_days)))
    spikes = []
    for day in chosen_days:
        service = rng.choice(services)
        multiplier = rng.uniform(*SPIKE_MULTIPLIER_RANGE)
        spikes.append(InjectedSpike(service=service, day=day, multiplier=multiplier))
    return spikes


def generate_synthetic_billing_data(
    days: int = 90,
    seed: int = 42,
    end_date: date | None = None,
) -> tuple[list[dict], list[dict], list[InjectedSpike]]:
    """Builds `days` worth of synthetic GCP billing data.

    Returns (billing_records, daily_service_costs, injected_spikes) where the
    first two are lists of plain dicts ready for a bulk insert, and the third
    documents which (service, day) pairs were pushed up as anomalies so it's
    easy to check that a detector actually catches them.
    """
    rng = random.Random(seed)

    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    all_days = [start_date + timedelta(days=i) for i in range(days)]

    spikes = _pick_spikes(rng, all_days)
    spikes_by_day: dict[date, dict[str, float]] = {}
    for spike in spikes:
        spikes_by_day.setdefault(spike.day, {})[spike.service] = spike.multiplier

    billing_records: list[dict] = []
    daily_service_costs: list[dict] = []

    for day in all_days:
        for service in SERVICE_PROFILES:
            total_cost = _daily_service_cost(rng, service, day, spikes_by_day)

            skus = SERVICE_SKUS[service]
            weights = [rng.uniform(0.6, 1.4) for _ in skus]
            weight_sum = sum(weights)

            sku_costs = [total_cost * (w / weight_sum) for w in weights]
            # Round each SKU cost individually, then true up the last one so
            # the SKU-level rows sum exactly to the daily total.
            rounded = [_round_money(c) for c in sku_costs[:-1]]
            last = _round_money(total_cost) - sum(rounded)
            rounded.append(last)

            for sku, cost in zip(skus, rounded):
                billing_records.append(
                    {
                        "provider": PROVIDER,
                        "account_id": ACCOUNT_ID,
                        "service": service,
                        "sku": sku,
                        "date": day,
                        "cost": cost,
                        "currency": CURRENCY,
                    }
                )

            daily_service_costs.append(
                {
                    "date": day,
                    "provider": PROVIDER,
                    "service": service,
                    "total_cost": _round_money(total_cost),
                }
            )

    return billing_records, daily_service_costs, spikes
