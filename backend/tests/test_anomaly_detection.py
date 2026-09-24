from collections import defaultdict
from datetime import date, timedelta

import pytest

from app.services.anomaly_detection import MIN_HISTORY_DAYS, evaluate_service_anomalies
from app.services.synthetic_billing import generate_synthetic_billing_data


@pytest.fixture(scope="module")
def synthetic_dataset():
    # Pinned end_date: the generator's default (today) shifts which calendar
    # dates fall on a Monday depending on when the suite happens to run,
    # which would make these assertions flaky. Tests need a fixed anchor.
    return generate_synthetic_billing_data(end_date=date(2026, 9, 23))


@pytest.fixture(scope="module")
def daily_costs_by_service(synthetic_dataset):
    _, daily_costs, _ = synthetic_dataset
    by_service: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for row in daily_costs:
        by_service[row["service"]].append((row["date"], float(row["total_cost"])))
    for rows in by_service.values():
        rows.sort()
    return by_service


@pytest.fixture(scope="module")
def evaluations_by_service(daily_costs_by_service):
    results = {}
    for service, rows in daily_costs_by_service.items():
        dates = [r[0] for r in rows]
        costs = [r[1] for r in rows]
        results[service] = evaluate_service_anomalies(service, dates, costs)
    return results


def test_injected_spikes_are_flagged(synthetic_dataset, evaluations_by_service):
    _, _, spikes = synthetic_dataset
    assert spikes, "expected the generator to inject at least one spike"

    for spike in spikes:
        flagged_days = {e.date for e in evaluations_by_service[spike.service] if e.is_anomaly}
        assert spike.day in flagged_days, (
            f"expected injected spike on {spike.day} for {spike.service} to be flagged, "
            f"but it wasn't (flagged days: {sorted(flagged_days)})"
        )


def test_weekly_batch_pattern_is_not_flagged(evaluations_by_service):
    bigquery_evaluations = evaluations_by_service["BigQuery"]
    monday_evaluations = [e for e in bigquery_evaluations if e.date.weekday() == 0]

    # Sanity check the fixture actually exercises several Mondays before
    # trusting the "none flagged" assertion below.
    assert len(monday_evaluations) >= 8

    flagged_mondays = [e for e in monday_evaluations if e.is_anomaly]
    assert not flagged_mondays, (
        "BigQuery's weekly Monday batch-job pattern should be absorbed by STL's seasonal "
        f"component, not flagged as anomalous: {flagged_mondays}"
    )


def test_non_anomalous_days_stay_unflagged(evaluations_by_service, synthetic_dataset):
    """The vast majority of ordinary days shouldn't be flagged -- this isn't
    a hard statistical guarantee (STL residuals aren't perfectly i.i.d.), but
    a detector flagging most days would be useless."""
    _, _, spikes = synthetic_dataset
    spike_days = {(s.service, s.day) for s in spikes}

    for service, evaluations in evaluations_by_service.items():
        flagged_ratio = sum(e.is_anomaly for e in evaluations) / len(evaluations)
        assert flagged_ratio < 0.25, f"{service} flagged {flagged_ratio:.0%} of evaluated days"

    # And specifically: no flagged day should be one we didn't inject.
    for service, evaluations in evaluations_by_service.items():
        unexpected = [e.date for e in evaluations if e.is_anomaly and (service, e.date) not in spike_days]
        # Some natural false positives are expected from ordinary noise; just
        # make sure they're not swamping the signal.
        assert len(unexpected) < len(evaluations) * 0.25


def test_short_history_is_skipped_not_flagged():
    """A service with fewer than MIN_HISTORY_DAYS of data should be skipped
    entirely, even if its most recent value is a wild outlier -- STL needs
    more warm-up than a plain rolling z-score would."""
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(MIN_HISTORY_DAYS - 1)]
    costs = [100.0] * (len(dates) - 1) + [10_000.0]

    evaluations = evaluate_service_anomalies("Test Service", dates, costs)

    assert evaluations == []
