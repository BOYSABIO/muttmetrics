import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { euro } from './money'
import { haptic, reducedMotion, useCountUp } from './motion'
import { PixelDog } from './PixelDogs'
import { play } from './sound'
import { nextMilestone } from './thisWeekModel'
import { PawMark } from './ui'

/** What the week looked like once this visit was in it. */
export type SavedWeek = {
  /** "This week" or "Nov 9–15" when the visit was dated in another week. */
  label: string
  takeHome: number
  grooms: number
  /** All grooms ever logged, for the milestone line; null if unknown. */
  allTimeGrooms: number | null
}

type SaveCelebrationProps = {
  petName: string
  ownerName: string
  /** '' or a note about the photos ("2 photo(s)", "only 1/2 photos uploaded…"). */
  photoNote: string
  serviceName: string | null
  minutes: number
  price: number
  tip: number
  week: SavedWeek | null
}

// Confetti in the brand's colours. Fixed, so it's the same burst every time
// and nothing depends on a random number during render.
const PIECES = Array.from({ length: 24 }, (_, i) => {
  const angle = (i * 137.5 * Math.PI) / 180 // golden angle: an even spread
  const reach = 70 + ((i * 53) % 70)
  return {
    x: Math.round(Math.cos(angle) * reach),
    y: Math.round(Math.sin(angle) * reach * 0.8 - 30),
    spin: ((i * 97) % 540) - 270,
    delay: (i % 6) * 18,
    tone: ['sun', 'pine', 'clay', 'ink'][i % 4],
    shape: i % 3 === 0 ? 'dot' : i % 3 === 1 ? 'bar' : 'chip',
  }
})

/** True once `ms` have passed (straight away under reduced motion). */
function useAfter(ms: number): boolean {
  const [done, setDone] = useState(() => reducedMotion())
  useEffect(() => {
    if (done) return
    const t = window.setTimeout(() => setDone(true), ms)
    return () => window.clearTimeout(t)
  }, [done, ms])
  return done
}

/**
 * The moment after Save: a stamp, what was logged, and the week's take-home
 * going up by what this groom earned. The line with role="status" is the
 * announcement ("Saved <pet> · <owner>"); the rest is the reward.
 */
export function SaveCelebration({
  petName,
  ownerName,
  photoNote,
  serviceName,
  minutes,
  price,
  tip,
  week,
}: SaveCelebrationProps) {
  // Once per save, also in development where effects run twice.
  const announced = useRef(false)
  useEffect(() => {
    if (announced.current) return
    announced.current = true
    haptic([14, 60, 24])
    play('saved')
  }, [])

  const earned = price + tip
  const counting = useAfter(650)
  const before = week === null ? 0 : Math.max(0, week.takeHome - earned)
  const takeHome = useCountUp(
    week === null ? 0 : counting ? week.takeHome : before,
    'saved.takeHome',
    900,
    before,
  )

  const milestone =
    week?.allTimeGrooms == null || week.allTimeGrooms < 1
      ? null
      : nextMilestone(week.allTimeGrooms)
  // nextMilestone(100) is already looking at 250: the count has just landed on one.
  const reached = milestone !== null && milestone.previous === week?.allTimeGrooms

  return (
    <>
      <section className="saved-card">
        <div className="saved-stamp-wrap" aria-hidden="true">
          <div className="saved-burst">
            {PIECES.map((p, i) => (
              <i
                key={i}
                className={`saved-piece saved-piece-${p.tone} saved-piece-${p.shape}`}
                style={
                  {
                    '--x': `${p.x}px`,
                    '--y': `${p.y}px`,
                    '--spin': `${p.spin}deg`,
                    '--delay': `${p.delay}ms`,
                  } as CSSProperties
                }
              />
            ))}
          </div>
          <div className="saved-stamp">
            <svg viewBox="0 0 48 48" width="44" height="44" fill="none">
              <path className="saved-check" d="M11 25.5l9 9L37 15.5" />
            </svg>
          </div>
        </div>

        <p className="saved-line" role="status">
          <span className="visually-hidden">Saved </span>
          <strong className="saved-pet">{petName}</strong>
          <span className="saved-owner">
            <span className="visually-hidden"> · </span>
            {ownerName}
          </span>
          {photoNote !== '' && (
            <span className="saved-note">
              <span className="visually-hidden"> · </span>
              {photoNote}
            </span>
          )}
        </p>

        <dl className="saved-receipt">
          {serviceName !== null && (
            <div>
              <dt>Service</dt>
              <dd>{serviceName}</dd>
            </div>
          )}
          <div>
            <dt>Time</dt>
            <dd>{minutes} min</dd>
          </div>
          <div>
            <dt>Price</dt>
            <dd>{euro(price)}</dd>
          </div>
          {tip > 0 && (
            <>
              <div>
                <dt>Tip</dt>
                <dd>{euro(tip)}</dd>
              </div>
              <div className="saved-receipt-total">
                <dt>Total</dt>
                <dd>{euro(earned)}</dd>
              </div>
            </>
          )}
        </dl>
      </section>

      {week !== null && (
        <section className="saved-week" aria-label={`${week.label}: take-home`}>
          <PawMark className="saved-week-mark" />
          <h2 className="saved-week-label">Take-home · {week.label}</h2>
          <p className="saved-week-row">
            <span className="saved-week-value">{euro(Math.round(takeHome))}</span>
            {earned > 0 && counting && <span className="saved-week-plus">+{euro(earned)}</span>}
          </p>
          <p className="saved-week-sub">
            {week.grooms} {week.grooms === 1 ? 'groom' : 'grooms'} logged
          </p>
          {milestone !== null && week.allTimeGrooms != null && (
            <div className="saved-milestone">
              {/* The dogs sit on the milestone line: one pleased, one on duty. */}
              <span className="saved-dogs" aria-hidden="true">
                <PixelDog who="collie" className="saved-dog-collie" />
                <PixelDog who="guard" wag />
              </span>
              <span className="saved-milestone-track" aria-hidden="true">
                <span
                  className="saved-milestone-fill"
                  style={{ width: `${(reached ? 1 : milestone.progress) * 100}%` }}
                />
              </span>
              <p className="saved-milestone-text">
                {reached ? (
                  <>
                    <strong>{week.allTimeGrooms} grooms logged.</strong> Next stop: {milestone.next}
                  </>
                ) : (
                  <>
                    Groom <strong>#{week.allTimeGrooms}</strong> · {milestone.toGo} to{' '}
                    {milestone.next}
                  </>
                )}
              </p>
            </div>
          )}
        </section>
      )}
    </>
  )
}
