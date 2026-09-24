from datetime import date
from decimal import Decimal

from app.models.billing import BillingRecord, DailyServiceCost


async def _seed_service_data(db_session):
    daily_costs = [
        DailyServiceCost(date=date(2026, 1, 1), provider="gcp", service="BigQuery", total_cost=Decimal("150.00")),
        DailyServiceCost(date=date(2026, 1, 2), provider="gcp", service="BigQuery", total_cost=Decimal("170.00")),
        DailyServiceCost(date=date(2026, 1, 1), provider="gcp", service="Cloud Storage", total_cost=Decimal("40.00")),
    ]
    billing_records = [
        BillingRecord(
            provider="gcp", account_id="acct-1", service="BigQuery", sku="Analysis",
            date=date(2026, 1, 1), cost=Decimal("100.00"), currency="USD",
        ),
        BillingRecord(
            provider="gcp", account_id="acct-1", service="BigQuery", sku="Storage",
            date=date(2026, 1, 1), cost=Decimal("50.00"), currency="USD",
        ),
        BillingRecord(
            provider="gcp", account_id="acct-1", service="BigQuery", sku="Analysis",
            date=date(2026, 1, 2), cost=Decimal("120.00"), currency="USD",
        ),
        BillingRecord(
            provider="gcp", account_id="acct-1", service="BigQuery", sku="Storage",
            date=date(2026, 1, 2), cost=Decimal("50.00"), currency="USD",
        ),
    ]
    db_session.add_all(daily_costs + billing_records)
    await db_session.commit()


async def test_drilldown_returns_time_series_and_top_skus(client, db_session):
    await _seed_service_data(db_session)

    response = await client.get("/services/BigQuery/drilldown")
    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "BigQuery"
    assert Decimal(data["total_cost"]) == Decimal("320.00")
    assert len(data["time_series"]) == 2
    assert data["time_series"][0]["date"] == "2026-01-01"

    top_skus = {sku["sku"]: Decimal(sku["total_cost"]) for sku in data["top_skus"]}
    assert top_skus["Analysis"] == Decimal("220.00")
    assert top_skus["Storage"] == Decimal("100.00")


async def test_drilldown_respects_date_range(client, db_session):
    await _seed_service_data(db_session)

    response = await client.get(
        "/services/BigQuery/drilldown",
        params={"start_date": "2026-01-02", "end_date": "2026-01-02"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["time_series"]) == 1
    assert Decimal(data["total_cost"]) == Decimal("170.00")


async def test_drilldown_respects_top_n(client, db_session):
    await _seed_service_data(db_session)

    response = await client.get("/services/BigQuery/drilldown", params={"top_n": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data["top_skus"]) == 1
    assert data["top_skus"][0]["sku"] == "Analysis"


async def test_drilldown_unknown_service_returns_404(client, db_session):
    await _seed_service_data(db_session)

    response = await client.get("/services/Nonexistent Service/drilldown")
    assert response.status_code == 404


async def test_drilldown_rejects_inverted_date_range(client, db_session):
    await _seed_service_data(db_session)

    response = await client.get(
        "/services/BigQuery/drilldown",
        params={"start_date": "2026-01-05", "end_date": "2026-01-01"},
    )
    assert response.status_code == 400
