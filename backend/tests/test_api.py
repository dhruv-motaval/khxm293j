from fastapi.testclient import TestClient

import app.main as main_module


def test_health_endpoint():
    client = TestClient(main_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_rejects_bad_month_and_cutoff():
    client = TestClient(main_module.app)
    assert client.get("/api/dashboard?month=January-2026").status_code == 422
    assert client.get("/api/dashboard?month=2026-01&cutoff=9am").status_code == 422


def test_dashboard_route_shapes_response_without_network(monkeypatch):
    async def fake_fetch_month(month: str, cutoff: str):
        return {
            "month": month,
            "cutoff": cutoff,
            "source": "elexon",
            "actual_rows_received": 1,
            "forecast_rows_received": 1,
            "matched_periods": [{
                "start_time": "2026-01-01T00:00:00Z",
                "local_time": "2026-01-01T00:00:00+00:00",
                "delivery_date": "2026-01-01",
                "settlement_period": 1,
                "forecast_mw": 100,
                "actual_mw": 90,
                "error_mw": 10,
                "absolute_error_mw": 10,
                "absolute_percentage_error": None,
                "publish_time": "2025-12-31T08:30:00Z",
                "cutoff_time": "2025-12-31T09:00:00Z",
                "forecast_lead_hours": 15.5,
            }],
        }

    monkeypatch.setattr(main_module, "fetch_month", fake_fetch_month)
    client = TestClient(main_module.app)
    response = client.get("/api/dashboard?month=2026-01&cutoff=09:00")
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["matched_periods"] == 1
    assert body["periods"][0]["error_mw"] == 10
    assert body["source"] == "elexon"
