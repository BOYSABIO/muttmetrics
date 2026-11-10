import { useEffect, useState } from 'react'
import { errorMessage, fetchMetricsPeriod, type MetricsPeriodOut } from './api'
import {
  addDays,
  addMonths,
  firstOfMonth,
  formatMonthRange,
  formatMonthTitle,
  formatShortDate,
  formatWeekRange,
  lastOfMonth,
  mondayOf,
  parseISODate,
  toISODate,
  todayISODate,
} from './dates'
import './ThisWeek.css'
import { AllTimeCard, DayStrip, HeroCard, RecentCard, TimingCard } from './ThisWeekCards'
import { monthColumns, nextMilestone, weekColumns } from './thisWeekModel'

const DEFAULT_BUFFER_MINUTES = 240
const MODE_STORAGE_KEY = 'muttmetrics.metricsMode'

type PeriodMode = 'week' | 'month' | 'all'

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

function readStoredMode(): PeriodMode {
  try {
    const raw = localStorage.getItem(MODE_STORAGE_KEY)
    if (raw === 'month' || raw === 'week' || raw === 'all') return raw
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
  // All-time reuses the current week as the API carrier (recent + all_time).
  const thisMonday = toISODate(mondayOf(new Date()))
  const requestKey =
    mode === 'week' ? `week:${weekStart}` : mode === 'month' ? `month:${monthStart}` : 'all'
  const loading = result?.key !== requestKey
  const data = loading ? null : result.data
  const error = loading ? '' : result.error

  useEffect(() => {
    let cancelled = false
    void (async () => {
      let next: LoadResult
      try {
        // One endpoint for both modes (#187): week = Mon…Sun, month = 1st…last.
        // All-time asks for the current week so the payload still includes
        // `recent` and `all_time` without a dedicated range endpoint.
        const fetched =
          mode === 'month'
            ? await fetchMetricsPeriod(
                monthStart,
                toISODate(lastOfMonth(parseISODate(monthStart))),
                DEFAULT_BUFFER_MINUTES,
              )
            : await fetchMetricsPeriod(
                mode === 'all' ? thisMonday : weekStart,
                toISODate(
                  addDays(parseISODate(mode === 'all' ? thisMonday : weekStart), 6),
                ),
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
  }, [mode, weekStart, monthStart, requestKey, thisMonday])

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

  const allTime = data?.all_time ?? null

  const pageTitle =
    mode === 'all'
      ? 'All time'
      : mode === 'week'
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
    mode === 'all'
      ? allTime
        ? `${formatShortDate(allTime.first_visit_date)} – ${formatShortDate(allTime.through)}`
        : 'Since day one'
      : mode === 'week'
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
    } else if (mode === 'month') {
      setMonthStart(toISODate(addMonths(parseISODate(monthStart), -1)))
    }
  }

  function goNext(): void {
    if (mode === 'week') {
      if (!canGoNextWeek) return
      setWeekStart(toISODate(addDays(parseISODate(weekStart), 7)))
    } else if (mode === 'month') {
      if (!canGoNextMonth) return
      setMonthStart(toISODate(addMonths(parseISODate(monthStart), 1)))
    }
  }

  function goCurrent(): void {
    if (mode === 'week') {
      setWeekStart(thisMonday)
    } else if (mode === 'month') {
      setMonthStart(thisMonth)
    }
  }

  function switchMode(next: PeriodMode): void {
    setMode(next)
  }

  const summary = mode === 'all' ? allTime?.summary : data?.summary
  const empty =
    mode === 'all'
      ? allTime === null || (summary !== undefined && summary.visit_count === 0)
      : summary !== undefined && summary.visit_count === 0
  const minN = data?.min_n
  const today = todayISODate()
  const capMinutes = data?.buffer_minutes ?? DEFAULT_BUFFER_MINUTES
  const recent = data?.recent ?? null
  const recentDays = data?.recent_days ?? null
  const hasEstimates =
    recent !== null && (recent.overrun.n > 0 || recent.p90_miss.n > 0)
  const showRecent = recent !== null && recentDays !== null

  const columns =
    data === null || mode === 'all'
      ? []
      : mode === 'week'
        ? weekColumns(data.start, data.utilization, capMinutes, today)
        : monthColumns(
            data.start,
            data.end,
            data.utilization_weeks,
            data.utilization,
            capMinutes,
            today,
          )

  const showJumpCurrent =
    mode === 'week' ? weeksBack > 0 : mode === 'month' ? monthsBack > 0 : false
  const canGoNext = mode === 'week' ? canGoNextWeek : mode === 'month' ? canGoNextMonth : false
  const periodKey =
    mode === 'all'
      ? allTime?.first_visit_date ?? 'all'
      : (data?.start ?? (mode === 'week' ? weekStart : monthStart))

  const showBody = data !== null && minN !== undefined && (mode === 'all' || summary !== undefined)

  return (
    <div className="this-week">
      <header className="app-header this-week-header">
        <div className="this-week-title-row">
          <h1>{pageTitle}</h1>
          <div className="week-nav period-picker" role="group" aria-label="Period">
            <div
              className="period-mode"
              role="group"
              aria-label="Week, month, or all time"
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
              <button
                type="button"
                className={
                  mode === 'all'
                    ? 'period-mode-btn period-mode-btn-active'
                    : 'period-mode-btn'
                }
                aria-pressed={mode === 'all'}
                aria-label="All time"
                onClick={() => switchMode('all')}
              >
                All
              </button>
            </div>
            {mode === 'all' ? (
              <div className="week-nav-pill week-nav-pill-static">
                <p className="week-nav-range" aria-live="polite">
                  {rangeLabel}
                </p>
              </div>
            ) : (
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
            )}
          </div>
        </div>
        {/* The jump-back link lives on this line so showing it never moves
            the controls above. */}
        <div className="this-week-meta-row">
          <p className="step-meta">
            {mode === 'all'
              ? 'Since the first groom'
              : mode === 'week'
                ? 'Monday–Sunday'
                : 'Calendar month'}
            {minN !== undefined ? ` · rates need ${minN} grooms` : ''}
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
          {mode === 'all'
            ? 'Loading all time…'
            : mode === 'week'
              ? 'Loading week…'
              : 'Loading month…'}
        </p>
      )}

      {showBody && (
        <div className="this-week-body" key={periodKey}>
          {empty ? (
            <section className="tw-card this-week-empty" aria-label="Empty period">
              <p className="this-week-empty-title">
                {mode === 'all'
                  ? 'No grooms logged yet'
                  : mode === 'week'
                    ? 'No grooms logged this week'
                    : 'No grooms logged this month'}
              </p>
              <p className="step-meta">Log a visit and this screen fills in.</p>
              <button type="button" className="primary" onClick={onLogVisit}>
                Log a visit
              </button>
            </section>
          ) : summary !== undefined && minN !== undefined ? (
            <>
              <HeroCard
                mode={mode}
                summary={summary}
                previous={mode === 'all' ? null : (data.previous_period?.summary ?? null)}
                partial={mode === 'all' ? false : (data.previous_is_partial ?? false)}
                minN={minN}
                sinceDate={mode === 'all' ? allTime?.first_visit_date : undefined}
                milestone={
                  mode === 'all' && allTime
                    ? nextMilestone(allTime.summary.visit_count)
                    : undefined
                }
              />
              {mode !== 'all' && (
                <DayStrip mode={mode} columns={columns} capMinutes={capMinutes} />
              )}
            </>
          ) : null}
          <div className="tw-grid">
            {showRecent && recent.summary.visit_count > 0 && (
              <RecentCard recent={recent} days={recentDays} />
            )}
            {showRecent && hasEstimates && <TimingCard recent={recent} days={recentDays} />}
            {mode !== 'all' && data.all_time && <AllTimeCard allTime={data.all_time} />}
          </div>
        </div>
      )}
    </div>
  )
}
