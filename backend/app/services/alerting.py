"""Slack alerting for flagged cost anomalies.

Flow: detection flags an anomaly -> ask an LLM for a one-sentence plain-English
root-cause guess -> if that succeeds, it replaces the anomaly's templated
root_cause_explanation -> format a Slack message from the (possibly upgraded)
explanation plus the raw numbers -> POST it to the webhook configured in
alert_config.

The LLM call is best-effort only: any failure (missing key, timeout, bad
response) falls back to whatever templated explanation the anomaly already
had. An alert should never fail to send just because the LLM did.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.alert import AlertConfig
from app.models.anomaly import Anomaly
from app.services.anomaly_detection import DEFAULT_Z_THRESHOLD, detect_and_record_anomalies

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass(frozen=True)
class AlertResult:
    service: str
    sent: bool
    dry_run: bool
    used_llm_explanation: bool
    message_text: str
    error: str | None = None


def _build_llm_prompt(
    service: str, cost_delta: float, pct_deviation: float, top_contributor: str | None
) -> str:
    direction = "higher" if cost_delta >= 0 else "lower"
    return (
        "A cloud cost monitoring system flagged a billing anomaly with these facts:\n"
        f"- Service: {service}\n"
        f"- Cost was ${abs(cost_delta):,.2f} {direction} than expected "
        f"({pct_deviation:+.1f}% deviation)\n"
        f"- Top contributing SKU: {top_contributor or 'unknown'}\n\n"
        "In exactly one plain-English sentence, give your best concrete guess at the "
        "likely root cause. Do not hedge (no 'it could be' or 'possibly') and do not "
        "repeat the numbers back -- just state the likely cause."
    )


async def generate_root_cause_guess(
    *,
    service: str,
    cost_delta: float,
    pct_deviation: float,
    top_contributor: str | None,
) -> str | None:
    """Best-effort LLM root-cause guess. Returns None on any failure so
    callers can fall back to a templated explanation without special-casing."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    prompt = _build_llm_prompt(service, cost_delta, pct_deviation, top_contributor)
    url = GEMINI_ENDPOINT.format(model=settings.gemini_model)

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                url,
                params={"key": settings.gemini_api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
    except httpx.HTTPError as exc:
        logger.warning("Gemini call failed, falling back to templated explanation: %s", exc)
        return None
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Unexpected Gemini response shape, falling back to templated explanation: %s", exc)
        return None

    text = text.strip()
    return text or None


def build_slack_message(anomaly: Anomaly) -> str:
    actual = float(anomaly.actual_cost)
    expected = float(anomaly.expected_cost)
    delta = actual - expected
    direction = "up" if delta >= 0 else "down"

    lines = [
        f":rotating_light: *Cost anomaly detected — {anomaly.service}* ({anomaly.date.isoformat()})",
        (
            f"• Actual: *${actual:,.2f}* vs. expected *${expected:,.2f}* "
            f"({direction} {abs(anomaly.pct_deviation):.0f}%, delta ${delta:,.2f})"
        ),
        f"• Z-score: {anomaly.z_score:.2f}",
    ]
    if anomaly.top_contributor:
        lines.append(f"• Top contributor: {anomaly.top_contributor}")
    if anomaly.root_cause_explanation:
        lines.append(f"• Likely cause: {anomaly.root_cause_explanation}")

    return "\n".join(lines)


async def _post_to_slack(webhook_url: str, message_text: str, timeout: float) -> None:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(webhook_url, json={"text": message_text})
        response.raise_for_status()


async def send_anomaly_alert(
    session: AsyncSession,
    anomaly: Anomaly,
    webhook_url: str,
    dry_run: bool = False,
) -> AlertResult:
    settings = get_settings()
    cost_delta = float(anomaly.actual_cost) - float(anomaly.expected_cost)

    llm_explanation = await generate_root_cause_guess(
        service=anomaly.service,
        cost_delta=cost_delta,
        pct_deviation=anomaly.pct_deviation,
        top_contributor=anomaly.top_contributor,
    )
    used_llm = llm_explanation is not None
    if used_llm:
        anomaly.root_cause_explanation = llm_explanation
        if anomaly.id is not None:  # a real, persisted anomaly -- not a test message
            session.add(anomaly)
            await session.commit()

    message_text = build_slack_message(anomaly)

    if dry_run:
        logger.info("[dry-run] Slack alert for %s:\n%s", anomaly.service, message_text)
        return AlertResult(
            service=anomaly.service,
            sent=False,
            dry_run=True,
            used_llm_explanation=used_llm,
            message_text=message_text,
        )

    try:
        await _post_to_slack(webhook_url, message_text, settings.slack_timeout_seconds)
    except httpx.HTTPError as exc:
        logger.exception("Failed to post Slack alert for %s", anomaly.service)
        return AlertResult(
            service=anomaly.service,
            sent=False,
            dry_run=False,
            used_llm_explanation=used_llm,
            message_text=message_text,
            error=str(exc),
        )

    return AlertResult(
        service=anomaly.service,
        sent=True,
        dry_run=False,
        used_llm_explanation=used_llm,
        message_text=message_text,
    )


async def _resolve_alert_config(session: AsyncSession, service: str | None) -> AlertConfig | None:
    """Per-service config takes precedence; falls back to the global default
    row (service IS NULL); falls back further to a deploy-time webhook from
    settings if nobody has configured a global row in the DB yet at all."""
    if service:
        result = await session.execute(
            select(AlertConfig).where(AlertConfig.service == service, AlertConfig.enabled.is_(True))
        )
        config = result.scalar_one_or_none()
        if config is not None:
            return config

    result = await session.execute(
        select(AlertConfig).where(AlertConfig.service.is_(None), AlertConfig.enabled.is_(True))
    )
    global_config = result.scalar_one_or_none()
    if global_config is not None:
        return global_config

    settings = get_settings()
    if settings.slack_webhook_url:
        return AlertConfig(
            service=None,
            z_threshold=DEFAULT_Z_THRESHOLD,
            slack_webhook_url=settings.slack_webhook_url,
            enabled=True,
        )
    return None


async def detect_and_alert(
    session: AsyncSession,
    as_of=None,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
    dry_run: bool | None = None,
) -> list[AlertResult]:
    """Runs anomaly detection, then sends (or logs, in dry-run) a Slack alert
    for each newly flagged anomaly that has an enabled alert_config with a
    webhook configured."""
    settings = get_settings()
    effective_dry_run = settings.alerts_dry_run if dry_run is None else dry_run

    anomalies = await detect_and_record_anomalies(session, as_of=as_of, z_threshold=z_threshold)

    results: list[AlertResult] = []
    for anomaly in anomalies:
        config = await _resolve_alert_config(session, anomaly.service)
        if config is None or not config.slack_webhook_url:
            logger.info("No enabled alert config/webhook for %s; skipping Slack alert", anomaly.service)
            continue

        result = await send_anomaly_alert(session, anomaly, config.slack_webhook_url, dry_run=effective_dry_run)
        results.append(result)

    return results


async def send_test_alert(
    session: AsyncSession,
    service: str | None = None,
    slack_webhook_url: str | None = None,
    dry_run: bool | None = None,
) -> AlertResult:
    """Builds a fake anomaly with example numbers and runs it through the
    real alert pipeline (LLM guess + Slack format + send), without touching
    the database. Used by POST /alerts/test."""
    settings = get_settings()
    effective_dry_run = settings.alerts_dry_run if dry_run is None else dry_run

    webhook_url = slack_webhook_url
    if webhook_url is None:
        config = await _resolve_alert_config(session, service)
        webhook_url = config.slack_webhook_url if config else None

    test_anomaly = Anomaly(
        service=service or "Test Service",
        date=datetime.now(UTC).date(),
        actual_cost=Decimal("1234.56"),
        expected_cost=Decimal("234.56"),
        z_score=4.20,
        pct_deviation=426.3,
        top_contributor="Example SKU",
        root_cause_explanation=(
            "Test Service cost was $1,234.56, 426% higher than the $234.56 expected "
            "from its trend (z=4.20). Largest contributor: Example SKU."
        ),
        status="open",
    )

    if webhook_url is None:
        message_text = build_slack_message(test_anomaly)
        logger.info("No Slack webhook configured for test alert; message not sent:\n%s", message_text)
        return AlertResult(
            service=test_anomaly.service,
            sent=False,
            dry_run=effective_dry_run,
            used_llm_explanation=False,
            message_text=message_text,
            error="no Slack webhook configured (pass slack_webhook_url or set one in alert_config)",
        )

    return await send_anomaly_alert(session, test_anomaly, webhook_url, dry_run=effective_dry_run)
