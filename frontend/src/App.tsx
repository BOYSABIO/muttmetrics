import { useEffect, useState } from 'react'
import './App.css'
import { APP_NAME, APP_VERSION, BUSINESS_NAME } from './brand'
import { Capture } from './Capture'
import { Directory } from './Directory'
import { loadDraft, type DraftVisit, type SelectedPet } from './draft'
import { withTransition } from './motion'
import { ThisWeek } from './ThisWeek'
import { Snowfall } from './Festive'
import { festiveEnabled, setFestiveEnabled } from './festive'
import { setSoundEnabled, soundEnabled } from './sound'
import { IconPlus, Toast } from './ui'

type Screen = 'home' | 'capture'
/** Home shell destinations. Capture is an action (+), not a peer tab. */
type Area = 'this_week' | 'directory'

/** The shell: home (dashboard / clients) or the capture flow. */
function App() {
  // Read a saved draft once, before the first render, and resume straight
  // into capture. (Restoring in an effect rendered an empty screen first.)
  const [resume, setResume] = useState<DraftVisit | null>(() => loadDraft())
  const [screen, setScreen] = useState<Screen>(resume === null ? 'home' : 'capture')
  const [area, setArea] = useState<Area>('this_week')
  const [startPet, setStartPet] = useState<SelectedPet | null>(null)
  const [message, setMessage] = useState('')
  const [sound, setSound] = useState(() => soundEnabled())
  const [festive, setFestive] = useState(() => festiveEnabled())

  // The New visit button is a labelled pill at the top of a page and shrinks
  // to a round "+" once you scroll, so it stops covering what you're reading.
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = (): void => setScrolled(window.scrollY > 48)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  function goTo(next: Area): void {
    if (next === area) return
    withTransition(() => {
      setArea(next)
      setMessage('')
    }, next === 'directory' ? 'forward' : 'back')
  }

  function openCapture(): void {
    withTransition(() => {
      setStartPet(null)
      setMessage('')
      setScreen('capture')
    }, 'up')
  }

  function startVisitForPet(dog: SelectedPet): void {
    withTransition(() => {
      setStartPet(dog)
      setMessage('')
      setScreen('capture')
    }, 'up')
  }

  function leaveCapture(doneMessage: string): void {
    withTransition(() => {
      setResume(null)
      setStartPet(null)
      setMessage(doneMessage)
      setScreen('home')
    }, 'down')
  }

  return (
    <main className={`app ${screen === 'home' ? 'app-home' : 'app-capture'}`}>
      {screen === 'home' && (
        <>
          <div className="page page-wide home-shell">
            <header className="app-header app-header-home">
              <button
                type="button"
                className="brand-home"
                onClick={() => goTo('this_week')}
              >
                {BUSINESS_NAME === '' ? (
                  APP_NAME
                ) : (
                  <span className="brand-stack">
                    <span className="brand-name">{BUSINESS_NAME}</span>
                    <span className="brand-sub">{APP_NAME}</span>
                  </span>
                )}
              </button>
              {/* Both main areas are named tabs in the same spot on every screen,
                  so getting back to the numbers never depends on knowing the logo
                  is a button. */}
              <nav className="home-links" aria-label="Main">
                <button
                  type="button"
                  className="home-link"
                  aria-current={area === 'this_week' ? 'page' : undefined}
                  onClick={() => goTo('this_week')}
                >
                  Home
                </button>
                <button
                  type="button"
                  className="home-link"
                  aria-current={area === 'directory' ? 'page' : undefined}
                  onClick={() => goTo('directory')}
                >
                  Clients
                </button>
                <button
                  type="button"
                  className="primary header-new-visit"
                  onClick={openCapture}
                >
                  New visit
                </button>
              </nav>
            </header>
            {festive && <Snowfall />}
            <Toast message={message} onClear={() => setMessage('')} />
            {area === 'this_week' && <ThisWeek onLogVisit={openCapture} />}
            {area === 'directory' && (
              <Directory onStartVisit={startVisitForPet} />
            )}
            <footer className="app-footer">
              <p className="app-version" aria-label={`App version ${APP_VERSION}`}>
                v{APP_VERSION}
              </p>
              <button
                type="button"
                className="linkish sound-toggle"
                aria-pressed={sound}
                onClick={() => {
                  setSoundEnabled(!sound)
                  setSound(!sound)
                }}
              >
                Sound {sound ? 'on' : 'off'}
              </button>
              <button
                type="button"
                className="linkish festive-toggle"
                aria-pressed={festive}
                onClick={() => {
                  setFestiveEnabled(!festive)
                  setFestive(!festive)
                }}
              >
                Christmas {festive ? 'on' : 'off'}
              </button>
            </footer>
          </div>
          <button
            type="button"
            className={scrolled ? 'fab fab-compact' : 'fab'}
            aria-label="New visit"
            onClick={openCapture}
          >
            <span className="fab-plus" aria-hidden>
              <IconPlus size={22} />
            </span>
            <span className="fab-label" aria-hidden>
              New visit
            </span>
          </button>
        </>
      )}

      {screen === 'capture' && (
        <Capture draft={resume} startPet={startPet} onDone={leaveCapture} />
      )}
    </main>
  )
}

export default App
