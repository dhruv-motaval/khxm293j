# Wind Signal — UK Wind Forecast Workbench

A React + FastAPI pilot dashboard for reviewing GB national wind-generation forecast accuracy around day-ahead electricity purchasing decisions. The assessment window is January 2026, using **only** Elexon's `FUELHH` actual-generation dataset and `WINDFOR` forecast dataset, as required by the challenge brief.

> **Data integrity:** the app does not silently replace failed API requests with fabricated values. Metrics are calculated only from records returned by Elexon that have both an actual wind-generation value and a forecast published before the configured decision cutoff.

## What it does

- Shows daily mean forecast and actual GB wind generation for January 2026.
- Reconstructs a day-ahead forecast vintage for each half-hour using `publishTime` and `startTime`.
- Lets the reviewer change the historical decision cutoff (default `09:00`, Europe/London) and recomputes the forecast-vintage selection.
- Calculates MAE, RMSE, forecast bias, coverage, and a guarded MAPE measure.
- Provides half-hourly inspection including the selected forecast publication time, forecast lead time, actual generation, error, and absolute error.
- Exports matched half-hourly records to CSV.
- Documents method assumptions and limits in the UI and this README.

## Technology

- **Frontend:** React 18, TypeScript, Vite, Recharts, Lucide icons.
- **Backend:** Python 3.12, FastAPI, HTTPX, Pydantic Settings.
- **Deployment/container:** Docker, Docker Compose; intended for a Vercel frontend and Render-hosted API.
- **Tests:** Pytest unit tests for forecast-vintage filtering and metric calculations.

## Data sources and access

The backend calls the public Elexon Insights API without an API key:

- Actual half-hourly generation: `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
- Wind forecast publications: `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
- API documentation: https://bmrs.elexon.co.uk/api-documentation
- Elexon developer portal: https://developer.data.elexon.co.uk/

The backend requests publication-time windows from the stream endpoints, wide enough to include forecast vintages created before the first January delivery date and outturn records published just after the last delivery period. It then filters the records by delivery `startTime`, filters actual generation to `fuelType == "WIND"`, and retains forecast records with their publication timestamps. Finally it selects the latest forecast version that was published on or before the decision cutoff for each delivery period. The exact upstream query contract can evolve; validate API responses after deploying and before presenting the live demo.

Please preserve Elexon's attribution and terms when redistributing or deploying data from the API. See the [Elexon developer portal terms](https://developer.data.elexon.co.uk/).

## Decision-time assumption

The challenge says that purchasing decisions are made one day before delivery but does not specify a universal cutoff timestamp. This implementation uses **09:00 Europe/London on the preceding calendar day** as the default analytical cutoff. This is a configurable, documented modelling assumption, not a claim that every UK market product has the same gate closure. To test another assumed cutoff, use the time selector and press **Apply**.

For every delivery half-hour:

1. Convert `startTime` to the `Europe/London` delivery date.
2. Calculate that date minus one calendar day at the configured cutoff.
3. Discard forecast records with `publishTime` after that instant.
4. Choose the remaining forecast with the latest `publishTime`.
5. Match it to the actual `FUELHH` WIND record for the same start time.
6. Exclude the period from scored metrics if either side is missing. Do not impute data.

January 2026 is in GMT, but the code uses `zoneinfo` and `Europe/London` so that date and cutoff calculations remain explicit if the month is changed for development.

## Metric definitions

- **Forecast error / bias per period:** `forecast_mw - actual_mw`. Positive means wind output was over-forecast; negative means it was under-forecast.
- **MAE:** mean absolute error across all matched half-hours, in MW.
- **RMSE:** square root of mean squared error, in MW; larger misses receive more weight.
- **Bias:** mean signed forecast error, in MW.
- **MAPE:** mean absolute percentage error, excluding periods with actual wind generation below 100 MW because percentages become unstable near zero. The UI shows how many periods contribute to MAPE. MAE, RMSE and bias still use all matched periods.
- **Coverage:** matched periods divided by the expected number of half-hour periods in the month. Missing records are reported as missing; no estimates are inserted.

This is a forecast-quality review, not a trading P&L, price forecast, or complete procurement calculator. With only wind forecast and wind actual data, the app cannot determine consumer demand, the residual demand to be served, the power deficit, or required thermal procurement. Those require extra datasets, which the challenge explicitly excludes.

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── analytics.py          # Metric calculation and dashboard response shape
│   │   ├── config.py             # Environment-backed configuration
│   │   ├── elexon.py             # Elexon requests and forecast-vintage selection
│   │   └── main.py               # FastAPI routes and short-lived cache
│   ├── tests/
│   │   ├── test_analytics.py
│   │   └── test_forecast_selection.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api.ts                # Typed API client and response contracts
│   │   ├── App.tsx               # Dashboard and interaction logic
│   │   ├── main.tsx              # React entry point
│   │   └── styles.css            # Responsive dashboard styling
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── vercel.json
├── docker-compose.yml
├── render.yaml
└── README.md
```

## Run locally

### Option A — Docker Compose

Install Docker Desktop, then run from the repository root:

```bash
docker compose up --build
```

Open the frontend at http://localhost:8080. The API root is http://localhost:8000, interactive docs at http://localhost:8000/docs, and health check at http://localhost:8000/health.

### Option B — Run services separately

Backend (Python 3.12 recommended):

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+): open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` and `/health` to `http://localhost:8000`.

### API examples

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/api/dashboard?month=2026-01&cutoff=09:00"
```

Query parameters:

- `month`: `YYYY-MM`; the assessment target is `2026-01`.
- `cutoff`: `HH:MM` in `Europe/London` on the day before delivery; defaults to `09:00`.

The backend caches each month/cutoff response in memory for 15 minutes by default (`CACHE_TTL_SECONDS`). Configure `ELEXON_BASE_URL`, `REQUEST_TIMEOUT_SECONDS`, and `CORS_ORIGINS` using environment variables; see `backend/.env.example`.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Tests cover metric arithmetic, MAPE low-output handling, the forecast error sign convention, and rejection of forecasts published after the prior-day cutoff. They are unit tests; a live test against Elexon's service must also be run in an environment with outbound network access.

## Deployment

A live public deployment is **not embedded in this source archive**. Deploy the API and frontend separately, then put the API URL into the Vercel frontend environment.

### 1. Deploy the API to Render

1. Push this directory to a public GitHub repository.
2. In Render, create a new Web Service from the repository. Set **Root Directory** to `backend`, environment/runtime to Docker, and health check path to `/health`.
3. Set `ELEXON_BASE_URL=https://data.elexon.co.uk/bmrs/api/v1`, `CACHE_TTL_SECONDS=900`, and `REQUEST_TIMEOUT_SECONDS=30`.
4. Deploy and confirm `https://YOUR-API.onrender.com/health` returns `{"status":"ok","service":"wind-forecast-workbench"}`.

The included `render.yaml` is a starting point; review its service name before applying it.

### 2. Deploy the frontend to Vercel

1. Import the same repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Set `VITE_API_BASE_URL=https://YOUR-API.onrender.com` in the Vercel project environment.
4. Build command: `npm run build`; output directory: `dist`.
5. Deploy, open the Vercel URL in a private/incognito window, and verify the dashboard loads real data.

The API permits `*.vercel.app` origins by regex. For a custom domain, add that exact origin to `CORS_ORIGINS` on the API service and redeploy.

## Required 10-minute demo video outline

The assessment brief requires an unlisted YouTube video with two parts and a maximum total duration of 10 minutes. Do not submit before the recording has been uploaded and checked in a private/incognito window.

### Part 1 — Client pitch (target 4:30–4:50)

- **0:00–0:35 — Business problem:** Wind is variable; the buyer needs an auditable day-ahead view of forecast uncertainty.
- **0:35–1:20 — What the portal shows:** January 2026, national wind-only data, daily forecast-versus-actual trend and error metrics.
- **1:20–2:15 — Decision-time integrity:** Explain the selected cutoff and why forecast vintages published after it are excluded.
- **2:15–3:25 — Explore a day:** Change the day, inspect individual half-hours, publication time, lead time, and error direction.
- **3:25–4:15 — Accuracy interpretation:** Explain MAE, RMSE, signed bias and the guarded MAPE.
- **4:15–4:50 — Scope honestly:** Explain that wind-only series quantify uncertainty but cannot calculate the total procurement deficit without demand data.

### Part 2 — Technical handover (target 4:30–4:50)

- **0:00–0:45 — Architecture:** React/Vite frontend → FastAPI backend → Elexon public API; no API key or database required for this pilot.
- **0:45–1:45 — Data pipeline:** `FUELHH` wind filter, `WINDFOR` publication versions, UTC parsing, `Europe/London` cutoff and exact `startTime` match.
- **1:45–2:40 — Analysis:** Error sign, MAE/RMSE/bias and MAPE threshold; coverage and missing records.
- **2:40–3:25 — Reliability:** API errors return a visible error; no fake-data fallback; small in-memory cache; config via environment variables.
- **3:25–4:05 — Tests:** Show `pytest -q` output and the test that proves the after-cutoff forecast is discarded.
- **4:05–4:50 — Deployment/repo:** Walk through Dockerfiles, compose, environment variables, deployment URLs, and known limitations.

## AI assistance disclosure

**AI tools were used during development** to assist with repository scaffolding, implementation drafting, test drafting, and documentation. Code, API assumptions, and the deployed behavior must be reviewed and validated before submission; AI assistance does not replace end-to-end verification.

## Submission checklist

- [ ] Run backend unit tests and record their result.
- [ ] Run `npm run build` and fix any TypeScript/build errors.
- [ ] Run Docker Compose locally and verify the API returns real Elexon records for January 2026.
- [ ] Confirm forecast revisions after the selected cutoff do not affect metrics.
- [ ] Deploy API and frontend; verify in a private/incognito browser.
- [ ] Record and upload the two-part video (maximum 10 minutes), set it to unlisted, and test the link in incognito.
- [ ] Create the public repository with an anonymous/random name as required by the challenge; remove personal references from repo metadata if anonymity is required.
- [ ] Fill out the challenge submission form with the public repository, live application and video URLs.
