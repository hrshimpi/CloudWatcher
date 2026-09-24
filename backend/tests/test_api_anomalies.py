from datetime import date

from app.models.anomaly import Anomaly


async def _seed_anomalies(db_session) -> list[Anomaly]:
    rows = [
        Anomaly(
            service="BigQuery",
            date=date(2026, 1, 1),
            expected_cost=100,
            actual_cost=500,
            z_score=6.2,
            pct_deviation=400.0,
            top_contributor="Analysis",
            root_cause_explanation="BigQuery cost was much higher than expected.",
            status="open",
        ),
        Anomaly(
            service="Cloud Storage",
            date=date(2026, 1, 2),
            expected_cost=80,
            actual_cost=90,
            z_score=2.8,
            pct_deviation=12.5,
            top_contributor="Class A Operations",
            root_cause_explanation="Cloud Storage cost was moderately higher than expected.",
            status="resolved",
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()
    for row in rows:
        await db_session.refresh(row)
    return rows


async def test_list_anomalies_returns_all_by_default(client, db_session):
    await _seed_anomalies(db_session)

    response = await client.get("/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {a["service"] for a in data} == {"BigQuery", "Cloud Storage"}


async def test_list_anomalies_filters_by_status(client, db_session):
    await _seed_anomalies(db_session)

    response = await client.get("/anomalies", params={"status": "open"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service"] == "BigQuery"
    assert data[0]["status"] == "open"


async def test_list_anomalies_filters_by_service(client, db_session):
    await _seed_anomalies(db_session)

    response = await client.get("/anomalies", params={"service": "Cloud Storage"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service"] == "Cloud Storage"


async def test_get_anomaly_by_id(client, db_session):
    seeded = await _seed_anomalies(db_session)
    target = seeded[0]

    response = await client.get(f"/anomalies/{target.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == target.id
    assert data["service"] == "BigQuery"
    assert data["top_contributor"] == "Analysis"


async def test_get_anomaly_not_found(client):
    response = await client.get("/anomalies/999999")
    assert response.status_code == 404


async def test_list_anomalies_filters_by_date_range(client, db_session):
    await _seed_anomalies(db_session)

    response = await client.get(
        "/anomalies", params={"start_date": "2026-01-02", "end_date": "2026-01-02"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service"] == "Cloud Storage"


async def test_list_anomalies_rejects_inverted_date_range(client):
    response = await client.get(
        "/anomalies", params={"start_date": "2026-01-05", "end_date": "2026-01-01"}
    )
    assert response.status_code == 400
