import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Database,
  Download,
  ExternalLink,
  Gauge,
  RefreshCw,
  Wind,
} from 'lucide-react'
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar,
} from 'recharts'
import { fetchDashboard, type Dashboard, type Period } from './api'

const TARGET_MONTH = '2026-01'
const formatNumber = (value: number | null | undefined, digits = 0) =>
  value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits })
const formatDate = (value: string) => new Date(`${value}T12:00:00Z`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' })
const formatUKTime = (value: string, includeDate = false) => {
  const date = new Date(value)
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    ...(includeDate ? { day: '2-digit', month: 'short' } : {}),
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(date)
}
const csvCell = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`

function exportCsv(periods: Period[]) {
  const headers = ['delivery_date', 'start_time_utc', 'settlement_period', 'forecast_mw', 'actual_mw', 'error_mw', 'absolute_error_mw', 'absolute_percentage_error_pct', 'forecast_publish_time_utc', 'decision_cutoff_utc', 'forecast_lead_hours']
  const rows = periods.map((p) => [p.delivery_date, p.start_time, p.settlement_period, p.forecast_mw, p.actual_mw, p.error_mw, p.absolute_error_mw, p.absolute_percentage_error, p.publish_time, p.cutoff_time, p.forecast_lead_hours])
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `wind-forecast-${TARGET_MONTH}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

function MetricCard({ label, value, unit, detail, icon, tone = 'neutral' }: {
  label: string; value: string; unit: string; detail: string; icon: ReactNode; tone?: 'neutral' | 'positive' | 'negative'
}) {
  return (
    <article className="metric-card">
      <div className="metric-top"><span>{label}</span><span className={`metric-icon ${tone}`}>{icon}</span></div>
      <div className="metric-value">{value}<small>{unit}</small></div>
      <div className="metric-detail">{detail}</div>
    </article>
  )
}

function ChartTooltip({ active, payload, label, showDate = false }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="tooltip-label">{showDate ? formatDate(String(label)) : String(label)}</div>
      {payload.map((item: any) => item.value != null && (
        <div className="tooltip-row" key={item.dataKey}>
          <span className="tooltip-dot" style={{ background: item.color }} />
          <span>{item.name}</span><b>{formatNumber(item.value, 1)} MW</b>
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [cutoffInput, setCutoffInput] = useState('09:00')
  const [cutoff, setCutoff] = useState('09:00')
  const [selectedDay, setSelectedDay] = useState('2026-01-01')
  const [view, setView] = useState<'forecast' | 'methodology'>('forecast')

  const load = async (nextCutoff = cutoff) => {
    setLoading(true)
    setError('')
    setDashboard(null)
    try {
      const data = await fetchDashboard(TARGET_MONTH, nextCutoff)
      setDashboard(data)
      if (data.daily.length > 0 && !data.daily.some((item) => item.date === selectedDay)) setSelectedDay(data.daily[0].date)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load Elexon data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load('09:00') }, []) // initial assessment window

  const selectedPeriods = useMemo(
    () => dashboard?.periods.filter((period) => period.delivery_date === selectedDay) ?? [],
    [dashboard, selectedDay],
  )
  const selectedDaily = dashboard?.daily.find((item) => item.date === selectedDay)
  const metrics = dashboard?.metrics
  const biasTone = (metrics?.bias_mw ?? 0) > 0 ? 'negative' : (metrics?.bias_mw ?? 0) < 0 ? 'positive' : 'neutral'

  const downloadPeriods = () => {
    if (dashboard) exportCsv(dashboard.periods)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><Wind size={22} strokeWidth={1.8} /></div>
          <div><div className="brand-name">WIND<span>SIGNAL</span></div><div className="brand-subtitle">FORECAST WORKBENCH</div></div>
        </div>
        <div className="side-section-label">WORKSPACE</div>
        <button className={`nav-item ${view === 'forecast' ? 'active' : ''}`} onClick={() => setView('forecast')}><Activity size={17} /><span>Forecast accuracy</span><span className="nav-live" /></button>
        <button className={`nav-item ${view === 'methodology' ? 'active' : ''}`} onClick={() => setView('methodology')}><Gauge size={17} /><span>Methodology</span></button>
        <div className="sidebar-bottom">
          <div className="source-card">
            <div className="source-card-heading"><span className="source-pulse" /> DATA SOURCE</div>
            <div className="source-name">Elexon Insights API</div>
            <div className="source-description">FUELHH actuals · WINDFOR forecasts</div>
            <a href="https://bmrs.elexon.co.uk/api-documentation" target="_blank" rel="noreferrer">API documentation <ExternalLink size={12} /></a>
          </div>
          <div className="sidebar-footer">PILOT ANALYTICS <span>·</span> JAN 2026</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>ENERGY MARKETS</span><span className="crumb-divider">/</span><b>WIND FORECAST</b></div>
          <div className="topbar-right"><span className="historical-pill"><span /> HISTORICAL REVIEW</span><span className="vertical-rule" /><span className="period-label">DELIVERY MONTH <b>JAN 2026</b></span></div>
        </header>

        <div className="content-wrap">
          <section className="page-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> {view === 'methodology' ? 'METHOD & DATA INTEGRITY' : 'DAY-AHEAD DECISION SUPPORT'}</div>
              <h1>{view === 'methodology' ? <>Methodology <em>&amp; caveats</em></> : <>Wind forecast <em>accuracy</em></>}</h1>
              <p className="page-subtitle">{view === 'methodology' ? 'How the forecast vintage is selected, how each metric is calculated, and what this analysis cannot tell you.' : 'Compare the forecast available before the day-ahead trading window with actual GB wind generation.'}</p>
            </div>
          </section>

          {view === 'forecast' && (
          <section className="decision-strip">
            <div className="decision-icon"><Clock3 size={19} /></div>
            <div className="decision-text"><b>Decision-time reconstruction</b><span>Latest wind forecast published by <strong>{cutoff} UK time on the preceding day</strong> · later revisions excluded.</span></div>
            <div className="decision-control"><label htmlFor="cutoff">CUTOFF (UK)</label><input id="cutoff" value={cutoffInput} onChange={(event) => setCutoffInput(event.target.value)} type="time" /><button disabled={loading || !/^([01]\d|2[0-3]):[0-5]\d$/.test(cutoffInput)} onClick={() => { setCutoff(cutoffInput); void load(cutoffInput) }}>Apply</button></div>
          </section>
          )}

          {error && (
            <section className="error-panel"><AlertCircle size={20} /><div><b>Unable to load Elexon data</b><p>{error}</p><span>Check the backend URL and Elexon API availability. The dashboard does not substitute made-up values when live data fails.</span></div><button onClick={() => void load(cutoff)}><RefreshCw size={14} /> Retry</button></section>
          )}

          {!loading && dashboard && dashboard.periods.length === 0 && (
            <section className="error-panel"><AlertCircle size={20} /><div><b>No matched data returned</b><p>Elexon returned no forecast/actual pairs for this cutoff.</p><span>Check the publication-time filters and source API response before interpreting any metrics.</span></div><button onClick={() => void load(cutoff)}><RefreshCw size={14} /> Retry</button></section>
          )}

          {loading && !dashboard ? (
            <div className="loading-panel"><div className="loading-spinner" /><b>Loading historical records</b><span>Fetching actual wind generation and published forecast versions from Elexon.</span></div>
          ) : dashboard && (
            <>
              {view === 'methodology' ? (
                <>
                  <section className="panel">
                    <div className="day-summary">
                      <div><span>MATCHED HALF-HOURS</span><b>{formatNumber(metrics?.matched_periods)}</b></div>
                      <div><span>EXPECTED PERIODS</span><b>{formatNumber(dashboard.data_quality.expected_periods, 0)}</b></div>
                      <div><span>NOT MATCHED</span><b>{formatNumber(dashboard.data_quality.unmatched_periods, 0)}</b></div>
                      <div><span>SOURCE ROWS (ACTUALS / FORECASTS)</span><b>{formatNumber(dashboard.data_quality.actual_rows_received)} <small>/</small> {formatNumber(dashboard.data_quality.forecast_rows_received)}</b></div>
                    </div>
                    <div className="methodology-grid">
                      <div><span className="method-number">01</span><b>Forecast vintage selection</b><p>{dashboard.methodology.forecast_selection}</p></div>
                      <div><span className="method-number">02</span><b>Error interpretation</b><p>{dashboard.methodology.error_sign}</p></div>
                      <div><span className="method-number">03</span><b>Percentage metric</b><p>{dashboard.methodology.mape}</p></div>
                      <div className="scope-warning"><span className="method-number">04</span><b>Scope limitation</b><p>{dashboard.methodology.scope_limit}</p></div>
                    </div>
                    <div className="table-footnote"><Database size={13} /><span><b>{formatNumber(metrics?.matched_periods)}</b> of <b>{formatNumber(dashboard.data_quality.expected_periods)}</b> half-hours matched for {dashboard.month} · missing forecast or outturn records are not imputed.</span></div>
                  </section>
                  <footer className="page-footer"><span>WIND SIGNAL <i>·</i> ENGINEERING PILOT</span><span>WIND-ONLY SCOPE: NOT A TOTAL PROCUREMENT POSITION <i>·</i> DATA BY ELEXON INSIGHTS (FUELHH, WINDFOR) <i>·</i> TIMES IN EUROPE/LONDON</span></footer>
                </>
              ) : (
                <>
                  <section className="metric-grid">
                <MetricCard label="MEAN ABSOLUTE ERROR" value={formatNumber(metrics?.mae_mw, 1)} unit="MW" detail="Average absolute forecast miss" icon={<Activity size={17} />} />
                <MetricCard label="ROOT MEAN SQUARED ERROR" value={formatNumber(metrics?.rmse_mw, 1)} unit="MW" detail="Penalises larger forecast misses" icon={<Gauge size={17} />} />
                <MetricCard label="FORECAST BIAS" value={metrics?.bias_mw == null ? '—' : `${metrics.bias_mw > 0 ? '+' : ''}${formatNumber(metrics.bias_mw, 1)}`} unit="MW" detail={metrics?.bias_mw == null ? 'Forecast minus actual' : metrics.bias_mw > 0 ? 'Wind was over-forecast on average' : metrics.bias_mw < 0 ? 'Wind was under-forecast on average' : 'No mean directional error'} icon={metrics?.bias_mw != null && metrics.bias_mw < 0 ? <ArrowDownRight size={17} /> : <ArrowUpRight size={17} />} tone={biasTone} />
                <MetricCard label="MATCHED HALF-HOURS" value={formatNumber(metrics?.matched_periods)} unit="/ 1,488" detail={`${formatNumber(metrics?.coverage_pct, 1)}% January period coverage`} icon={<CheckCircle2 size={17} />} />
              </section>

              <section className="chart-grid">
                <article className="panel trend-panel">
                  <div className="panel-heading"><div><div className="panel-kicker">MONTHLY PROFILE</div><h2>Forecast vs actual generation</h2><p>Daily mean wind output · MW</p></div><div className="chart-legend"><span><i className="legend-line forecast" /> Forecast</span><span><i className="legend-line actual" /> Actual</span></div></div>
                  {dashboard.daily.length ? <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={dashboard.daily} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e8edf2" />
                    <XAxis dataKey="date" tickFormatter={(value) => String(value).slice(8)} tickLine={false} axisLine={false} tick={{ fill: '#7d8b9a', fontSize: 12 }} interval={2} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: '#7d8b9a', fontSize: 12 }} tickFormatter={(value) => `${(Number(value) / 1000).toFixed(0)}k`} width={44} />
                    <Tooltip content={<ChartTooltip showDate />} />
                    <Legend verticalAlign="top" align="right" height={0} content={() => null} />
                    <Line type="monotone" dataKey="forecast_mw" name="Forecast" stroke="#7186a5" strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls />
                    <Line type="monotone" dataKey="actual_mw" name="Actual" stroke="#14a68c" strokeWidth={2.2} dot={false} activeDot={{ r: 4 }} connectNulls />
                  </ComposedChart></ResponsiveContainer></div> : <EmptyChart />}
                  <div className="chart-footer"><span><b>{dashboard.daily.length}</b> days with matched data</span><span>Select a day below to inspect half-hourly records</span></div>
                </article>

                <article className="panel error-panel-chart">
                  <div className="panel-heading"><div><div className="panel-kicker">ERROR DISTRIBUTION</div><h2>Daily mean absolute error</h2><p>Lower values indicate closer forecasts</p></div></div>
                  {dashboard.daily.length ? <div className="chart-area error-bars"><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.daily} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e8edf2" />
                    <XAxis dataKey="date" tickFormatter={(value) => String(value).slice(8)} tickLine={false} axisLine={false} tick={{ fill: '#7d8b9a', fontSize: 11.5 }} interval={4} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: '#7d8b9a', fontSize: 11.5 }} width={44} />
                    <Tooltip content={<ChartTooltip showDate />} />
                    <Bar dataKey="mae_mw" name="Mean absolute error" fill="#d9a34c" radius={[3, 3, 0, 0]} maxBarSize={17} />
                  </BarChart></ResponsiveContainer></div> : <EmptyChart />}
                  <div className="small-stat-row"><div><span>MONTHLY MAPE*</span><b>{formatNumber(metrics?.mape_pct, 1)}<small>%</small></b></div><div><span>PERIODS IN MAPE</span><b>{formatNumber(metrics?.mape_periods)}</b></div></div>
                </article>
              </section>

              <section className="panel periods-panel">
                <div className="periods-head"><div><div className="panel-kicker">HALF-HOURLY DETAIL</div><h2>Delivery-period inspection</h2><p>Review selected day’s forecast vintage, actual output and forecast error.</p></div><div className="table-actions"><label className="date-picker-label"><CalendarDays size={15} /><select value={selectedDay} onChange={(event) => setSelectedDay(event.target.value)}>{(dashboard.daily.length ? dashboard.daily.map((day) => day.date) : ['2026-01-01']).map((day) => <option value={day} key={day}>{formatDate(day)}</option>)}</select><ChevronDown size={13} /></label><button className="export-button" onClick={downloadPeriods}><Download size={14} /> Export month CSV</button></div></div>
                <div className="day-summary"><div><span>SELECTED DAY</span><b>{selectedDay ? new Date(`${selectedDay}T12:00:00Z`).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'long', year: 'numeric', timeZone: 'UTC' }) : '—'}</b></div><div><span>MEAN FORECAST</span><b>{formatNumber(selectedDaily?.forecast_mw, 0)} <small>MW</small></b></div><div><span>MEAN ACTUAL</span><b>{formatNumber(selectedDaily?.actual_mw, 0)} <small>MW</small></b></div><div><span>DAILY MAE</span><b>{formatNumber(selectedDaily?.mae_mw, 1)} <small>MW</small></b></div></div>
                <div className="table-scroll"><table><thead><tr><th>DELIVERY TIME (UK)</th><th className="numeric">FORECAST</th><th className="numeric">ACTUAL</th><th className="numeric">ERROR</th><th>PUBLISHED (UK)</th><th className="numeric">LEAD</th></tr></thead><tbody>
                  {selectedPeriods.map((period) => <tr key={period.start_time}><td className="period-time">{formatUKTime(period.start_time)}<span>{period.settlement_period != null ? `SP ${period.settlement_period}` : '30 min'}</span></td><td className="numeric">{formatNumber(period.forecast_mw, 1)}</td><td className="numeric">{formatNumber(period.actual_mw, 1)}</td><td className={`numeric error-value ${period.error_mw > 0 ? 'over' : period.error_mw < 0 ? 'under' : ''}`}>{period.error_mw > 0 ? '+' : ''}{formatNumber(period.error_mw, 1)}</td><td className="published-cell">{formatUKTime(period.publish_time)}</td><td className="numeric lead-cell">{formatNumber(period.forecast_lead_hours, 1)}h</td></tr>)}
                  {selectedPeriods.length === 0 && <tr><td colSpan={6} className="empty-row">No periods have both an actual record and a forecast published before the selected cutoff.</td></tr>}
                </tbody></table></div>
                <div className="table-footnote"><Database size={13} /><span><b>{formatNumber(metrics?.matched_periods)}</b> of <b>{formatNumber(dashboard.data_quality.expected_periods)}</b> half-hours matched for {dashboard.month} · missing forecast or outturn records are not imputed.</span></div>
              </section>

              <footer className="page-footer"><span>WIND SIGNAL <i>·</i> ENGINEERING PILOT</span><span>WIND-ONLY SCOPE: NOT A TOTAL PROCUREMENT POSITION <i>·</i> DATA BY ELEXON INSIGHTS (FUELHH, WINDFOR) <i>·</i> TIMES IN EUROPE/LONDON</span></footer>
                </>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  )
}

function EmptyChart() {
  return <div className="empty-chart"><Database size={20} /><b>No matched records available</b><span>Check source data and forecast cutoff.</span></div>
}
