from datetime import date
from decimal import Decimal

from app.models.billing import DailyServiceCost


async def _seed_daily_costs(db_session):
    rows = [
        DailyServiceCost(date=date(2026, 1, 1), provider="gcp", service="Compute Engine", total_cost=Decimal("100.00")),
        DailyServiceCost(date=date(2026, 1, 1), provider="gcp", service="BigQuery", total_cost=Decimal("50.00")),
        DailyServiceCost(date=date(2026, 1, 2), provider="gcp", service="Compute Engine", total_cost=Decimal("120.00")),
        DailyServiceCost(date=date(2026, 1, 2), provider="gcp", service="BigQuery", total_cost=Decimal("55.00")),
        DailyServiceCost(date=date(2026, 1, 1), provider="aws", service="EC2", total_cost=Decimal("200.00")),
    ]
    db_session.add_all(rows)
    await db_session.commit()


async def test_cost_summary_totals_and_trend(client, db_session):
    await _seed_daily_costs(db_session)

    response = await client.get("/costs/summary", params={"provider": "gcp"})
    assert response.status_code == 200
    data = response.json()

    assert data["provider"] == "gcp"
    assert Decimal(data["total_cost"]) == Decimal("325.00")
    assert {item["service"] for item in data["by_service"]} == {"Compute Engine", "BigQuery"}
    assert len(data["trend"]) == 2
    assert data["trend"][0]["date"] == "2026-01-01"


async def test_cost_summary_date_range_filter(client, db_session):
    await _seed_daily_costs(db_session)

    response = await client.get(
        "/costs/summary",
        params={"provider": "gcp", "start_date": "2026-01-02", "end_date": "2026-01-02"},
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["total_cost"]) == Decimal("175.00")
    assert len(data["trend"]) == 1


async def test_cost_summary_rejects_inverted_date_range(client):
    response = await client.get(
        "/costs/summary", params={"start_date": "2026-01-05", "end_date": "2026-01-01"}
    )
    assert response.status_code == 400


async def test_cost_summary_with_no_filters_sums_everything(client, db_session):
    await _seed_daily_costs(db_session)

    response = await client.get("/costs/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] is None
    assert Decimal(data["total_cost"]) == Decimal("525.00")


async def test_cost_summary_with_no_matching_data_returns_zero(client):
    response = await client.get("/costs/summary", params={"provider": "azure"})
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["total_cost"]) == Decimal(0)
    assert data["by_service"] == []
    assert data["trend"] == []
