import { useEffect, useState } from 'react'
import {
  errorMessage,
  fetchMetricsPeriod,
  type MetricValue,
  type MetricsPeriodOut,
} from './api'
import {
  addDays,
  addMonths,
  firstOfMonth,
  formatMonthRange,
  formatMonthTitle,
  formatShortDate,
  formatWeekday,
  formatWeekRange,
  lastOfMonth,
  mondayOf,
  parseISODate,
  toISODate,
} from './dates'

const DEFAULT_BUFFER_MINUTES = 240
const MODE_STORAGE_KEY = 'muttmetrics.metricsMode'

type PeriodMode = 'week' | 'month'

type ThisWeekProps = {
  onLogVisit: () => void
}

/** The answer to one request, tagged with the request it answers. */
type LoadResult = {
  key: string
  data: MetricsPeriodOut | null
  error: string
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

function readStoredMode(): PeriodMode {
  try {
    const raw = localStorage.getItem(MODE_STORAGE_KEY)
    if (raw === 'month' || raw === 'week') return raw
  } catch {
    /* private mode / blocked storage */
  }
  return 'week'
}

function writeStoredMode(mode: PeriodMode): void {
  try {
    localStorage.setItem(MODE_STORAGE_KEY, mode)
  } catch {
    /* ignore */
  }
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
  const [mode, setMode] = useState<PeriodMode>(() => readStoredMode())
  const [weekStart, setWeekStart] = useState(() =>
    toISODate(mondayOf(new Date())),
  )
  const [monthStart, setMonthStart] = useState(() =>
    toISODate(firstOfMonth(new Date())),
  )
  const [result, setResult] = useState<LoadResult | null>(null)

  useEffect(() => {
    writeStoredMode(mode)
  }, [mode])

  // Which period the screen is asking for right now. "Loading" is not stored:
  // it is simply "the last answer we have is for a different request". That
  // way the panels can never show last week's numbers under this week's title.
  const requestKey = mode === 'week' ? `week:${weekStart}` : `month:${monthStart}`
  const loading = result?.key !== requestKey
  const data = loading ? null : result.data
  const error = loading ? '' : result.error

  useEffect(() => {
    let cancelled = false
    void (async () => {
      let next: LoadResult
      try {
        // One endpoint for both modes (#187): week = Mon…Sun, month = 1st…last.
        const fetched =
          mode === 'week'
            ? await fetchMetricsPeriod(
                weekStart,
                toISODate(addDays(parseISODate(weekStart), 6)),
                DEFAULT_BUFFER_MINUTES,
              )
            : await fetchMetricsPeriod(
                monthStart,
                toISODate(lastOfMonth(parseISODate(monthStart))),
                DEFAULT_BUFFER_MINUTES,
              )
        next = { key: requestKey, data: fetched, error: '' }
      } catch (err) {
        console.error(err)
        next = {
          key: requestKey,
          data: null,
          error: errorMessage(err),
        }
      }
      if (!cancelled) {
        setResult(next)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [mode, weekStart, monthStart, requestKey])

  const thisMonday = toISODate(mondayOf(new Date()))
  const thisMonth = toISODate(firstOfMonth(new Date()))

  const canGoNextWeek = weekStart < thisMonday
  const canGoNextMonth = monthStart < thisMonth

  const weeksBack = Math.round(
    (parseISODate(thisMonday).getTime() - parseISODate(weekStart).getTime()) /
      (7 * 24 * 60 * 60 * 1000),
  )
  const monthsBack =
    (parseISODate(thisMonth).getFullYear() -
      parseISODate(monthStart).getFullYear()) *
      12 +
    (parseISODate(thisMonth).getMonth() - parseISODate(monthStart).getMonth())

  const pageTitle =
    mode === 'week'
      ? weeksBack === 0
        ? 'This week'
        : weeksBack === 1
          ? 'Last week'
          : `Week of ${formatShortDate(weekStart)}`
      : monthsBack === 0
        ? 'This month'
        : monthsBack === 1
          ? 'Last month'
          : formatMonthTitle(monthStart)

  const rangeLabel =
    mode === 'week'
      ? formatWeekRange(
          data?.start ?? weekStart,
          data?.end ?? toISODate(addDays(parseISODate(weekStart), 6)),
        )
      : formatMonthRange(
          data?.start ?? monthStart,
          data?.end ?? toISODate(lastOfMonth(parseISODate(monthStart))),
        )

  function goPrev(): void {
    if (mode === 'week') {
      setWeekStart(toISODate(addDays(parseISODate(weekStart), -7)))
    } else {
      setMonthStart(toISODate(addMonths(parseISODate(monthStart), -1)))
    }
  }

  function goNext(): void {
    if (mode === 'week') {
      if (!canGoNextWeek) return
      setWeekStart(toISODate(addDays(parseISODate(weekStart), 7)))
    } else {
      if (!canGoNextMonth) return
      setMonthStart(toISODate(addMonths(parseISODate(monthStart), 1)))
    }
  }

  function goCurrent(): void {
    if (mode === 'week') {
      setWeekStart(thisMonday)
    } else {
      setMonthStart(thisMonth)
    }
  }

  function switchMode(next: PeriodMode): void {
    setMode(next)
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
  // Weekly rows come from the API (#178). The cap is per day, so month mode
  // scales bars to the biggest week and draws no cap line against them.
  const weeks = data?.utilization_weeks ?? []
  const utilMax =
    mode === 'month'
      ? Math.max(1, ...weeks.flatMap((w) => [w.planned_p90, w.actual_minutes]))
      : Math.max(
          1,
          dayCapMinutes,
          ...(data?.utilization.flatMap((d) => [
            d.planned_p90,
            d.actual_minutes,
          ]) ?? [1]),
        )
  const overrun =
    data && minN !== undefined
      ? formatOverrun(data.overrun.avg_minutes, data.overrun.n, minN)
      : null
  const p90 =
    data && minN !== undefined
      ? formatPct(data.p90_miss.rate, data.p90_miss.n, minN)
      : null

  const showJumpCurrent = mode === 'week' ? weeksBack > 0 : monthsBack > 0
  const canGoNext = mode === 'week' ? canGoNextWeek : canGoNextMonth
  const periodKey = data?.start ?? (mode === 'week' ? weekStart : monthStart)

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
        {/* Pivot isn't recorded yet (#178): capture sets booked = actual until
            booking exists (#44), so any rate here would be a made-up 0%. */}
        <TimingRow
          label="Plan changes"
          value="Not captured yet"
          hint="The app doesn't record plan changes yet"
          thin
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
          <div className="week-nav period-picker" role="group" aria-label="Period">
            <div
              className="period-mode"
              role="group"
              aria-label="Week or month"
              data-mode={mode}
            >
              <button
                type="button"
                className={
                  mode === 'week'
                    ? 'period-mode-btn period-mode-btn-active'
                    : 'period-mode-btn'
                }
                aria-pressed={mode === 'week'}
                onClick={() => switchMode('week')}
              >
                Week
              </button>
              <button
                type="button"
                className={
                  mode === 'month'
                    ? 'period-mode-btn period-mode-btn-active'
                    : 'period-mode-btn'
                }
                aria-pressed={mode === 'month'}
                onClick={() => switchMode('month')}
              >
                Month
              </button>
            </div>
            <div className="week-nav-pill">
              <button
                type="button"
                className="week-nav-btn"
                aria-label={mode === 'week' ? 'Previous week' : 'Previous month'}
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
                aria-label={mode === 'week' ? 'Next week' : 'Next month'}
                disabled={!canGoNext}
                onClick={goNext}
              >
                <Chevron dir="right" />
              </button>
            </div>
          </div>
        </div>
        {/* The jump-back link lives on this line so showing it never moves
            the controls above. */}
        <div className="this-week-meta-row">
          <p className="step-meta">
            {mode === 'week' ? 'Monday–Sunday' : 'Calendar month'}
            {minN !== undefined
              ? `. Averages unlock at ${minN} grooms.`
              : '.'}
          </p>
          {showJumpCurrent && (
            <button
              type="button"
              className="week-nav-today"
              onClick={goCurrent}
            >
              {mode === 'week' ? 'Back to this week' : 'Back to this month'}
            </button>
          )}
        </div>
      </header>

      {error !== '' && (
        <p className="status" role="alert">
          {error}
        </p>
      )}

      {loading && (
        <p className="step-meta">
          {mode === 'week' ? 'Loading week…' : 'Loading month…'}
        </p>
      )}

      {!loading && empty && (
        <section className="panel this-week-empty" aria-label="Empty period">
          <p className="this-week-empty-title">
            {mode === 'week'
              ? 'No grooms logged this week'
              : 'No grooms logged this month'}
          </p>
          <p className="step-meta">
            Log a visit and this screen fills in.
          </p>
          <button type="button" className="primary" onClick={onLogVisit}>
            Log a visit
          </button>
        </section>
      )}

      {data !== null && !empty && summary !== undefined && (
        <div className="this-week-body" key={periodKey}>
          <section
            className="this-week-headlines"
            aria-label={mode === 'week' ? 'Week headlines' : 'Month headlines'}
          >
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
            aria-label={mode === 'week' ? 'Day load' : 'Week load'}
          >
            <h2 className="tw-label">
              {mode === 'week' ? 'Day load' : 'Week load'}
            </h2>
            <p className="step-meta">
              {mode === 'week'
                ? `Does the day fit before closing? Cap: ${formatMinutesAsHours(dayCapMinutes)}.`
                : `Totals per week. The ${formatMinutesAsHours(dayCapMinutes)} cap is per day, so each week shows how many days went over.`}
            </p>
            <div className="util-legend" aria-hidden>
              <span className="util-legend-item">
                <span className="util-swatch util-swatch-p90" /> If every dog runs long
              </span>
              <span className="util-legend-item">
                <span className="util-swatch util-swatch-actual" /> Actual time
              </span>
              {mode === 'week' && (
                <span className="util-legend-item">
                  <span className="util-swatch util-swatch-cap" /> Day cap
                </span>
              )}
            </div>
            {mode === 'month' ? (
              weeks.length === 0 ? (
                <p className="step-meta">No days with visits.</p>
              ) : (
                <ul className="util-list">
                  {weeks.map((week) => {
                    const p90Pct = Math.min(
                      100,
                      (week.planned_p90 / utilMax) * 100,
                    )
                    const actPct = Math.min(
                      100,
                      (week.actual_minutes / utilMax) * 100,
                    )
                    const over = week.over_buffer_days
                    return (
                      <li key={week.week_start}>
                        <div className="util-row-head">
                          <span className="util-date">
                            {formatWeekRange(week.range_start, week.range_end)}
                          </span>
                          <span
                            className={
                              over > 0
                                ? 'util-badge util-badge-warn'
                                : 'util-badge'
                            }
                          >
                            {over > 0
                              ? `${over} ${over === 1 ? 'day' : 'days'} over`
                              : 'Days fit'}
                            {' · '}
                            {week.n} {week.n === 1 ? 'groom' : 'grooms'}
                            {' · '}
                            {week.day_count}{' '}
                            {week.day_count === 1 ? 'day' : 'days'}
                          </span>
                        </div>
                        <div className="util-bars" aria-hidden>
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
                          If long {formatMinutesAsHours(week.planned_p90)}
                          {' · '}
                          Actual {formatMinutesAsHours(week.actual_minutes)}
                          {week.missing_prediction > 0
                            ? ` · ${week.missing_prediction} without estimate`
                            : ''}
                        </p>
                      </li>
                    )
                  })}
                </ul>
              )
            ) : data.utilization.length === 0 ? (
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
