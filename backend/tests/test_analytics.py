from app.analytics import calculate_metrics, dashboard_payload


def period(day, forecast, actual):
    error = forecast - actual
    return {
        "start_time": f"2026-01-{day:02d}T00:00:00Z",
        "local_time": f"2026-01-{day:02d}T00:00:00+00:00",
        "delivery_date": f"2026-01-{day:02d}",
        "forecast_mw": forecast,
        "actual_mw": actual,
        "error_mw": error,
        "absolute_error_mw": abs(error),
        "absolute_percentage_error": abs(error) / actual * 100 if actual >= 100 else None,
        "publish_time": "2025-12-31T08:30:00Z",
        "cutoff_time": "2025-12-31T09:00:00Z",
        "forecast_lead_hours": 15.5,
    }


def test_calculate_metrics_error_sign_and_values():
    periods = [period(1, 110, 100), period(1, 80, 100)]
    metrics = calculate_metrics(periods)
    assert metrics["matched_periods"] == 2
    assert metrics["mae_mw"] == 15
    assert metrics["rmse_mw"] == 15.81
    assert metrics["bias_mw"] == -5
    assert metrics["mape_pct"] == 15


def test_mape_excludes_low_actual_values_but_other_metrics_do_not():
    metrics = calculate_metrics([period(1, 20, 10), period(1, 100, 200)])
    assert metrics["matched_periods"] == 2
    assert metrics["mae_mw"] == 55
    assert metrics["mape_periods"] == 1
    assert metrics["mape_pct"] == 50


def test_empty_metrics_return_null_values():
    metrics = calculate_metrics([])
    assert metrics["matched_periods"] == 0
    assert metrics["mae_mw"] is None
    assert metrics["mape_pct"] is None


def test_dashboard_payload_includes_scope_and_daily_summary():
    raw = {
        "month": "2026-01",
        "cutoff": "09:00",
        "source": "elexon",
        "actual_rows_received": 48,
        "forecast_rows_received": 100,
        "matched_periods": [period(1, 110, 100), period(1, 90, 100)],
    }
    payload = dashboard_payload(raw)
    assert len(payload["daily"]) == 1
    assert payload["daily"][0]["periods"] == 2
    assert "cannot determine total electricity procurement" in payload["methodology"]["scope_limit"]
