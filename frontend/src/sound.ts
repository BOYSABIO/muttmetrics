/**
 * Sound effects (0.8.0): a handful of short, quiet tones, made in the browser
 * (no audio files). Rules in docs/architecture/ui-conventions.md ("Sound"):
 * a sound confirms something that just happened, it is never the only signal,
 * and one switch turns all of it off.
 */

const STORAGE_KEY = 'muttmetrics.sound'

type AudioWindow = Window & { webkitAudioContext?: typeof AudioContext }

let ctx: AudioContext | null = null
let enabled = readSetting()

function readSetting(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== 'off'
  } catch {
    return true
  }
}

export function soundEnabled(): boolean {
  return enabled
}

export function setSoundEnabled(on: boolean): void {
  enabled = on
  try {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off')
  } catch {
    /* private mode: the choice lasts until the tab closes */
  }
  if (on) {
    wake()
    play('done')
  }
}

/**
 * Browsers only let a page make sound after a tap. The first tap anywhere
 * starts the audio engine, so a sound that follows a save (which finishes a
 * moment after the tap) is allowed to play.
 */
function wake(): void {
  if (!enabled) return
  try {
    if (ctx === null) {
      const Ctor = window.AudioContext ?? (window as AudioWindow).webkitAudioContext
      if (Ctor === undefined) return
      ctx = new Ctor()
    }
    if (ctx.state === 'suspended') void ctx.resume()
  } catch {
    ctx = null
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('pointerdown', wake, { passive: true })
  window.addEventListener('keydown', wake, { passive: true })
}

type Note = {
  /** Hz */
  freq: number
  /** seconds after the sound starts */
  at: number
  /** seconds */
  length: number
  /** 0–1, before the master volume */
  level?: number
  type?: OscillatorType
  /** Slide to this pitch over the note (a thud falls, a blip rises). */
  to?: number
}

/** Overall volume. Quiet on purpose: these sit under a hair dryer, not over it. */
const MASTER = 0.07

export type SoundName = 'start' | 'stop' | 'saved' | 'done' | 'problem'

const SOUNDS: Record<SoundName, Note[]> = {
  // Timer on: two notes going up.
  start: [
    { freq: 659, at: 0, length: 0.09 },
    { freq: 988, at: 0.08, length: 0.16 },
  ],
  // Timer off: the same two, coming down.
  stop: [
    { freq: 988, at: 0, length: 0.09 },
    { freq: 659, at: 0.08, length: 0.18 },
  ],
  // A visit saved: the stamp lands, then three notes as the take-home counts up.
  saved: [
    { freq: 150, to: 70, at: 0.42, length: 0.12, level: 1.6, type: 'triangle' },
    { freq: 1047, at: 0.66, length: 0.22, level: 0.8 },
    { freq: 1319, at: 0.76, length: 0.22, level: 0.8 },
    { freq: 1568, at: 0.86, length: 0.4, level: 0.8 },
  ],
  // Something small went through (a profile saved).
  done: [{ freq: 1319, at: 0, length: 0.16, level: 0.7 }],
  // Something needs attention: one low, soft note. Not a buzzer.
  problem: [{ freq: 233, to: 196, at: 0, length: 0.2, level: 1.2, type: 'triangle' }],
}

export function play(name: SoundName): void {
  if (!enabled || ctx === null || ctx.state !== 'running') return
  try {
    const now = ctx.currentTime
    for (const note of SOUNDS[name]) {
      const start = now + note.at
      const end = start + note.length
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = note.type ?? 'sine'
      osc.frequency.setValueAtTime(note.freq, start)
      if (note.to !== undefined) osc.frequency.exponentialRampToValueAtTime(note.to, end)
      // A fast, soft attack and a fade to nothing: no clicks.
      const peak = MASTER * (note.level ?? 1)
      gain.gain.setValueAtTime(0.0001, start)
      gain.gain.exponentialRampToValueAtTime(peak, start + 0.012)
      gain.gain.exponentialRampToValueAtTime(0.0001, end)
      osc.connect(gain).connect(ctx.destination)
      osc.start(start)
      osc.stop(end + 0.02)
    }
  } catch {
    /* sound is never worth an error */
  }
}
