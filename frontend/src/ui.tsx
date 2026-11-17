/**
 * Small shared pieces (0.8.0): a toast for status messages, loading
 * skeletons, and the handful of icons the app uses. All presentation; no data.
 */

import { useEffect, useRef, useState } from 'react'
import { DogsWaiting } from './PixelDogs'
import { useSlow } from './motion'
import { play } from './sound'

// ---------------------------------------------------------------------------
// Icons (24 × 24, stroke = currentColor)
// ---------------------------------------------------------------------------

type IconProps = { size?: number }

function Svg({ size = 20, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

export function IconPlus(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5v14M5 12h14" />
    </Svg>
  )
}

export function IconCheck(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </Svg>
  )
}

export function IconAlert(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 8v5M12 16.5v.5" />
      <circle cx="12" cy="12" r="9" />
    </Svg>
  )
}

export function IconClose(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Svg>
  )
}

/** The paw from the app icon, as a filled mark. */
export function PawMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="currentColor" aria-hidden="true">
      <ellipse cx="32" cy="43" rx="14" ry="11.5" />
      <ellipse cx="14" cy="28" rx="6" ry="7.5" transform="rotate(-20 14 28)" />
      <ellipse cx="25" cy="17" rx="6" ry="8" />
      <ellipse cx="39" cy="17" rx="6" ry="8" />
      <ellipse cx="50" cy="28" rx="6" ry="7.5" transform="rotate(20 50 28)" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

type Tone = 'success' | 'busy' | 'info' | 'error'

/** Messages are plain sentences; their first words say what kind they are. */
function toneOf(message: string): Tone {
  const m = message.trim()
  if (/^(saving|uploading|loading|creating|adding|visit saved - uploading)/i.test(m)) return 'busy'
  if (/^(saved|photo updated|added|picked|deleted|next:|ready:|using existing)/i.test(m)) {
    return 'success'
  }
  if (/^(nothing changed|resumed timer for [^—]+$)/i.test(m)) return 'info'
  return 'error'
}

/**
 * How much of the bottom of the page the on-screen keyboard is covering.
 * A fixed element is placed against the whole page, not the part you can
 * see, so without this a message would sit behind the keyboard.
 */
function useKeyboardInset(active: boolean): number {
  const [inset, setInset] = useState(0)
  useEffect(() => {
    const vv = window.visualViewport
    if (!active || vv == null) return
    const measure = (): void => {
      setInset(Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop)))
    }
    measure()
    vv.addEventListener('resize', measure)
    vv.addEventListener('scroll', measure)
    return () => {
      vv.removeEventListener('resize', measure)
      vv.removeEventListener('scroll', measure)
    }
  }, [active])
  return active ? inset : 0
}

type ToastProps = {
  message: string
  /** Called when a passing message has been shown long enough. */
  onClear?: () => void
}

/**
 * One status line floating above the bottom bar, so a message never pushes
 * the page down. Good news leaves by itself; a problem stays until the next
 * action replaces it (or it's dismissed).
 */
export function Toast({ message, onClear }: ToastProps) {
  const tone = message === '' ? 'info' : toneOf(message)
  const passing = tone === 'success' || tone === 'info'

  // The latest onClear, so a parent re-render doesn't restart the timer.
  const clear = useRef(onClear)
  useEffect(() => {
    clear.current = onClear
  }, [onClear])

  useEffect(() => {
    if (message === '' || !passing) return
    const t = window.setTimeout(() => clear.current?.(), tone === 'info' ? 2200 : 3200)
    return () => window.clearTimeout(t)
  }, [message, passing, tone])

  const keyboard = useKeyboardInset(message !== '')

  // A quiet note with the message: one for "that went through", one for
  // "look at this". Messages that are only passing by stay silent.
  useEffect(() => {
    if (message === '') return
    if (tone === 'success') play('done')
    else if (tone === 'error') play('problem')
  }, [message, tone])

  if (message === '') return null
  return (
    <div
      className="toast-layer"
      style={keyboard > 0 ? { transform: `translateY(-${keyboard}px)` } : undefined}
    >
      <p
        key={message}
        className={`toast toast-${tone}`}
        role={tone === 'error' ? 'alert' : 'status'}
      >
        <span className="toast-icon" aria-hidden>
          {tone === 'success' ? (
            <IconCheck size={16} />
          ) : tone === 'busy' ? (
            <span className="toast-spinner" />
          ) : tone === 'error' ? (
            <IconAlert size={16} />
          ) : null}
        </span>
        <span className="toast-text">{message}</span>
        {tone === 'error' && onClear !== undefined && (
          <button type="button" className="toast-close" aria-label="Dismiss" onClick={onClear}>
            <IconClose size={14} />
          </button>
        )}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skeletons
// ---------------------------------------------------------------------------

/** Most loads are over before anyone looks; the dogs only come out for the long ones. */
function SlowDogs({ label }: { label: string }) {
  const slow = useSlow(true, 900)
  return slow ? <DogsWaiting label={label.replace(/…$/, '')} /> : null
}

/**
 * The same scene over the whole screen, for a tap that is taking its time
 * (opening a profile, saving a visit with photos on a slow connection).
 */
export function SlowOverlay({ active, label }: { active: boolean; label: string }) {
  const slow = useSlow(active, 700)
  if (!slow) return null
  return (
    <div className="slow-overlay">
      <div className="slow-overlay-card">
        <DogsWaiting label={label} />
      </div>
    </div>
  )
}

function Bar({ w, h = '0.9rem' }: { w: string; h?: string }) {
  return <span className="skeleton" style={{ width: w, height: h }} />
}

/** The dashboard's shape while its numbers load. */
export function DashboardSkeleton({ label }: { label: string }) {
  return (
    <div className="skeleton-stack" aria-busy="true">
      <span className="visually-hidden">{label}</span>
      <SlowDogs label={label} />
      <div className="skeleton-card skeleton-hero">
        <Bar w="30%" h="0.7rem" />
        <Bar w="55%" h="2.8rem" />
        <Bar w="70%" />
        <Bar w="100%" h="4.2rem" />
      </div>
      <div className="skeleton-card">
        <Bar w="35%" h="0.7rem" />
        <Bar w="100%" h="6.5rem" />
      </div>
      <div className="skeleton-card">
        <Bar w="40%" h="0.7rem" />
        <Bar w="45%" h="1.8rem" />
        <Bar w="100%" />
        <Bar w="90%" />
        <Bar w="95%" />
      </div>
    </div>
  )
}

/** A list of rows (clients, pets to pick) while it loads. */
export function ListSkeleton({ rows = 6, label }: { rows?: number; label: string }) {
  return (
    <div className="skeleton-stack skeleton-list" aria-busy="true">
      <span className="visually-hidden">{label}</span>
      <SlowDogs label={label} />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-row">
          <span className="skeleton skeleton-avatar" />
          <span className="skeleton-row-text">
            <Bar w={`${50 + ((i * 17) % 30)}%`} h="1rem" />
            <Bar w={`${35 + ((i * 11) % 25)}%`} h="0.75rem" />
          </span>
        </div>
      ))}
    </div>
  )
}
