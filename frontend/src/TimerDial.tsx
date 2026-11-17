import type { TimerStatus } from './draft'

type TimerDialProps = {
  status: TimerStatus
  elapsedMs: number
  /** When the timer was started (ms since epoch), for "Started 14:32". */
  startedAt: number | null
}

const TICKS = Array.from({ length: 60 }, (_, i) => i)

function clockText(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function startedText(startedAt: number): string {
  return new Date(startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/**
 * The groom timer as a stopwatch face: sixty ticks that light up through each
 * minute, a hand that goes round once a minute, and the time in the middle.
 * Drawing only: starting and stopping stay with the buttons under it.
 */
export function TimerDial({ status, elapsedMs, startedAt }: TimerDialProps) {
  const seconds = Math.floor(elapsedMs / 1000) % 60
  // Not wrapped at 360, so the hand never has to travel backwards at :00.
  const handDeg = (elapsedMs / 60000) * 360
  const minutes = Math.floor(elapsedMs / 60000)
  const text = clockText(elapsedMs)

  return (
    <div className={`timer-dial timer-dial-${status}`}>
      <svg className="timer-dial-face" viewBox="0 0 240 240" aria-hidden="true" focusable="false">
        <circle className="timer-dial-rim" cx="120" cy="120" r="88" />
        {TICKS.map((i) => {
          const major = i % 5 === 0
          const lit = status === 'stopped' || (status === 'running' && i < seconds)
          return (
            <line
              key={i}
              className={`timer-dial-tick${major ? ' is-major' : ''}${lit ? ' is-lit' : ''}`}
              x1="120"
              y1={major ? 12 : 14}
              x2="120"
              y2={major ? 26 : 22}
              transform={`rotate(${i * 6} 120 120)`}
            />
          )
        })}
        {status !== 'stopped' && (
          <g className="timer-dial-hand" style={{ transform: `rotate(${handDeg}deg)` }}>
            <circle cx="120" cy="18" r="7" />
          </g>
        )}
      </svg>
      <div className="timer-dial-center">
        <p className="timer-state">
          {status === 'idle' && 'Not started'}
          {status === 'running' && 'Timing'}
          {status === 'stopped' && 'Stopped'}
        </p>
        <p className={`timer-clock${text.length > 5 ? ' timer-clock-long' : ''}`}>{text}</p>
        <p className="timer-sub">
          {status === 'idle' && 'min : sec'}
          {status === 'running' && startedAt !== null && `Started ${startedText(startedAt)}`}
          {status === 'stopped' && (minutes < 1 ? 'Under a minute' : `${minutes} min`)}
        </p>
      </div>
    </div>
  )
}
