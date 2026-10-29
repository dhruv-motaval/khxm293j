# Demo recording script — Wind Signal

Target runtime: 9 minutes 20 seconds. Use the actual live dashboard and only quote metrics shown in the running app. Do not invent or prefill a number if the upstream API is unavailable.

## Part 1 — Client presentation (4:40 maximum)

### 0:00–0:35 | Set the context

"This pilot addresses one specific purchasing problem: the buyer has to estimate the wind generation available on the delivery day before that day arrives. Wind forecasts are revised during the day, so an accurate historical review must distinguish what was known when the decision was made from what became known later. This portal focuses on national GB wind generation for January 2026, using the two Elexon datasets in the brief."

### 0:35–1:20 | Read the summary

"The top row summarises the quality of the selected forecast vintage. Mean absolute error gives the average size of a miss in megawatts. Root mean squared error penalises large misses more strongly. Forecast bias preserves the sign: a positive result means the forecast was higher than actual wind generation on average, while a negative result means it was lower. Coverage tells us how much of the month's half-hourly data could be matched without filling gaps."

Pause briefly and let the reviewer read the values displayed by the live source.

### 1:20–2:00 | Explain the time cutoff

"The default decision cutoff is 09:00 UK time on the preceding day. The brief does not define one single cutoff for all GB day-ahead products, so this is an explicit pilot assumption. Each row uses the latest forecast publication at or before that cutoff. A forecast published after the cutoff is excluded, even if it would later prove more accurate. The selector lets us test another assumed cutoff transparently."

Change the cutoff and press Apply. Wait for the API response and show the result updating.

### 2:00–3:10 | Explore the monthly pattern

"The left chart compares daily mean forecast and actual wind generation. It gives the buyer a quick view of broad over- and under-forecast patterns. The right chart shows daily mean absolute error, making higher-error days easier to spot. These are daily averages of the matched half-hours only, so coverage should be checked before interpreting a day's result."

Hover over a high-error day and a low-error day if the chart data makes that comparison available.

### 3:10–4:05 | Inspect a delivery day

"The detailed table brings the decision-time data together at half-hour resolution. We can inspect the selected forecast, actual output, signed and absolute errors, publication timestamp, and forecast lead time. This makes the result auditable: the user can see which published forecast was scored, not just a monthly aggregate. The CSV export allows further review outside the portal."

Choose a delivery day, scroll through a few rows, and export the CSV if appropriate.

### 4:05–4:40 | Set expectations

"This is a wind forecast accuracy pilot, not a complete procurement optimiser. The required scope excludes electricity demand and other generation sources, so these two datasets cannot establish the total residual demand or an exact thermal procurement volume. The output quantifies one important source of uncertainty while keeping that boundary explicit."

## Part 2 — Technical handover (4:40 maximum)

### 0:00–0:45 | Architecture

"The app has a React and TypeScript frontend and a FastAPI Python backend. The browser requests one dashboard response from the API. The backend calls the public Elexon Insights dataset endpoints and performs timestamp alignment and scoring. There is no database or API key in this pilot; responses are cached in process for fifteen minutes to avoid repeating the same historical query for every interaction."

### 0:45–1:40 | Source and timestamp handling

"FUELHH contains actual half-hourly generation by fuel type, and the code filters it to WIND. WINDFOR contains wind forecast records with a target start time and a publication time. The stream requests use publication-time windows wide enough to include the preceding-day forecasts and the final outturn records. The data is parsed as timezone-aware timestamps. Delivery dates and the previous-day cutoff use Europe/London; timestamps are normalised to UTC for matching."

### 1:40–2:35 | Forecast-vintage selection and metrics

"For each actual period in January, the backend calculates the previous local delivery date and cutoff, filters forecast records to publishTime at or before that instant, and takes the latest eligible publication. It then matches by exact startTime. Error is forecast minus actual. MAE, RMSE and bias use all matched records. MAPE excludes actual wind output below 100 megawatts because relative error is unstable near zero; the UI tells the reviewer how many periods contribute to that metric. Missing values are not imputed."

### 2:35–3:20 | Reliability and failure behavior

"If Elexon returns an error or a response shape the backend does not recognise, the API returns an error and the frontend displays it. The frontend does not fall back to fabricated data. Configuration such as the source API URL, cache duration, timeout and CORS origins is environment-backed. The root compose file starts both containers for local review."

### 3:20–4:05 | Tests

Run `cd backend` and `pytest -q` in the recording. Show the test that supplies multiple forecast vintages and proves that a record published after the cutoff is rejected. Explain that these are deterministic unit tests; the challenge environment should also verify the live Elexon call because network access varies by deployment environment.

### 4:05–4:40 | Deployment and limits

"The frontend is built as a static Vite site for Vercel. The backend has its own Dockerfile and can run as a Render web service. The frontend receives the backend URL through VITE_API_BASE_URL. Before submission, both services must be deployed, opened in an incognito window, and recorded in the README and submission form. The most important limitation is deliberate: wind-only data cannot calculate the total procurement requirement without demand and other generation."

## Recording checklist

- Keep the full recording under 10 minutes, including transitions.
- Show the deployed app, not only slides or screenshots.
- Use values actually displayed by the live Elexon response.
- Show tests running in a terminal.
- Upload as **Unlisted** on YouTube.
- Open the video URL in a private/incognito window before submitting.
