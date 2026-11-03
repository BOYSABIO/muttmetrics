import { useEffect, useState } from 'react'
import './App.css'
import { APP_NAME, APP_VERSION, BUSINESS_NAME } from './brand'
import { Capture } from './Capture'
import { Directory } from './Directory'
import { loadDraft, type DraftVisit, type SelectedPet } from './draft'
import { ThisWeek } from './ThisWeek'

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

  // Home toast (e.g. "Saved …") used to stick forever after a visit save.
  useEffect(() => {
    if (screen !== 'home' || message === '') {
      return
    }
    const t = window.setTimeout(() => {
      setMessage('')
    }, 4000)
    return () => window.clearTimeout(t)
  }, [screen, message])

  function openCapture(): void {
    setStartPet(null)
    setMessage('')
    setScreen('capture')
  }

  function startVisitForPet(dog: SelectedPet): void {
    setStartPet(dog)
    setMessage('')
    setScreen('capture')
  }

  function leaveCapture(doneMessage: string): void {
    setResume(null)
    setStartPet(null)
    setMessage(doneMessage)
    setScreen('home')
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
                onClick={() => {
                  setArea('this_week')
                  setMessage('')
                }}
                aria-current={area === 'this_week' ? 'page' : undefined}
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
              <nav className="home-links" aria-label="Main">
                <button
                  type="button"
                  className="home-link"
                  aria-current={area === 'directory' ? 'page' : undefined}
                  onClick={() => {
                    setArea('directory')
                    setMessage('')
                  }}
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
            {message !== '' && (
              <p className="status" role="status">
                {message}
              </p>
            )}
            {area === 'this_week' && <ThisWeek onLogVisit={openCapture} />}
            {area === 'directory' && (
              <Directory onStartVisit={startVisitForPet} />
            )}
            <p className="app-version" aria-label={`App version ${APP_VERSION}`}>
              v{APP_VERSION}
            </p>
          </div>
          <button
            type="button"
            className="fab"
            aria-label="New visit"
            onClick={openCapture}
          >
            <span className="fab-plus" aria-hidden>
              +
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
