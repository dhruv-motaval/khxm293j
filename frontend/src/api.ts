export type Period = {
  start_time: string
  local_time: string
  delivery_date: string
  settlement_period?: number | null
  forecast_mw: number
  actual_mw: number
  error_mw: number
  absolute_error_mw: number
  absolute_percentage_error: number | null
  publish_time: string
  cutoff_time: string
  forecast_lead_hours: number
}

export type DailyPoint = {
  date: string
  forecast_mw: number
  actual_mw: number
  mae_mw: number
  bias_mw: number
  periods: number
}

export type Dashboard = {
  month: string
  cutoff: string
  timezone: string
  source: string
  metrics: {
    matched_periods: number
    coverage_pct: number
    mae_mw: number | null
    rmse_mw: number | null
    bias_mw: number | null
    mape_pct: number | null
    mape_periods: number
    forecast_mean_mw: number | null
    actual_mean_mw: number | null
  }
  daily: DailyPoint[]
  periods: Period[]
  data_quality: {
    actual_rows_received: number | null
    forecast_rows_received: number | null
    matched_periods: number
    expected_periods: number | null
    unmatched_periods: number
    completeness_note: string
  }
  methodology: {
    forecast_selection: string
    forecast_resolution: string
    error_sign: string
    mape: string
    scope_limit: string
  }
}

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export async function fetchDashboard(month: string, cutoff: string): Promise<Dashboard> {
  const response = await fetch(`${apiBase}/api/dashboard?month=${encodeURIComponent(month)}&cutoff=${encodeURIComponent(cutoff)}`)
  if (!response.ok) {
    let message = `API error (${response.status})`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the HTTP message if the response body is not JSON.
    }
    throw new Error(message)
  }
  return response.json() as Promise<Dashboard>
}
