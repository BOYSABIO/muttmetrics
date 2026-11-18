import type { CSSProperties } from 'react'

// Where each flake falls, how big it is and how long it takes. Fixed, so the
// snow is the same every time and nothing random happens during render.
const FLAKES = Array.from({ length: 14 }, (_, i) => ({
  left: (i * 37 + 11) % 100,
  size: 3 + (i % 3),
  seconds: 9 + ((i * 5) % 8),
  delay: -((i * 13) % 17),
  drift: ((i * 29) % 40) - 20,
}))

/**
 * A little snow over Home and Clients, only while the Christmas switch is on
 * (App decides). Square flakes, like the dogs. Never over New visit: that's
 * where the work happens. Hidden under reduced motion (festive.css).
 */
export function Snowfall() {
  return (
    <div className="snowfall" aria-hidden="true">
      {FLAKES.map((f, i) => (
        <i
          key={i}
          style={
            {
              left: `${f.left}%`,
              width: f.size,
              height: f.size,
              '--fall': `${f.seconds}s`,
              '--delay': `${f.delay}s`,
              '--drift': `${f.drift}px`,
            } as CSSProperties
          }
        />
      ))}
    </div>
  )
}
