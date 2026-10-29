from datetime import datetime, timezone

from app.elexon import build_matched_periods

UTC = timezone.utc


def test_selects_latest_forecast_before_previous_day_cutoff():
    actuals = [{
        "fuelType": "WIND",
        "startTime": "2026-01-02T10:00:00Z",
        "publishTime": "2026-01-02T10:30:00Z",
        "generation": 500,
        "settlementPeriod": 21,
    }]
    forecasts = [
        {"startTime": "2026-01-02T10:00:00Z", "publishTime": "2026-01-01T03:30:00Z", "generation": 480},
        {"startTime": "2026-01-02T10:00:00Z", "publishTime": "2026-01-01T08:30:00Z", "generation": 510},
        # Must be excluded because it was published after the configured cutoff.
        {"startTime": "2026-01-02T10:00:00Z", "publishTime": "2026-01-01T10:30:00Z", "generation": 550},
    ]
    result = build_matched_periods(actuals, forecasts, "2026-01", "09:00")
    assert len(result) == 1
    assert result[0]["forecast_mw"] == 510
    assert result[0]["actual_mw"] == 500
    assert result[0]["error_mw"] == 10
    assert result[0]["publish_time"] == "2026-01-01T08:30:00Z"


def test_ignores_non_wind_actual_rows_and_unmatched_periods():
    actuals = [
        {"fuelType": "GAS", "startTime": "2026-01-02T10:00:00Z", "generation": 900},
        {"fuelType": "WIND", "startTime": "2026-01-02T10:30:00Z", "generation": 400},
    ]
    forecasts = [
        {"startTime": "2026-01-02T10:00:00Z", "publishTime": "2026-01-01T08:30:00Z", "generation": 600},
    ]
    result = build_matched_periods(actuals, forecasts, "2026-01", "09:00")
    assert result == []
