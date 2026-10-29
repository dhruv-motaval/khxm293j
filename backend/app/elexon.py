"""Small, defensive client for Elexon's public Insights API."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import settings

UK = ZoneInfo("Europe/London")
UTC = timezone.utc


class ElexonError(RuntimeError):
    """Raised when Elexon cannot provide a usable response."""


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "items", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ElexonError("Elexon returned an unrecognised response shape.")


async def _get_rows(client: httpx.AsyncClient, dataset: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    url = f"{settings.elexon_base_url.rstrip('/')}/datasets/{dataset}/stream"
    params = {"publishDateTimeFrom": _iso_utc(start), "publishDateTimeTo": _iso_utc(end)}
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        detail = response.text[:240].replace("\n", " ")
        raise ElexonError(f"Elexon {dataset} request failed ({response.status_code}): {detail}")
    try:
        return _extract_rows(response.json())
    except ValueError as exc:
        raise ElexonError(f"Elexon {dataset} returned invalid JSON.") from exc


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _fuel_type(row: dict[str, Any]) -> str:
    value = row.get("fuelType", row.get("fuel", row.get("fuel_type", "")))
    return str(value).strip().upper()


def _value(row: dict[str, Any]) -> float | None:
    # The challenge specifies `generation`; the alternate names protect against
    # harmless casing/schema differences in archived API responses.
    return _number(row.get("generation", row.get("Generation")))


def _start_time(row: dict[str, Any]) -> datetime | None:
    return _parse_datetime(row.get("startTime", row.get("start_time")))


def _publish_time(row: dict[str, Any]) -> datetime | None:
    return _parse_datetime(row.get("publishTime", row.get("publish_time")))


def cutoff_for_delivery(start_time_utc: datetime, cutoff: str) -> datetime:
    """Return the prior local delivery date's cutoff as an aware UTC instant."""
    local_delivery_date = start_time_utc.astimezone(UK).date()
    hour, minute = (int(part) for part in cutoff.split(":"))
    local_cutoff = datetime.combine(local_delivery_date - timedelta(days=1), time(hour, minute), tzinfo=UK)
    return local_cutoff.astimezone(UTC)


def _actuals_by_start(rows: list[dict[str, Any]]) -> dict[datetime, tuple[float, Any]]:
    actuals: dict[datetime, tuple[datetime, float, Any]] = {}
    for row in rows:
        if _fuel_type(row) != "WIND":
            continue
        start = _start_time(row)
        generation = _value(row)
        if start is None or generation is None:
            continue
        published = _publish_time(row) or datetime.min.replace(tzinfo=UTC)
        previous = actuals.get(start)
        # If the source provides revisions, use the latest row for each period.
        if previous is None or published >= previous[0]:
            actuals[start] = (published, generation, row.get("settlementPeriod", row.get("settlement_period")))
    return {start: (value, settlement_period) for start, (_, value, settlement_period) in actuals.items()}


def _forecasts_by_start(rows: list[dict[str, Any]]) -> dict[datetime, list[tuple[datetime, float]]]:
    forecasts: dict[datetime, list[tuple[datetime, float]]] = {}
    for row in rows:
        start = _start_time(row)
        publish = _publish_time(row)
        generation = _value(row)
        if start is None or publish is None or generation is None:
            continue
        forecasts.setdefault(start, []).append((publish, generation))
    return forecasts


def build_matched_periods(
    actual_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    month: str,
    cutoff: str = "09:00",
) -> list[dict[str, Any]]:
    """Match actuals to the latest forecast published by each period's cutoff.

    Forecast records published after the day-ahead decision cutoff are excluded,
    preventing look-ahead leakage in the accuracy metrics.
    """
    actuals = _actuals_by_start(actual_rows)
    forecasts = _forecasts_by_start(forecast_rows)
    year, month_number = (int(part) for part in month.split("-"))
    start_date = date(year, month_number, 1)
    end_date = date(year + (month_number == 12), 1 if month_number == 12 else month_number + 1, 1)
    start_local = datetime.combine(start_date, time.min, tzinfo=UK)
    end_local = datetime.combine(end_date, time.min, tzinfo=UK)
    start_utc = start_local.astimezone(UTC)
    end_utc = end_local.astimezone(UTC)

    matched: list[dict[str, Any]] = []
    for start, (actual, settlement_period) in sorted(actuals.items()):
        if not (start_utc <= start < end_utc):
            continue
        cutoff_dt = cutoff_for_delivery(start, cutoff)
        eligible = [(published, value) for published, value in forecasts.get(start, []) if published <= cutoff_dt]
        if not eligible:
            continue
        published, forecast = max(eligible, key=lambda pair: pair[0])
        error = forecast - actual  # Positive means wind generation was over-forecast.
        local_start = start.astimezone(UK)
        lead_hours = (start - published).total_seconds() / 3600
        matched.append({
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "local_time": local_start.isoformat(),
            "delivery_date": local_start.date().isoformat(),
            "settlement_period": settlement_period,
            "forecast_mw": round(forecast, 3),
            "actual_mw": round(actual, 3),
            "error_mw": round(error, 3),
            "absolute_error_mw": round(abs(error), 3),
            "absolute_percentage_error": round(abs(error) / actual * 100, 3) if actual >= 100 else None,
            "publish_time": published.isoformat().replace("+00:00", "Z"),
            "cutoff_time": cutoff_dt.isoformat().replace("+00:00", "Z"),
            "forecast_lead_hours": round(lead_hours, 2),
        })
    return matched


async def fetch_month(month: str, cutoff: str = "09:00") -> dict[str, Any]:
    """Fetch actuals and forecast revisions for a UTC-safe UK delivery month."""
    year, month_number = (int(part) for part in month.split("-"))
    start_date = date(year, month_number, 1)
    end_date = date(year + (month_number == 12), 1 if month_number == 12 else month_number + 1, 1)
    # Dataset stream filters use publication timestamps. Fetch a publication
    # window wide enough to include the forecast versions available before the
    # first delivery-day cutoff and outturn records published shortly after the
    # final settlement period. `build_matched_periods` filters delivery startTime.
    start_local = datetime.combine(start_date, time.min, tzinfo=UK)
    end_local = datetime.combine(end_date, time.min, tzinfo=UK)
    actual_publish_start = start_local.astimezone(UTC)
    actual_publish_end = (end_local + timedelta(days=1)).astimezone(UTC)
    forecast_publish_start = (start_local - timedelta(days=2)).astimezone(UTC)
    forecast_publish_end = (end_local + timedelta(days=1)).astimezone(UTC)
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
        actual_rows = await _get_rows(client, "FUELHH", actual_publish_start, actual_publish_end)
        forecast_rows = await _get_rows(client, "WINDFOR", forecast_publish_start, forecast_publish_end)
    # Some API versions return more fuels than requested; the domain layer filters WIND.
    matched = build_matched_periods(actual_rows, forecast_rows, month, cutoff)
    return {
        "month": month,
        "cutoff": cutoff,
        "actual_rows_received": len(actual_rows),
        "forecast_rows_received": len(forecast_rows),
        "matched_periods": matched,
        "source": "elexon",
    }
