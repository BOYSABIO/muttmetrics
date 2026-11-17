/**
 * Motion helpers (0.8.0). The rules are in docs/architecture/ui-conventions.md
 * ("Motion"): motion explains what just happened, it never makes anyone wait,
 * and everything here does nothing when the device asks for reduced motion.
 */

import { useEffect, useMemo, useState } from 'react'
import { flushSync } from 'react-dom'

export function reducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

// ---------------------------------------------------------------------------
// Screen transitions
// ---------------------------------------------------------------------------

/**
 * How the next screen arrives. `forward` / `back` slide sideways (deeper into
 * a client, the next wizard step), `up` / `down` are the capture sheet opening
 * and closing, `fade` is a change in place.
 */
export type TransitionKind = 'fade' | 'forward' | 'back' | 'up' | 'down'

type ViewTransitionDocument = Document & {
  startViewTransition?: (update: () => void) => {
    finished: Promise<void>
    ready: Promise<void>
  }
}

/**
 * Run a state change as a view transition where the browser supports it
 * (the old and new screens are animated between by the browser, so there is
 * nothing to keep in sync). Elsewhere, and under reduced motion, the change
 * just happens.
 */
export function withTransition(update: () => void, kind: TransitionKind = 'fade'): void {
  const doc = document as ViewTransitionDocument
  if (typeof doc.startViewTransition !== 'function' || reducedMotion()) {
    update()
    return
  }
  const root = document.documentElement
  root.dataset.vt = kind
  try {
    const transition = doc.startViewTransition(() => {
      flushSync(update)
    })
    // A transition that gets skipped (a second one started, the tab was
    // hidden) rejects `ready`; the state change itself still happened.
    transition.ready.catch(() => undefined)
    transition.finished
      .catch(() => undefined)
      .finally(() => {
        if (root.dataset.vt === kind) delete root.dataset.vt
      })
  } catch {
    delete root.dataset.vt
    update()
  }
}

// ---------------------------------------------------------------------------
// Numbers that count to their value
// ---------------------------------------------------------------------------

// Where each number was last, so a change of week morphs from the old value
// instead of restarting at zero.
const lastShown = new Map<string, number>()

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

/**
 * The number to draw right now, easing toward `target`. `id` names the
 * number across re-mounts ("hero.takeHome"). `from` fixes where it starts
 * (the "before" of a before / after); without it the number starts where it
 * was last drawn. Under reduced motion it is simply `target`.
 */
export function useCountUp(target: number, id: string, durationMs = 650, from?: number): number {
  // Where this run starts, read once per target.
  const start = useMemo(() => from ?? lastShown.get(id) ?? 0, [target, id]) // eslint-disable-line react-hooks/exhaustive-deps
  const [frame, setFrame] = useState<{ to: number; value: number } | null>(null)

  useEffect(() => {
    lastShown.set(id, target)
    if (reducedMotion() || start === target) return
    const t0 = performance.now()
    let raf = requestAnimationFrame(function step(now: number) {
      const t = Math.min(1, (now - t0) / durationMs)
      setFrame({ to: target, value: start + (target - start) * easeOutCubic(t) })
      if (t < 1) raf = requestAnimationFrame(step)
    })
    return () => cancelAnimationFrame(raf)
  }, [target, id, durationMs, start])

  if (reducedMotion() || start === target) return target
  // Until the first frame of this run arrives, hold the starting value.
  return frame !== null && frame.to === target ? frame.value : start
}

/** Forget remembered numbers (tests, and leaving a screen for good). */
export function resetCountUp(prefix = ''): void {
  for (const key of [...lastShown.keys()]) {
    if (key.startsWith(prefix)) lastShown.delete(key)
  }
}

// ---------------------------------------------------------------------------
// Waits
// ---------------------------------------------------------------------------

/** True once `active` has lasted `ms`: the moment a wait starts to feel long. */
export function useSlow(active: boolean, ms: number): boolean {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (!active) return
    const t = window.setTimeout(() => setSlow(true), ms)
    return () => {
      window.clearTimeout(t)
      setSlow(false)
    }
  }, [active, ms])
  return active && slow
}

// ---------------------------------------------------------------------------
// Touch feedback
// ---------------------------------------------------------------------------

/** A short buzz on phones that support it (Android). Silent everywhere else. */
export function haptic(pattern: number | number[] = 10): void {
  if (reducedMotion()) return
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      navigator.vibrate(pattern)
    }
  } catch {
    // not allowed in this context: fine
  }
}
