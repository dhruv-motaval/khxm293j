from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from math import sqrt
from statistics import mean
from typing import Any


def calculate_metrics(periods: list[dict[str, Any]], expected_periods: int = 1488) -> dict[str, Any]:
    if not periods:
        return {
            "matched_periods": 0,
            "coverage_pct": 0.0,
            "mae_mw": None,
            "rmse_mw": None,
            "bias_mw": None,
            "mape_pct": None,
            "mape_periods": 0,
            "forecast_mean_mw": None,
            "actual_mean_mw": None,
        }
    errors = [float(p["error_mw"]) for p in periods]
    absolute_errors = [abs(v) for v in errors]
    mape_values = [float(p["absolute_percentage_error"]) for p in periods if p.get("absolute_percentage_error") is not None]
    return {
        "matched_periods": len(periods),
        # January has 48 settlement periods per day except clock-change days;
        # compare with actual records, so this is based on the expected 31*48.
        "coverage_pct": round(len(periods) / expected_periods * 100, 2) if expected_periods else 0.0,
        "mae_mw": round(mean(absolute_errors), 2),
        "rmse_mw": round(sqrt(mean(v * v for v in errors)), 2),
        "bias_mw": round(mean(errors), 2),
        "mape_pct": round(mean(mape_values), 2) if mape_values else None,
        "mape_periods": len(mape_values),
        "forecast_mean_mw": round(mean(float(p["forecast_mw"]) for p in periods), 2),
        "actual_mean_mw": round(mean(float(p["actual_mw"]) for p in periods), 2),
    }


def dashboard_payload(raw: dict[str, Any]) -> dict[str, Any]:
    periods = raw["matched_periods"]
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for period in periods:
        by_day[period["delivery_date"]].append(period)

    daily = []
    for day, values in sorted(by_day.items()):
        errors = [float(p["error_mw"]) for p in values]
        daily.append({
            "date": day,
            "forecast_mw": round(mean(float(p["forecast_mw"]) for p in values), 2),
            "actual_mw": round(mean(float(p["actual_mw"]) for p in values), 2),
            "mae_mw": round(mean(abs(v) for v in errors), 2),
            "bias_mw": round(mean(errors), 2),
            "periods": len(values),
        })

    year, month_number = (int(part) for part in raw["month"].split("-"))
    start_date = date(year, month_number, 1)
    end_date = date(year + (month_number == 12), 1 if month_number == 12 else month_number + 1, 1)
    zone = ZoneInfo("Europe/London")
    start_local = datetime.combine(start_date, time.min, tzinfo=zone)
    end_local = datetime.combine(end_date, time.min, tzinfo=zone)
    expected = int((end_local.astimezone(ZoneInfo("UTC")) - start_local.astimezone(ZoneInfo("UTC"))).total_seconds() / 1800)
    metrics = calculate_metrics(periods, expected)
    return {
        "month": raw["month"],
        "cutoff": raw["cutoff"],
        "timezone": "Europe/London",
        "source": raw["source"],
        "metrics": metrics,
        "daily": daily,
        "periods": periods,
        "data_quality": {
            "actual_rows_received": raw.get("actual_rows_received"),
            "forecast_rows_received": raw.get("forecast_rows_received"),
            "matched_periods": len(periods),
            "expected_periods": expected,
            "unmatched_periods": max(0, (expected or len(periods)) - len(periods)),
            "completeness_note": f"Coverage compares {len(periods):,} matched forecast records with {expected:,} possible settlement periods in {raw['month']} (48 per day). WINDFOR forecasts are published hourly, so matched records occur hourly and no missing values are imputed.",
        },
        "methodology": {
            "forecast_selection": "For each delivery period with a whole-hour startTime in the forecast dataset, select the record with the latest publishTime at or before the configured cutoff on the previous UK calendar day.",
            "forecast_resolution": "The WINDFOR forecast dataset is published at hourly resolution (whole-hour startTimes only), while the FUELHH actual dataset covers all 48 settlement periods per day. A period is matched only where both datasets contain a record at the identical startTime, so matched periods appear hourly and coverage is reported against every settlement period of the month.",
            "error_sign": "Forecast error = forecast MW − actual MW. Positive bias means wind was over-forecast; negative bias means it was under-forecast.",
            "mape": "MAPE excludes matched periods where actual wind generation is below 100 MW to avoid unstable percentages near zero. MAE, RMSE and bias use every matched period.",
            "scope_limit": "Wind generation alone cannot determine total electricity procurement or thermal generation requirements; demand and other generation sources are intentionally outside this brief's data scope.",
        },
    }
