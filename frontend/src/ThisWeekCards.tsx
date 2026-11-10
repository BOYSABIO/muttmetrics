/**
 * The cards of the This week screen (0.6.5). Each one gets numbers the API
 * already decided (MIN_N in SQL) and only lays them out.
 */

import type { CSSProperties } from 'react'
import type { AllTimeOut, MetricsPeriodBlock, PeriodSummary } from './api'
import { formatShortDate } from './dates'
import {
  type Delta,
  type StripColumn,
  coatInsight,
  coatLabel,
  comparisonLabel,
  formatCap,
  formatHours,
  formatMoney,
  nextMilestone,
  rateText,
  sortCoatCells,
  summaryDeltas,
} from './thisWeekModel'

function DeltaTag({ delta, label }: { delta: Delta; label?: string }) {
  const arrow = delta.dir === 'up' ? '↑' : delta.dir === 'down' ? '↓' : '→'
  return (
    <span className={`tw-delta tw-delta-${delta.dir}`}>
      <span aria-hidden>{arrow}</span> {delta.text}
      {label ? <span className="tw-delta-label"> {label}</span> : null}
    </span>
  )
}

function MiniStat({
  title,
  value,
  delta,
  thin,
}: {
  title: string
  value: string
  delta: Delta | null
  thin?: boolean
}) {
  return (
    <article className="tw-stat">
      <h3 className="tw-stat-title">{title}</h3>
      <p className={thin ? 'tw-stat-value tw-stat-value-thin' : 'tw-stat-value'}>{value}</p>
      {delta ? <DeltaTag delta={delta} /> : <span className="tw-delta tw-delta-none">&nbsp;</span>}
    </article>
  )
}

// ---------------------------------------------------------------------------

export function HeroCard({
  mode,
  summary,
  previous,
  partial,
  minN,
  sinceDate,
  milestone,
}: {
  mode: 'week' | 'month' | 'all'
  summary: PeriodSummary
  previous: PeriodSummary | null
  /** The previous period is clipped to the same elapsed days. */
  partial: boolean
  minN: number
  /** First visit date — all-time mode only. */
  sinceDate?: string
  /** Progress toward the next groom milestone — all-time mode only. */
  milestone?: { toGo: number; next: number; progress: number }
}) {
  const deltas = mode === 'all' ? null : summaryDeltas(summary, previous)
  const tips = summary.revenue_inc_tip - summary.revenue_ex_tip
  const rate = rateText(summary.eur_per_hour_inc_tip)
  const aria =
    mode === 'week' ? 'Week headlines' : mode === 'month' ? 'Month headlines' : 'All-time headlines'
  return (
    <section className="tw-card tw-hero" aria-label={aria}>
      <h2 className="tw-label">Take-home</h2>
      <p className="tw-hero-value">{formatMoney(summary.revenue_inc_tip)}</p>
      <p className="tw-hero-sub">
        {mode === 'all' && sinceDate ? (
          <>since {formatShortDate(sinceDate)}</>
        ) : tips > 0 ? (
          `${formatMoney(summary.revenue_ex_tip)} + ${formatMoney(tips)} tips`
        ) : (
          'incl. tips'
        )}
        {mode !== 'all' && deltas ? (
          <>
            {' · '}
            <DeltaTag delta={deltas.takeHome} label={comparisonLabel(mode, partial)} />
          </>
        ) : mode !== 'all' && previous ? (
          <span className="tw-delta-label">
            {' · '}none last {mode}
            {partial ? ' by now' : ''}
          </span>
        ) : null}
      </p>
      <div className="tw-hero-stats">
        <MiniStat title="Grooms" value={String(summary.visit_count)} delta={deltas?.grooms ?? null} />
        <MiniStat title="Hours" value={formatHours(summary.groomed_minutes)} delta={deltas?.hours ?? null} />
        <MiniStat
          title="€ / hour"
          value={rate ?? `${summary.eur_per_hour_n}/${minN}`}
          delta={deltas?.eurPerHour ?? null}
          thin={rate === null}
        />
      </div>
      {milestone ? (
        <div className="tw-milestone tw-hero-milestone">
          <div className="tw-milestone-track" aria-hidden>
            <span className="tw-milestone-fill" style={{ width: `${milestone.progress * 100}%` }} />
          </div>
          <p className="tw-milestone-text">
            <strong>{milestone.toGo}</strong> more {milestone.toGo === 1 ? 'groom' : 'grooms'} to{' '}
            <strong>{milestone.next}</strong>
          </p>
        </div>
      ) : null}
    </section>
  )
}

// ---------------------------------------------------------------------------

export function DayStrip({
  mode,
  columns,
  capMinutes,
}: {
  mode: 'week' | 'month'
  columns: StripColumn[]
  capMinutes: number
}) {
  // Week bars are scaled so the cap line sits at 80% height; a long day pokes above it.
  const capRef = mode === 'week' ? capMinutes : 0
  const max = Math.max(1, capRef * 1.25, ...columns.map((c) => c.minutes))
  const capPct = (capMinutes / max) * 100
  const overTotal = columns.reduce((s, c) => s + c.overDays, 0)
  return (
    <section className="tw-card" aria-label={mode === 'week' ? 'Day by day' : 'Week by week'}>
      <div className="tw-card-head">
        <h2 className="tw-label">{mode === 'week' ? 'Day by day' : 'Week by week'}</h2>
        <span className="tw-card-note">
          {overTotal > 0
            ? `${overTotal} ${overTotal === 1 ? 'day' : 'days'} over ${formatCap(capMinutes)}`
            : `Cap ${formatCap(capMinutes)} a day`}
        </span>
      </div>
      <ol
        className={`tw-strip tw-strip-${mode}`}
        style={{ '--cap': `${capPct}%` } as CSSProperties}
      >
        {columns.map((c) => {
          const pct = c.minutes > 0 ? Math.max(4, (c.minutes / max) * 100) : 0
          const cls = [
            'tw-strip-col',
            c.isToday ? 'is-today' : '',
            c.isFuture ? 'is-future' : '',
            c.overDays > 0 ? 'is-over' : '',
          ]
            .filter(Boolean)
            .join(' ')
          return (
            <li key={c.key} className={cls}>
              <span className="tw-strip-amount">{c.minutes > 0 ? formatHours(c.minutes) : ''}</span>
              <span className="tw-strip-track">
                {pct > 0 && <span className="tw-strip-bar" style={{ height: `${pct}%` }} />}
              </span>
              <span className="tw-strip-label">{c.label}</span>
              <span className="tw-strip-n">
                {c.grooms > 0 ? `${c.grooms} ${c.grooms === 1 ? 'dog' : 'dogs'}` : '·'}
              </span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

// ---------------------------------------------------------------------------

export function RecentCard({ recent, days }: { recent: MetricsPeriodBlock; days: number }) {
  const minN = recent.min_n
  const cells = sortCoatCells(recent.eur_per_hour)
  const ready = cells.filter((c) => c.eur_per_hour_inc_tip.value !== null)
  const filling = cells.filter((c) => c.eur_per_hour_inc_tip.value === null)
  const max = Math.max(1, ...ready.map((c) => c.eur_per_hour_inc_tip.value as number))
  const rate = rateText(recent.summary.eur_per_hour_inc_tip)
  return (
    <section className="tw-card" aria-label={`Last ${days} days`}>
      <div className="tw-card-head">
        <h2 className="tw-label">Last {days} days</h2>
        <span className="tw-card-note">
          {formatShortDate(recent.start)} – {formatShortDate(recent.end)}
        </span>
      </div>
      <p className="tw-recent-rate">
        <span className="tw-big">{rate ?? '—'}</span>
        <span className="tw-recent-unit">
          {rate ? ' an hour' : ` needs ${minN} grooms`} · {recent.summary.visit_count}{' '}
          {recent.summary.visit_count === 1 ? 'groom' : 'grooms'}
        </span>
      </p>
      {cells.length > 0 && (
        <>
          <p className="tw-insight">{coatInsight(cells, minN, days)}</p>
          {ready.length > 0 && (
            <ul className="tw-coat-list" aria-label="Euro per hour by coat">
              {ready.map((c) => {
                const v = c.eur_per_hour_inc_tip.value as number
                return (
                  <li key={`${c.condition_score}-${c.shaved_down}`} className="tw-coat-row">
                    <span className="tw-coat-label">{coatLabel(c.condition_score, c.shaved_down)}</span>
                    <span className="tw-coat-track" aria-hidden>
                      <span className="tw-coat-fill" style={{ width: `${(v / max) * 100}%` }} />
                    </span>
                    <span className="tw-coat-value">
                      {formatMoney(v)}
                      <span className="tw-coat-n"> · {c.n}</span>
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
          {filling.length > 0 && (
            <p className="tw-filling">
              <span className="tw-filling-title">Filling up:</span>{' '}
              {filling.map((c) => (
                <span key={`${c.condition_score}-${c.shaved_down}`} className="tw-chip">
                  {coatLabel(c.condition_score, c.shaved_down)} {c.n}/{minN}
                </span>
              ))}
            </p>
          )}
        </>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------

/** Only rendered once visits carry a time estimate (none do yet). */
export function TimingCard({ recent, days }: { recent: MetricsPeriodBlock; days: number }) {
  const minN = recent.min_n
  const over = recent.overrun.avg_minutes.value
  const miss = recent.p90_miss.rate.value
  return (
    <section className="tw-card" aria-label="Timing">
      <div className="tw-card-head">
        <h2 className="tw-label">Time vs estimate</h2>
        <span className="tw-card-note">last {days} days</span>
      </div>
      <div className="tw-pair">
        <article className="tw-stat">
          <h3 className="tw-stat-title">Ran long</h3>
          <p className={over === null ? 'tw-stat-value tw-stat-value-thin' : 'tw-stat-value'}>
            {over === null
              ? `${recent.overrun.n}/${minN}`
              : `${over > 0 ? '+' : ''}${Math.round(over)} min`}
          </p>
          <span className="tw-delta tw-delta-none">on average</span>
        </article>
        <article className="tw-stat">
          <h3 className="tw-stat-title">Past worst case</h3>
          <p className={miss === null ? 'tw-stat-value tw-stat-value-thin' : 'tw-stat-value'}>
            {miss === null ? `${recent.p90_miss.n}/${minN}` : `${Math.round(miss * 100)}%`}
          </p>
          <span className="tw-delta tw-delta-none">
            {recent.p90_miss.miss_count} of {recent.p90_miss.n} grooms
          </span>
        </article>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------

export function AllTimeCard({ allTime }: { allTime: AllTimeOut }) {
  const s = allTime.summary
  const m = nextMilestone(s.visit_count)
  return (
    <section className="tw-card tw-alltime" aria-label="Since day one">
      <div className="tw-card-head">
        <h2 className="tw-label">Since day one</h2>
        <span className="tw-card-note">since {formatShortDate(allTime.first_visit_date)}</span>
      </div>
      <div className="tw-trio">
        <article className="tw-stat">
          <h3 className="tw-stat-title">Grooms</h3>
          <p className="tw-stat-value">{s.visit_count}</p>
        </article>
        <article className="tw-stat">
          <h3 className="tw-stat-title">Hours</h3>
          <p className="tw-stat-value">{formatHours(s.groomed_minutes)}</p>
        </article>
        <article className="tw-stat">
          <h3 className="tw-stat-title">Take-home</h3>
          <p className="tw-stat-value">{formatMoney(s.revenue_inc_tip)}</p>
        </article>
      </div>
      <div className="tw-milestone">
        <div className="tw-milestone-track" aria-hidden>
          <span className="tw-milestone-fill" style={{ width: `${m.progress * 100}%` }} />
        </div>
        <p className="tw-milestone-text">
          <strong>{m.toGo}</strong> more {m.toGo === 1 ? 'groom' : 'grooms'} to{' '}
          <strong>{m.next}</strong>
        </p>
      </div>
    </section>
  )
}
