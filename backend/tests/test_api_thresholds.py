from app.models.alert import AlertConfig


async def _seed_configs(db_session):
    rows = [
        AlertConfig(service=None, z_threshold=2.5, slack_webhook_url=None, enabled=True),
        AlertConfig(
            service="BigQuery",
            z_threshold=3.0,
            slack_webhook_url="https://hooks.slack.com/services/AAA/BBB/CCC",
            enabled=True,
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()


async def test_get_thresholds_returns_all_configs(client, db_session):
    await _seed_configs(db_session)

    response = await client.get("/config/thresholds")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    services = {row["service"] for row in data}
    assert services == {None, "BigQuery"}


async def test_get_thresholds_filters_by_service(client, db_session):
    await _seed_configs(db_session)

    response = await client.get("/config/thresholds", params={"service": "BigQuery"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service"] == "BigQuery"
    assert data[0]["z_threshold"] == 3.0


async def test_put_thresholds_creates_new_config(client):
    response = await client.put(
        "/config/thresholds",
        json={
            "service": "Cloud Run",
            "z_threshold": 4.0,
            "slack_webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
            "enabled": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Cloud Run"
    assert data["z_threshold"] == 4.0
    assert data["enabled"] is False

    follow_up = await client.get("/config/thresholds", params={"service": "Cloud Run"})
    assert len(follow_up.json()) == 1


async def test_put_thresholds_updates_existing_config_in_place(client, db_session):
    await _seed_configs(db_session)

    response = await client.put(
        "/config/thresholds",
        json={"service": "BigQuery", "z_threshold": 5.0, "slack_webhook_url": None, "enabled": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["z_threshold"] == 5.0
    assert data["slack_webhook_url"] is None
    assert data["enabled"] is False

    all_configs = await client.get("/config/thresholds")
    assert len(all_configs.json()) == 2  # updated in place, not a new row


async def test_put_thresholds_upserts_global_default(client, db_session):
    await _seed_configs(db_session)

    response = await client.put(
        "/config/thresholds",
        json={"service": None, "z_threshold": 3.5, "slack_webhook_url": None, "enabled": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service"] is None
    assert data["z_threshold"] == 3.5

    all_configs = await client.get("/config/thresholds")
    assert len(all_configs.json()) == 2


async def test_put_thresholds_rejects_non_positive_threshold(client):
    response = await client.put(
        "/config/thresholds",
        json={"service": "BigQuery", "z_threshold": 0, "slack_webhook_url": None, "enabled": True},
    )
    assert response.status_code == 422
