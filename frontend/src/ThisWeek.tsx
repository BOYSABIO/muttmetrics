import { useEffect, useState } from 'react'

const DEFAULT_BUFFER_MINUTES = 240

type MetricValue = {
  value: number | null
  reason: string | null
}

type WeekSummary = {
  visit_count: number
  groomed_minutes: number
  revenue_ex_tip: number
  revenue_inc_tip: number
  eur_per_hour_n: number
  eur_per_hour_ex_tip: MetricValue
  eur_per_hour_inc_tip: MetricValue
}

type EurPerHourCell = {
  condition_score: number
  shaved_down: boolean
  n: number
  groomed_minutes: number | null
  hours: number | null
  revenue_ex_tip: number | null
  revenue_inc_tip: number | null
  eur_per_hour_ex_tip: MetricValue
  eur_per_hour_inc_tip: MetricValue
}

type PivotOut = {
  n: number
  pivoted_count: number
  rate: MetricValue
}

type OverrunOut = {
  n: number
  avg_minutes: MetricValue
}

type P90MissOut = {
  n: number
  miss_count: number
  rate: MetricValue
}

type UtilizationDay = {
  visit_date: string
  n: number
  planned_p50: number
  planned_p90: number
  actual_minutes: number
  missing_prediction: number
  over_buffer: boolean
}

type MetricsWeekBlock = {
  week_start: string
  week_end: string
  buffer_minutes: number
  min_n: number
  summary: WeekSummary
  eur_per_hour: EurPerHourCell[]
  pivot: PivotOut
  overrun: OverrunOut
  p90_miss: P90MissOut
  utilization: UtilizationDay[]
}

type MetricsWeekOut = MetricsWeekBlock & {
  previous_week: MetricsWeekBlock | null
}

type ThisWeekProps = {
  onLogVisit: () => void
}

function apiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY,
  }
}

async function readJson(res: Response): Promise<unknown> {
  const text = await res.text()
  let data: unknown = null
  if (text !== '') {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }
  if (!res.ok) {
    const detail =
      typeof data === 'object' && data !== null && 'detail' in data
        ? (data as { detail: unknown }).detail
        : null
    throw new Error(
      typeof detail === 'string'
        ? detail
        : `Request failed (${res.status})`,
    )
  }
  return data
}

function mondayOf(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const day = x.getDay()
  const offset = day === 0 ? -6 : 1 - day
  x.setDate(x.getDate() + offset)
  return x
}

function addDays(d: Date, days: number): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  x.setDate(x.getDate() + days)
  return x
}

function toISODate(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

function parseISODate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function formatShortDate(iso: string): string {
  const d = parseISODate(iso)
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

/**
 * "Oct 12–18", or "Sep 28–Oct 4" across a month. Built by hand (not
 * toLocaleDateString's day/month order) so the label is never longer than
 * 13 characters: the switcher has a fixed width and must not resize.
 */
function formatWeekRange(startIso: string, endIso: string): string {
  const start = parseISODate(startIso)
  const end = parseISODate(endIso)
  const month = (d: Date) =>
    d.toLocaleDateString(undefined, { month: 'short' }).replace(/\.$/, '')
  if (start.getMonth() === end.getMonth()) {
    return `${month(start)} ${start.getDate()}–${end.getDate()}`
  }
  return `${month(start)} ${start.getDate()}–${month(end)} ${end.getDate()}`
}

function Chevron({ dir }: { dir: 'left' | 'right' }) {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden>
      <path
        d={dir === 'left' ? 'M10 3 5 8l5 5' : 'M6 3l5 5-5 5'}
        fill="none"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function formatWeekday(iso: string): string {
  const d = parseISODate(iso)
  return d.toLocaleDateString(undefined, { weekday: 'short' })
}

function formatMoney(n: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(n)
}

function formatMoneyExact(n: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
  }).format(n)
}

function formatHours(minutes: number): string {
  const h = minutes / 60
  return `${h.toFixed(h >= 10 ? 0 : 1)}h`
}

function formatMinutesAsHours(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const h = minutes / 60
  return `${Number(h.toFixed(1))}h`
}

function thinAvgCopy(n: number, minN: number): string {
  if (n === 0) return '—'
  return `${n}/${minN} grooms`
}

function formatPct(
  mv: MetricValue,
  n: number,
  minN: number,
): { main: string; thin: boolean } {
  if (mv.value === null) {
    return { main: thinAvgCopy(n, minN), thin: n > 0 }
  }
  return { main: `${(mv.value * 100).toFixed(0)}%`, thin: false }
}

function formatOverrun(
  mv: MetricValue,
  n: number,
  minN: number,
): { main: string; thin: boolean } {
  if (mv.value === null) {
    return { main: thinAvgCopy(n, minN), thin: n > 0 }
  }
  const sign = mv.value > 0 ? '+' : ''
  return { main: `${sign}${Math.round(mv.value)} min`, thin: false }
}

function formatEurCell(
  mv: MetricValue,
  n: number,
  minN: number,
): { main: string; thin: boolean } {
  if (mv.value === null) {
    return { main: thinAvgCopy(n, minN), thin: n > 0 }
  }
  return { main: formatMoneyExact(mv.value), thin: false }
}

/** Display only — rates come from the API (SQL MIN_N). */
function formatHeadlineEur(
  mv: MetricValue,
  n: number,
  minN: number,
): { text: string; thin: boolean } {
  if (mv.value === null) {
    return { text: thinAvgCopy(n, minN), thin: n > 0 }
  }
  return { text: formatMoneyExact(mv.value), thin: false }
}

function coatCellLabel(score: number, shaved: boolean): string {
  const base =
    score === 0 ? 'Worst' : score === 5 ? 'Best' : `Coat ${score}`
  return shaved ? `${base} · shaved` : base
}

async function fetchMetricsWeek(start: string): Promise<MetricsWeekOut> {
  const params = new URLSearchParams({
    start,
    buffer_minutes: String(DEFAULT_BUFFER_MINUTES),
  })
  const res = await fetch(`/api/metrics/week?${params}`, {
    method: 'GET',
    headers: apiHeaders(),
  })
  return (await readJson(res)) as MetricsWeekOut
}

function TimingRow({
  label,
  value,
  hint,
  thin,
}: {
  label: string
  value: string
  hint: string
  thin?: boolean
}) {
  return (
    <div className="timing-row">
      <span className="timing-label">{label}</span>
      <span className={thin ? 'timing-value thin' : 'timing-value'}>{value}</span>
      <span className="timing-hint">{hint}</span>
    </div>
  )
}

function StatCard({
  title,
  value,
  hint,
  thin,
}: {
  title: string
  value: string
  hint: string
  thin?: boolean
}) {
  return (
    <article className="headline-card">
      <h2 className="tw-label">{title}</h2>
      <p className={thin ? 'headline-value headline-value-thin' : 'headline-value'}>
        {value}
      </p>
      <p className="step-meta headline-hint">{hint}</p>
    </article>
  )
}

export function ThisWeek({ onLogVisit }: ThisWeekProps) {
  const [weekStart, setWeekStart] = useState(() =>
    toISODate(mondayOf(new Date())),
  )
  const [data, setData] = useState<MetricsWeekOut | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    void (async () => {
      try {
        const week = await fetchMetricsWeek(weekStart)
        if (!cancelled) {
          setData(week)
        }
      } catch (err) {
        console.error(err)
        if (!cancelled) {
          setData(null)
          setError(
            err instanceof TypeError
              ? "Can't reach server — check your connection"
              : err instanceof Error
                ? err.message
                : 'Could not load week metrics',
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [weekStart])

  const thisMonday = toISODate(mondayOf(new Date()))
  const canGoNext = weekStart < thisMonday
  const weeksBack = Math.round(
    (parseISODate(thisMonday).getTime() - parseISODate(weekStart).getTime()) /
      (7 * 24 * 60 * 60 * 1000),
  )
  const pageTitle =
    weeksBack === 0
      ? 'This week'
      : weeksBack === 1
        ? 'Last week'
        : `Week of ${formatShortDate(weekStart)}`
  const rangeLabel = formatWeekRange(
    data?.week_start ?? weekStart,
    data?.week_end ?? toISODate(addDays(parseISODate(weekStart), 6)),
  )

  function goPrev(): void {
    setWeekStart(toISODate(addDays(parseISODate(weekStart), -7)))
  }

  function goNext(): void {
    if (!canGoNext) return
    setWeekStart(toISODate(addDays(parseISODate(weekStart), 7)))
  }

  const summary = data?.summary
  const empty = summary !== undefined && summary.visit_count === 0
  const minN = data?.min_n
  const headlineEur =
    summary !== undefined && minN !== undefined
      ? formatHeadlineEur(
          summary.eur_per_hour_inc_tip,
          summary.eur_per_hour_n,
          minN,
        )
      : null

  const coatCells = data?.eur_per_hour ?? []
  const barMax = Math.max(
    0,
    ...coatCells
      .map((c) => c.eur_per_hour_inc_tip.value)
      .filter((v): v is number => v !== null),
  )

  const dayCapMinutes = data?.buffer_minutes ?? DEFAULT_BUFFER_MINUTES
  const utilMax = Math.max(
    1,
    dayCapMinutes,
    ...(data?.utilization.flatMap((d) => [
      d.planned_p90,
      d.actual_minutes,
    ]) ?? [1]),
  )

  const pivot =
    data && minN !== undefined
      ? formatPct(data.pivot.rate, data.pivot.n, minN)
      : null
  const overrun =
    data && minN !== undefined
      ? formatOverrun(data.overrun.avg_minutes, data.overrun.n, minN)
      : null
  const p90 =
    data && minN !== undefined
      ? formatPct(data.p90_miss.rate, data.p90_miss.n, minN)
      : null

  const coatPanel =
    minN === undefined ? null : (
    <section
      className="panel this-week-panel this-week-coat"
      aria-label="Euro per hour by coat condition"
    >
      <h2 className="tw-label">€ / hour by coat</h2>
      <p className="step-meta">
        0 = worst, 5 = best. Shaved-down jobs are their own rows.
      </p>
      {coatCells.length === 0 ? (
        <p className="step-meta this-week-soft-empty">
          No coat scores yet — add condition when you save a visit.
        </p>
      ) : (
        <ul className="eur-bar-list">
          {coatCells
            .slice()
            .sort(
              (a, b) =>
                a.condition_score - b.condition_score ||
                Number(a.shaved_down) - Number(b.shaved_down),
            )
            .map((cell) => {
              const shown = formatEurCell(
                cell.eur_per_hour_inc_tip,
                cell.n,
                minN,
              )
              const v = cell.eur_per_hour_inc_tip.value
              const widthPct =
                v !== null && barMax > 0 ? (v / barMax) * 100 : 0
              const label = coatCellLabel(
                cell.condition_score,
                cell.shaved_down,
              )
              return (
                <li key={`${cell.condition_score}-${cell.shaved_down}`}>
                  <div className="eur-bar-row">
                    <span className="eur-bar-label">{label}</span>
                    <div
                      className={
                        v === null
                          ? 'eur-bar-track eur-bar-track-thin'
                          : 'eur-bar-track'
                      }
                      aria-hidden
                    >
                      {v !== null ? (
                        <div
                          className="eur-bar-fill"
                          style={{ width: `${widthPct}%` }}
                        />
                      ) : null}
                    </div>
                    <div className="eur-bar-value">
                      <span
                        className={
                          shown.thin ? 'eur-bar-main thin' : 'eur-bar-main'
                        }
                      >
                        {shown.thin ? 'Not yet' : shown.main}
                      </span>
                      <span className="eur-bar-n">
                        {shown.thin
                          ? `${cell.n}/${minN} grooms`
                          : `${cell.n} ${cell.n === 1 ? 'groom' : 'grooms'}`}
                      </span>
                    </div>
                  </div>
                </li>
              )
            })}
        </ul>
      )}
    </section>
    )

  const timingPanel =
    minN === undefined ? null : (
    <section
      className="panel this-week-panel this-week-timing"
      aria-label="Timing checks"
    >
      <h2 className="tw-label">Timing</h2>
      <p className="step-meta">Did jobs stay on plan, or run long?</p>
      <div className="timing-list">
        <TimingRow
          label="Plan changes"
          value={pivot?.main ?? '—'}
          hint={
            pivot?.thin
              ? `Need ${minN} for a rate`
              : data
                ? `${data.pivot.pivoted_count} of ${data.pivot.n} switched plan`
                : ''
          }
          thin={pivot?.thin}
        />
        <TimingRow
          label="Ran long"
          value={overrun?.main ?? '—'}
          hint={
            overrun?.thin
              ? `Need ${minN} for an average`
              : data
                ? `vs typical estimate · ${data.overrun.n} grooms`
                : ''
          }
          thin={overrun?.thin}
        />
        <TimingRow
          label="Past worst case"
          value={p90?.main ?? '—'}
          hint={
            p90?.thin
              ? `Need ${minN} for a rate`
              : data
                ? `${data.p90_miss.miss_count} of ${data.p90_miss.n} grooms`
                : ''
          }
          thin={p90?.thin}
        />
      </div>
    </section>
    )

  return (
    <div className="this-week">
      <header className="app-header this-week-header">
        <div className="this-week-title-row">
          <h1>{pageTitle}</h1>
          <div className="week-nav" role="group" aria-label="Week">
            {weeksBack > 0 && (
              <button
                type="button"
                className="week-nav-today"
                onClick={() => setWeekStart(thisMonday)}
              >
                This week
              </button>
            )}
            <div className="week-nav-pill">
              <button
                type="button"
                className="week-nav-btn"
                aria-label="Previous week"
                onClick={goPrev}
              >
                <Chevron dir="left" />
              </button>
              <p className="week-nav-range" aria-live="polite">
                {rangeLabel}
              </p>
              <button
                type="button"
                className="week-nav-btn"
                aria-label="Next week"
                disabled={!canGoNext}
                onClick={goNext}
              >
                <Chevron dir="right" />
              </button>
            </div>
          </div>
        </div>
        <p className="step-meta">
          Monday–Sunday
          {minN !== undefined
            ? `. Averages unlock at ${minN} grooms.`
            : '.'}
        </p>
      </header>

      {error !== '' && (
        <p className="status" role="alert">
          {error}
        </p>
      )}

      {loading && data === null && (
        <p className="step-meta">Loading week…</p>
      )}

      {!loading && empty && (
        <section className="panel this-week-empty" aria-label="Empty week">
          <p className="this-week-empty-title">No grooms logged this week</p>
          <p className="step-meta">
            Log a visit and this screen fills in.
          </p>
          <button type="button" className="primary" onClick={onLogVisit}>
            Log a visit
          </button>
        </section>
      )}

      {data !== null && !empty && summary !== undefined && (
        <div className="this-week-body" key={data.week_start}>
          <section className="this-week-headlines" aria-label="Week headlines">
            <StatCard
              title="Grooms"
              value={String(summary.visit_count)}
              hint="completed"
            />
            <StatCard
              title="Time"
              value={formatHours(summary.groomed_minutes)}
              hint={`${summary.groomed_minutes} min`}
            />
            <StatCard
              title="Take-home"
              value={formatMoney(summary.revenue_inc_tip)}
              hint={`${formatMoney(summary.revenue_ex_tip)} + tips`}
            />
            <StatCard
              title="€ / hour"
              value={headlineEur?.text ?? '—'}
              hint={
                headlineEur?.thin
                  ? `Need ${minN} for an average`
                  : 'incl. tips'
              }
              thin={headlineEur?.thin}
            />
          </section>

          <div className="this-week-mid">
            {coatPanel}
            {timingPanel}
          </div>

          <section
            className="panel this-week-panel"
            aria-label="Day load"
          >
            <h2 className="tw-label">Day load</h2>
            <p className="step-meta">
              Does the day fit before closing? Cap:{' '}
              {formatMinutesAsHours(dayCapMinutes)}.
            </p>
            <div className="util-legend" aria-hidden>
              <span className="util-legend-item">
                <span className="util-swatch util-swatch-p90" /> If every dog runs long
              </span>
              <span className="util-legend-item">
                <span className="util-swatch util-swatch-actual" /> Actual time
              </span>
              <span className="util-legend-item">
                <span className="util-swatch util-swatch-cap" /> Day cap
              </span>
            </div>
            {data.utilization.length === 0 ? (
              <p className="step-meta">No days with visits.</p>
            ) : (
              <ul className="util-list">
                {data.utilization.map((day) => {
                  const p90Pct = Math.min(
                    100,
                    (day.planned_p90 / utilMax) * 100,
                  )
                  const actPct = Math.min(
                    100,
                    (day.actual_minutes / utilMax) * 100,
                  )
                  const bufPct = Math.min(
                    100,
                    (dayCapMinutes / utilMax) * 100,
                  )
                  return (
                    <li key={day.visit_date}>
                      <div className="util-row-head">
                        <span className="util-date">
                          {formatWeekday(day.visit_date)}{' '}
                          {formatShortDate(day.visit_date)}
                        </span>
                        <span
                          className={
                            day.over_buffer
                              ? 'util-badge util-badge-warn'
                              : 'util-badge'
                          }
                        >
                          {day.over_buffer ? 'Over capacity' : 'Fits'}
                          {' · '}
                          {day.n} {day.n === 1 ? 'groom' : 'grooms'}
                        </span>
                      </div>
                      <div className="util-bars" aria-hidden>
                        <div
                          className="util-buffer-mark"
                          style={{ left: `${bufPct}%` }}
                        />
                        <div
                          className="util-bar util-bar-p90"
                          style={{ width: `${p90Pct}%` }}
                        />
                        <div
                          className="util-bar util-bar-actual"
                          style={{ width: `${actPct}%` }}
                        />
                      </div>
                      <p className="step-meta util-nums">
                        If long {formatMinutesAsHours(day.planned_p90)}
                        {' · '}
                        Actual {formatMinutesAsHours(day.actual_minutes)}
                        {day.missing_prediction > 0
                          ? ` · ${day.missing_prediction} without estimate`
                          : ''}
                      </p>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
