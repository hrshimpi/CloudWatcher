"""Cost anomaly detection.

For each service, decomposes its daily cost history with STL (weekly
seasonality) into trend, seasonal, and residual components, then flags a day
as anomalous when its residual is more than `z_threshold` standard deviations
from the trailing 30-day mean residual (yesterday and earlier — never today's
own value, to avoid the anomaly masking itself).

STL absorbs the weekly pattern into the seasonal component, so a service that
is reliably heavier every Monday (e.g. a weekly batch job) shows up as a
predictable seasonal swing, not a residual spike — only genuine one-off
deviations from that pattern should trip the z-score threshold.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.tsa.seasonal import STL

from app.models.anomaly import Anomaly
from app.models.billing import BillingRecord, DailyServiceCost

DEFAULT_Z_THRESHOLD = 2.5

# STL decomposition needs more warm-up than a plain rolling mean/std would --
# below this many days of history for a service, skip it rather than flag.
MIN_HISTORY_DAYS = 21

SEASONAL_PERIOD = 7  # weekly seasonality
ROLLING_WINDOW = 30
ROLLING_MIN_PERIODS = 14  # smallest trailing window we trust for a mean/std


@dataclass(frozen=True)
class AnomalyEvaluation:
    service: str
    date: date
    actual_cost: float
    expected_cost: float
    z_score: float
    pct_deviation: float
    is_anomaly: bool


def evaluate_service_anomalies(
    service: str,
    dates: Sequence[date],
    costs: Sequence[float],
    z_threshold: float = DEFAULT_Z_THRESHOLD,
    min_history_days: int = MIN_HISTORY_DAYS,
    seasonal_period: int = SEASONAL_PERIOD,
    rolling_window: int = ROLLING_WINDOW,
    rolling_min_periods: int = ROLLING_MIN_PERIODS,
) -> list[AnomalyEvaluation]:
    """Evaluates every day in the series that has enough trailing history.

    `dates` must be a gap-free, ascending daily series (STL's weekly period
    is positional, so a missing day would shift the seasonal alignment for
    everything after it).
    """
    if len(dates) < min_history_days:
        return []

    series = pd.Series(list(costs), index=pd.DatetimeIndex(list(dates)), dtype=float)

    stl_result = STL(series, period=seasonal_period, robust=True).fit()
    expected = stl_result.trend + stl_result.seasonal
    residual = stl_result.resid

    # Rolling mean/std of the residual, shifted so "today" is never part of
    # its own baseline.
    baseline = residual.shift(1)
    rolling_mean = baseline.rolling(window=rolling_window, min_periods=rolling_min_periods).mean()
    rolling_std = baseline.rolling(window=rolling_window, min_periods=rolling_min_periods).std()

    z_scores = (residual - rolling_mean) / rolling_std

    evaluations: list[AnomalyEvaluation] = []
    for i, timestamp in enumerate(series.index):
        z = z_scores.iloc[i]
        if pd.isna(z) or not pd.notna(rolling_std.iloc[i]) or rolling_std.iloc[i] == 0:
            continue

        actual = float(series.iloc[i])
        exp = float(expected.iloc[i])
        pct_deviation = ((actual - exp) / exp * 100) if exp else 0.0

        evaluations.append(
            AnomalyEvaluation(
                service=service,
                date=timestamp.date(),
                actual_cost=actual,
                expected_cost=exp,
                z_score=float(z),
                pct_deviation=pct_deviation,
                is_anomaly=abs(z) > z_threshold,
            )
        )

    return evaluations


def evaluate_latest_day(
    service: str,
    dates: Sequence[date],
    costs: Sequence[float],
    **kwargs,
) -> AnomalyEvaluation | None:
    """Evaluates only the most recent day in the series (the "today" check a
    daily job would run), or None if there isn't enough history to do so."""
    if not dates:
        return None

    evaluations = evaluate_service_anomalies(service, dates, costs, **kwargs)
    if not evaluations or evaluations[-1].date != dates[-1]:
        return None
    return evaluations[-1]


def _build_root_cause_explanation(evaluation: AnomalyEvaluation, top_contributor: str | None) -> str:
    direction = "higher" if evaluation.actual_cost >= evaluation.expected_cost else "lower"
    explanation = (
        f"{evaluation.service} cost on {evaluation.date.isoformat()} was "
        f"${evaluation.actual_cost:,.2f}, {abs(evaluation.pct_deviation):.0f}% {direction} than the "
        f"${evaluation.expected_cost:,.2f} expected from its trend and weekly pattern "
        f"(z={evaluation.z_score:.2f})."
    )
    if top_contributor:
        explanation += f" Largest contributor: {top_contributor}."
    return explanation


async def _find_top_contributor(
    session: AsyncSession, provider: str, service: str, day: date
) -> str | None:
    result = await session.execute(
        select(BillingRecord.sku)
        .where(
            BillingRecord.provider == provider,
            BillingRecord.service == service,
            BillingRecord.date == day,
        )
        .group_by(BillingRecord.sku)
        .order_by(func.sum(BillingRecord.cost).desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def detect_and_record_anomalies(
    session: AsyncSession,
    as_of: date | None = None,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> list[Anomaly]:
    """Runs anomaly detection for every service as of `as_of` (default today)
    and writes any flagged days to the `anomalies` table."""
    as_of = as_of or datetime.now(UTC).date()

    services_result = await session.execute(
        select(DailyServiceCost.provider, DailyServiceCost.service)
        .where(DailyServiceCost.date <= as_of)
        .distinct()
    )
    service_rows = services_result.all()

    created: list[Anomaly] = []

    for provider, service in service_rows:
        history_result = await session.execute(
            select(DailyServiceCost.date, DailyServiceCost.total_cost)
            .where(
                DailyServiceCost.provider == provider,
                DailyServiceCost.service == service,
                DailyServiceCost.date <= as_of,
            )
            .order_by(DailyServiceCost.date)
        )
        rows = history_result.all()
        dates = [row.date for row in rows]
        costs = [float(row.total_cost) for row in rows]

        evaluation = evaluate_latest_day(service, dates, costs, z_threshold=z_threshold)
        if evaluation is None or not evaluation.is_anomaly:
            continue

        top_contributor = await _find_top_contributor(session, provider, service, as_of)

        anomaly = Anomaly(
            service=service,
            date=as_of,
            expected_cost=Decimal(str(round(evaluation.expected_cost, 4))),
            actual_cost=Decimal(str(round(evaluation.actual_cost, 4))),
            z_score=evaluation.z_score,
            pct_deviation=evaluation.pct_deviation,
            top_contributor=top_contributor,
            root_cause_explanation=_build_root_cause_explanation(evaluation, top_contributor),
            status="open",
        )
        session.add(anomaly)
        created.append(anomaly)

    await session.commit()
    return created
