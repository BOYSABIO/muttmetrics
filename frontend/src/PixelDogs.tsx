/**
 * The app's two dogs as pixel art (0.8.0): original drawings, made of squares
 * in code (pixelSprites.ts), so there is no image file and nothing to load.
 *
 * - `collie`: black and white, tongue always out, tail always going. He is
 *   the happy one: he turns up when something went well or when you wait.
 * - `guard`: all black, same look whatever happens. He sits wherever
 *   something is worth guarding (the take-home, a delete button). Only his
 *   tail says what he thinks.
 *
 * Decoration only: always `aria-hidden`, and still under reduced motion.
 */

import {
  COLLIE,
  COLLIE_PANT,
  COLLIE_TAIL_DOWN,
  COLLIE_TAIL_UP,
  COLOURS,
  GUARD,
  GUARD_BLINK,
  GUARD_SIDE_EYE,
  GUARD_TAIL_DOWN,
  GUARD_TAIL_UP,
  SANTA_HAT,
  SANTA_HAT_RISE,
  type Frame,
} from './pixelSprites'

type Run = { x: number; y: number; w: number; fill: string }

/**
 * Squares of the same colour next to each other become one rectangle.
 * `keep` picks which squares are drawn (all of them by default).
 */
function runsOf(
  frame: Frame,
  dx = 0,
  dy = 0,
  keep: (row: number, ch: string) => boolean = () => true,
): Run[] {
  const runs: Run[] = []
  frame.forEach((line, row) => {
    let x = 0
    while (x < line.length) {
      const ch = line[x]
      let end = x + 1
      while (end < line.length && line[end] === ch) end += 1
      if (ch !== '.' && keep(row, ch)) {
        runs.push({ x: x + dx, y: row + dy, w: end - x, fill: COLOURS[ch] })
      }
      x = end
    }
  })
  return runs
}

const COLS = COLLIE[0].length
const ROWS = COLLIE.length
/** How many rows show when a dog looks over an edge: down to the nose. */
const PEEK_ROWS = 10

/** Looking over an edge: the head only. */
const head = (row: number): boolean => row < PEEK_ROWS
/** ...except the collie's tongue, which hangs over the edge. */
const headAndTongue = (row: number, ch: string): boolean =>
  row < PEEK_ROWS || ((ch === 'P' || ch === 'p') && row < 14)

type Part = { name: string; runs: Run[] }

// Same hat on every pose: last in the list, so it sits on top of the head.
const HAT: Part = { name: 'hat', runs: runsOf(SANTA_HAT, 0, -SANTA_HAT_RISE) }
type Pose = 'collie' | 'guard' | 'colliePeek' | 'guardPeek'

// Drawn in order, so a tail comes first and the dog covers where they meet.
// Peeking, the tail sits higher, so it shows beside the head.
const PARTS: Record<Pose, Part[]> = {
  collie: [
    { name: 'tail pd-tail-a', runs: runsOf(COLLIE_TAIL_UP, -3, 11) },
    { name: 'tail pd-tail-b', runs: runsOf(COLLIE_TAIL_DOWN, -3, 11) },
    { name: 'frame pd-rest', runs: runsOf(COLLIE) },
    { name: 'frame pd-pant', runs: runsOf(COLLIE_PANT) },
    HAT,
  ],
  guard: [
    { name: 'tail pd-tail-a', runs: runsOf(GUARD_TAIL_UP, 14, 11) },
    { name: 'tail pd-tail-b', runs: runsOf(GUARD_TAIL_DOWN, 14, 11) },
    { name: 'frame pd-rest', runs: runsOf(GUARD) },
    { name: 'frame pd-blink', runs: runsOf(GUARD_BLINK) },
    { name: 'frame pd-side', runs: runsOf(GUARD_SIDE_EYE) },
    HAT,
  ],
  colliePeek: [
    { name: 'tail pd-tail-a', runs: runsOf(COLLIE_TAIL_UP, -3, 5) },
    { name: 'tail pd-tail-b', runs: runsOf(COLLIE_TAIL_DOWN, -3, 5) },
    { name: 'frame pd-rest', runs: runsOf(COLLIE, 0, 0, headAndTongue) },
    { name: 'frame pd-pant', runs: runsOf(COLLIE_PANT, 0, 0, headAndTongue) },
    HAT,
  ],
  guardPeek: [
    { name: 'tail pd-tail-a', runs: runsOf(GUARD_TAIL_UP, 14, 5) },
    { name: 'tail pd-tail-b', runs: runsOf(GUARD_TAIL_DOWN, 14, 5) },
    { name: 'frame pd-rest', runs: runsOf(GUARD, 0, 0, head) },
    { name: 'frame pd-blink', runs: runsOf(GUARD_BLINK, 0, 0, head) },
    { name: 'frame pd-side', runs: runsOf(GUARD_SIDE_EYE, 0, 0, head) },
    HAT,
  ],
}

type PixelDogProps = {
  who: 'collie' | 'guard'
  /** Screen pixels per square. */
  scale?: number
  /** Looking over an edge: the head, with the tail wagging beside it. */
  peek?: boolean
  /** Wag the guard's tail (the collie's never stops). */
  wag?: boolean
  className?: string
}

export function PixelDog({ who, scale = 3, peek = false, wag = false, className }: PixelDogProps) {
  const rows = peek ? PEEK_ROWS : ROWS
  const pose: Pose = peek ? (who === 'collie' ? 'colliePeek' : 'guardPeek') : who
  const classes = [
    'pixel-dog',
    `pixel-dog-${who}`,
    wag || peek || who === 'collie' ? 'pixel-dog-wag' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <svg
      className={classes}
      width={COLS * scale}
      height={rows * scale}
      viewBox={`0 0 ${COLS} ${rows}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
      focusable="false"
    >
      {PARTS[pose].map((part) => (
        <g key={part.name} className={`pd-${part.name}`}>
          {part.runs.map((r) => (
            <rect key={`${r.x}-${r.y}`} x={r.x} y={r.y} width={r.w} height={1} fill={r.fill} />
          ))}
        </g>
      ))}
    </svg>
  )
}

/**
 * Waiting: both of them looking over the edge at you. The collie pants, his
 * tongue hanging over the line; the guard gives him a look now and then.
 * Both tails are going.
 */
export function DogsWaiting({ label }: { label: string }) {
  return (
    <div className="dogs-waiting">
      <div className="dogs-waiting-stage" aria-hidden="true">
        <PixelDog who="collie" peek scale={4} />
        <PixelDog who="guard" peek scale={4} />
      </div>
      <p className="dogs-waiting-label">
        {label}
        <span className="dogs-waiting-dots" aria-hidden="true">
          <i>.</i>
          <i>.</i>
          <i>.</i>
        </span>
      </p>
    </div>
  )
}
