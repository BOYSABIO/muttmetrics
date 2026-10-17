import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  createDog,
  createOwner,
  createVisit,
  errorMessage,
  listServices,
  searchDogs,
  uploadVisitPhoto,
  type CreatedOwner,
  type DogSearchItem,
  type ServiceListItem,
} from './api'
import { todayISODate } from './dates'
import { Directory } from './Directory'
import { PhotoPicker } from './PhotoPicker'
import { ThisWeek } from './ThisWeek'
import { APP_NAME, BUSINESS_NAME } from './brand'

type TimerStatus = 'idle' | 'running' | 'stopped'

function formatElapsed(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function floorMinutes(ms: number): number {
  return Math.floor(ms / 60000)
}

type VisitStep = 1 | 2 | 3

type Mode = 'search' | 'new' | 'visit'
type Screen = 'home' | 'capture'
/** Home shell destinations. Capture is an action (+), not a peer tab. */
type Area = 'this_week' | 'directory'

type SelectedDog = {
  dog_id: number
  owner_id: number
  dog_name: string
  owner_name: string
}

const DRAFT_KEY = 'muttmetrics.draftVisit'
const DRAFT_MAX_AGE_MS = 12 * 60 * 60 * 1000 // 12 hours

type DraftVisit = {
  selectedDog: SelectedDog
  visitStep: VisitStep
  timerStatus: TimerStatus
  startedAt: number | null
  actualMinutes: string
  visitDate: string
  conditionScore: string
  surprise: string
  serviceId: string
  finalPrice: string
  tip: string
  quotedPrice: string
  shavedDown: boolean
  hadIntakeFile: boolean
  hadAfterFile: boolean
  savedAt: number
}

function clearDraft(): void {
  localStorage.removeItem(DRAFT_KEY)
}

function saveDraft(draft: Omit<DraftVisit, 'savedAt'>): void {
  const full: DraftVisit = {
    ...draft,
    savedAt: Date.now(),
  }
  localStorage.setItem(DRAFT_KEY, JSON.stringify(full))
}

function loadDraft(): DraftVisit | null {
  const raw = localStorage.getItem(DRAFT_KEY)
  if (raw === null) {
    return null
  }

  let draft: DraftVisit
  try {
    draft = JSON.parse(raw) as DraftVisit
  } catch {
    clearDraft()
    return null
  }

  const now = Date.now()

  // Timer was started a long time ago -> abandon
  if (
    draft.startedAt !== null &&
    now - draft.startedAt > DRAFT_MAX_AGE_MS
  ) {
    clearDraft()
    return null
  }

  // Never started (or startedAt null), but draft itself is old
  if (now - draft.savedAt > DRAFT_MAX_AGE_MS) {
    clearDraft()
    return null
  }

  return draft
}

/** Status line after restoring a draft. Each photo is checked on its own. */
function resumeMessage(draft: DraftVisit): string {
  const lost: string[] = []
  if (draft.hadIntakeFile) lost.push('before')
  if (draft.hadAfterFile) lost.push('after')
  if (lost.length === 0) {
    return `Resumed timer for ${draft.selectedDog.dog_name}`
  }
  const many = lost.length > 1
  return (
    `Resumed timer for ${draft.selectedDog.dog_name} — the ${lost.join(' and ')} ` +
    `photo${many ? 's' : ''} could not be kept, please pick ${many ? 'them' : 'it'} again`
  )
}

function App() {
  // Read the saved draft once, before the first render, and start from it.
  // (Restoring it in an effect rendered an empty screen first, then the draft.)
  const [draft] = useState<DraftVisit | null>(() => loadDraft())

  const [ownerName, setOwnerName] = useState('')
  const [dogName, setDogName] = useState('')
  const [visitDate, setVisitDate] = useState(draft?.visitDate ?? todayISODate())
  const [actualMinutes, setActualMinutes] = useState(draft?.actualMinutes ?? '')
  const [conditionScore, setConditionScore] = useState(draft?.conditionScore ?? '')
  const [surprise, setSurprise] = useState(draft?.surprise ?? '')
  const [message, setMessage] = useState(() =>
    draft === null ? '' : resumeMessage(draft),
  )
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DogSearchItem[]>([])
  const [screen, setScreen] = useState<Screen>(draft === null ? 'home' : 'capture')
  const [area, setArea] = useState<Area>('this_week')
  const [mode, setMode] = useState<Mode>(draft === null ? 'search' : 'visit')
  const [selectedDog, setSelectedDog] = useState<SelectedDog | null>(
    draft?.selectedDog ?? null,
  )
  const [visitStep, setVisitStep] = useState<VisitStep>(draft?.visitStep ?? 1)
  const [intakeFile, setIntakeFile] = useState<File | null>(null)
  const [afterFile, setAfterFile] = useState<File | null>(null)
  const [timerStatus, setTimerStatus] = useState<TimerStatus>(
    draft?.timerStatus ?? 'idle',
  )
  const [startedAt, setStartedAt] = useState<number | null>(draft?.startedAt ?? null)
  const [tickNow, setTickNow] = useState(() => Date.now())
  const [services, setServices] = useState<ServiceListItem[]>([])
  const [serviceId, setServiceId] = useState(draft?.serviceId ?? '')
  const [finalPrice, setFinalPrice] = useState(draft?.finalPrice ?? '')
  const [tip, setTip] = useState(draft?.tip ?? '')
  const [quotedPrice, setQuotedPrice] = useState(draft?.quotedPrice ?? '')
  const [shavedDown, setShavedDown] = useState(draft?.shavedDown ?? false)
  // Owner created by a "new client" attempt whose dog step failed. A retry with
  // the same owner name reuses it instead of creating the owner again.
  const [pendingOwner, setPendingOwner] = useState<
    (CreatedOwner & { typed: string }) | null
  >(null)
  // One in-flight guard for both write flows: a second tap while a request
  // is running creates duplicate visits / owners (#92 phone trial).
  const [isBusy, setIsBusy] = useState(false)

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

  useEffect(() => {
    // No dog / not in visit wizard -> nothing to persist
    if (selectedDog === null || mode !== 'visit') {
      return
    }

    saveDraft({
      selectedDog,
      visitStep,
      timerStatus,
      startedAt,
      actualMinutes,
      visitDate,
      conditionScore,
      surprise,
      serviceId,
      finalPrice,
      tip,
      quotedPrice,
      shavedDown,
      hadIntakeFile: intakeFile !== null,
      hadAfterFile: afterFile !== null,
    })
  }, [
    selectedDog,
    mode,
    visitStep,
    timerStatus,
    startedAt,
    actualMinutes,
    visitDate,
    conditionScore,
    surprise,
    intakeFile,
    afterFile,
    serviceId,
    finalPrice,
    tip,
    quotedPrice,
    shavedDown,
  ])

  useEffect(() => {
    if (timerStatus !== 'running') return
  
    const id = window.setInterval(() => {
      setTickNow(Date.now())
    }, 250)
  
    return () => window.clearInterval(id)
  }, [timerStatus])

  useEffect(() => {
    void (async () => {
      try {
        const rows = await listServices()
        setServices(rows)
      } catch (error) {
        console.error(error)
        setMessage('Could not load services - check API / seed')
      }
    })()
  }, [])

  function startTimer() {
    const now = Date.now()
    setStartedAt(now)
    setTickNow(now)
    setTimerStatus('running')
    setMessage('')
  }

  function stopTimer() {
    if (startedAt === null) return
    const now = Date.now()
    setTickNow(now)
    setTimerStatus('stopped')
    const minutes = floorMinutes(now - startedAt)
    if (minutes < 1) {
      setActualMinutes('')
      setMessage('Under 1 minute - type minutes manually or press Start again.')
      return
    }
    setActualMinutes(String(minutes))
    setMessage(`Timer stopped: ${minutes} min (floored). You can edit before continuing.`)
  }

  function resetTimer() {
    clearDraft()
    setTimerStatus('idle')
    setStartedAt(null)
    setTickNow(Date.now())
    setActualMinutes('')
    // Do not clear `message` here — saveVisit sets a success line then calls
    // resetTimer; wiping it made successful saves look like a no-op.
  }

  function resetVisitDetails() {
    setConditionScore('')
    setSurprise('')
    setServiceId('')
    setFinalPrice('')
    setTip('')
    setQuotedPrice('')
    setShavedDown(false)
  }


  async function saveVisit() {
    if (selectedDog === null) {
      setMessage('No dog selected - go back and pick one.')
      return
    }
    if (isBusy) {
      return
    }
    if (serviceId.trim() === '' || Number(serviceId) < 1) {
      setMessage('Pick a service package.')
      return
    }
    if (finalPrice.trim() === '' || Number(finalPrice) < 0 || Number.isNaN(Number(finalPrice))) {
      setMessage('Enter a final price (€).')
      return
    }

    setIsBusy(true)
    setMessage('Saving...')
    try {
      const visitBody: Record<string, unknown> = {
        owner_id: selectedDog.owner_id,
        dog_id: selectedDog.dog_id,
        visit_date: visitDate,
        actual_minutes: Number(actualMinutes),
        status: 'completed',
        actual_service_id: Number(serviceId),
        booked_service_id: Number(serviceId), // until booking exists: booked = actual
        final_price: Number(finalPrice),
        shaved_down: shavedDown,
      }
      if (conditionScore.trim() !== '') {
        visitBody.condition_score = Number(conditionScore)
      }
      if (surprise.trim() !== '') {
        visitBody.what_surprised_me = surprise.trim()
      }
      if (tip.trim() !== '') {
        visitBody.tip = Number(tip)
      }
      if (quotedPrice.trim() !== '') {
        visitBody.quoted_price = Number(quotedPrice)
      }

      const visit = await createVisit(visitBody)
      const savedId = visit.visit_id

      // The visit is saved from here on. Nothing below may claim otherwise
      const photoJobs: Array<[File, 'intake' | 'after']> = []
      if (intakeFile !== null) {
        photoJobs.push([intakeFile, 'intake'])
      }
      if (afterFile !== null) {
        photoJobs.push([afterFile, 'after'])
      }

      let photoNote = ''
      if (photoJobs.length > 0) {
        setMessage(`Visit saved - uploading ${photoJobs.length} photos...`)

        let uploaded = 0
        for (const [file, kind] of photoJobs) {
          try {
            await uploadVisitPhoto(savedId, file, kind)
            uploaded += 1
          } catch (error) {
            // Never rethrow: the visit is already saved and the outer catch
            // would tell the user it was not
            console.error(error)
          }
        }

        photoNote =
          uploaded === photoJobs.length
          ? ` · ${uploaded} photo(s)`
          : ` · only ${uploaded}/${photoJobs.length} photos uploaded - visit is safe`
      }

      clearDraft()
      setSelectedDog(null)
      resetVisitDetails()
      setVisitStep(1)
      setIntakeFile(null)
      setAfterFile(null)
      setVisitDate(todayISODate())
      resetTimer()
      setMode('search')
      setScreen('home')
      setMessage(
        `Saved ${selectedDog.dog_name} · ${selectedDog.owner_name}${photoNote}`,
      )
    } catch (error) {
      setMessage(`Not saved: ${errorMessage(error)}. Try again.`)
      console.error(error)
    } finally {
      // Always re-enable, or one failed save locks the screen until a reload.
      setIsBusy(false)
    }
  }

  function openCapture(): void {
    setScreen('capture')
    setMode('search')
    setQuery('')
    setSelectedDog(null)
    setMessage('')
    void (async () => {
      try {
        const rows = await searchDogs('')
        setResults(rows)
      } catch (error) {
        console.error(error)
        setResults([])
        setMessage(errorMessage(error))
      }
    })()
  }

  function exitCapture(): void {
    clearDraft()
    setSelectedDog(null)
    resetVisitDetails()
    setVisitStep(1)
    setIntakeFile(null)
    setAfterFile(null)
    resetTimer()
    setMode('search')
    setQuery('')
    setResults([])
    setScreen('home')
    setMessage('')
  }

  /**
   * Close / Cancel visit. Never while a save is running (the draft would be
   * cleared under it), and ask first if the timer is still going: one stray
   * tap would otherwise end a groom.
   */
  function requestExitCapture(): void {
    if (isBusy) return
    if (
      timerStatus === 'running' &&
      !window.confirm('Discard this visit? The timer is still running.')
    ) {
      return
    }
    exitCapture()
  }

  function requestResetTimer(): void {
    if (
      timerStatus === 'running' &&
      !window.confirm('Reset the timer? The time so far will be lost.')
    ) {
      return
    }
    resetTimer()
  }

  function startVisitForDog(dog: SelectedDog): void {
    setSelectedDog(dog)
    resetVisitDetails()
    setVisitStep(1)
    setIntakeFile(null)
    setAfterFile(null)
    setVisitDate(todayISODate())
    resetTimer()
    setScreen('capture')
    setMode('visit')
    setMessage('')
  }

  async function continueNewClient() {
    if (isBusy) {
      return
    }
    const ownerTyped = ownerName.trim()
    const dogTyped = dogName.trim()
    if (ownerTyped === '' || dogTyped === '') {
      setMessage('Enter both an owner name and a dog name.')
      return
    }

    setIsBusy(true)
    setMessage('Creating...')
    try {
      let owner: CreatedOwner
      if (pendingOwner !== null && pendingOwner.typed === ownerTyped) {
        // Owner already exists from the last attempt: only the dog is left.
        owner = pendingOwner
      } else {
        owner = await createOwner(ownerTyped)
        setPendingOwner({ ...owner, typed: ownerTyped })
      }

      const dog = await createDog(owner.owner_id, dogTyped)

      setSelectedDog({
        dog_id: dog.dog_id,
        owner_id: owner.owner_id,
        dog_name: dog.name,
        owner_name: owner.name,
      })
      resetVisitDetails()
      setVisitStep(1)
      setIntakeFile(null)
      setAfterFile(null)
      setVisitDate(todayISODate())
      resetTimer()
      setMode('visit')
      setMessage(`Ready: ${dog.name} · ${owner.name}`)
      setPendingOwner(null)
      setOwnerName('')
      setDogName('')
    } catch (error) {
      setMessage(`Could not create client: ${errorMessage(error)}`)
      console.error(error)
    } finally {
      setIsBusy(false)
    }
  }


  const elapsedMs =
    startedAt !== null &&
    (timerStatus === 'running' || timerStatus === 'stopped')
      ? tickNow - startedAt
      : 0

  const captureMatches = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q === '') return results
    return results.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.owner_name.toLowerCase().includes(q),
    )
  }, [query, results])

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
              <Directory onStartVisit={startVisitForDog} />
            )}
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
        <>
          <header className="app-header app-header-capture">
            <button
              type="button"
              className="header-back"
              onClick={requestExitCapture}
              disabled={isBusy}
            >
              Close
            </button>
            <h1>
              {mode === 'new'
                ? 'New client'
                : mode === 'visit' && selectedDog !== null
                  ? selectedDog.dog_name
                  : 'New visit'}
            </h1>
          </header>

          {message !== '' && (
            <p className="status" role="status">
              {message}
            </p>
          )}

      {mode === 'search' && (
        <section className="panel">
          <p className="step-meta">Who's in the chair?</p>
          <div className="search-bar">
            <label className="visually-hidden" htmlFor="dog_search">
              Search dog or owner
            </label>
            <input
              id="dog_search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter dogs or owners…"
              autoComplete="off"
              autoFocus
            />
          </div>
          <button
            type="button"
            className="ghost full-width"
            onClick={() => {
              setMode('new')
              setMessage('')
            }}
          >
            New client instead
          </button>
          <ul className="dir-card-list">
            {captureMatches.map((dog) => (
              <li key={dog.dog_id}>
                <button
                  type="button"
                  className="dir-card"
                  onClick={() => {
                    startVisitForDog({
                      dog_id: dog.dog_id,
                      owner_id: dog.owner_id,
                      dog_name: dog.name,
                      owner_name: dog.owner_name,
                    })
                  }}
                >
                  <div className="dir-card-body">
                    <span className="dir-card-title">{dog.name}</span>
                    <span className="dir-card-meta">{dog.owner_name}</span>
                  </div>
                  <span className="dir-card-action">Visit</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {mode === 'new' && (
        <section className="panel">
          <div className="field">
            <label htmlFor="owner_name">Owner name</label>
            <input
              id="owner_name"
              type="text"
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="dog_name">Dog name</label>
            <input
              id="dog_name"
              type="text"
              value={dogName}
              onChange={(e) => setDogName(e.target.value)}
            />
          </div>
          <div className="actions stack">
            <button
              type="button"
              className="primary"
              onClick={continueNewClient}
              disabled={isBusy}
            >
              {isBusy ? 'Creating…' : 'Continue to visit'}
            </button>
            <button
              type="button"
              className="ghost"
              disabled={isBusy}
              onClick={() => {
                setMode('search')
                setMessage('')
              }}
            >
              Back
            </button>
          </div>
        </section>
      )}

      {mode === 'visit' && selectedDog !== null && (
        <section className="panel">
          <p className="visit-owner">{selectedDog.owner_name}</p>
          <p className="step-meta">Step {visitStep} of 3</p>

          {visitStep === 1 && (
            <>
              <PhotoPicker
                label="Before photo (optional)"
                inputId="intake-photo"
                file={intakeFile}
                onPick={setIntakeFile}
                disabled={isBusy}
              />
              <div className="actions stack">
                <button
                  type="button"
                  className="primary"
                  onClick={() => setVisitStep(2)}
                >
                  Continue
                </button>
              </div>
            </>
          )}

          {visitStep === 2 && (
            <>
              <p className="timer-readout">
                {timerStatus === 'idle' && 'Ready'}
                {timerStatus === 'running' && `Running ${formatElapsed(elapsedMs)}`}
                {timerStatus === 'stopped' && `Stopped ${formatElapsed(elapsedMs)}`}
              </p>
              <div className="timer-controls">
                <button
                  type="button"
                  className="primary"
                  onClick={startTimer}
                  disabled={timerStatus === 'running'}
                >
                  Start
                </button>
                <button
                  type="button"
                  onClick={stopTimer}
                  disabled={timerStatus !== 'running'}
                >
                  Stop
                </button>
                <button type="button" onClick={requestResetTimer}>
                  Reset
                </button>
              </div>
              <div className="field">
                <label htmlFor="actual_minutes">Actual minutes</label>
                <input
                  id="actual_minutes"
                  type="number"
                  min={1}
                  value={actualMinutes}
                  onChange={(e) => setActualMinutes(e.target.value)}
                />
              </div>
              <div className="actions stack">
                <button
                  type="button"
                  className="primary"
                  onClick={() => {
                    if (Number(actualMinutes) < 1) {
                      setMessage('Need minutes ≥ 1 (use timer or type).')
                      return
                    }
                    setMessage('')
                    setVisitStep(3)
                  }}
                >
                  Continue
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => setVisitStep(1)}
                  disabled={isBusy}
                >
                  Back
                </button>
              </div>
            </>
          )}

          {visitStep === 3 && (
            <>
              <div className="field">
                <label htmlFor="visit_date">Visit date</label>
                <input
                  id="visit_date"
                  type="date"
                  value={visitDate}
                  onChange={(e) => setVisitDate(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="service_id">Service</label>
                <select
                  id="service_id"
                  value={serviceId}
                  onChange={(e) => setServiceId(e.target.value)}
                  disabled={isBusy || services.length === 0}
                >
                  <option value="">Select package…</option>
                  {services.map((s) => (
                    <option key={s.service_id} value={String(s.service_id)}>
                      {s.name_en ?? s.slug ?? `Service ${s.service_id}`}
                      {s.base_minutes != null ? ` (~${s.base_minutes} min)` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="final_price">Final price (€)</label>
                <input
                  id="final_price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={finalPrice}
                  onChange={(e) => setFinalPrice(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="tip">Tip (€, optional)</label>
                <input
                  id="tip"
                  type="number"
                  min={0}
                  step="0.01"
                  value={tip}
                  onChange={(e) => setTip(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="quoted_price">Quoted price (€, optional)</label>
                <input
                  id="quoted_price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={quotedPrice}
                  onChange={(e) => setQuotedPrice(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="condition_score">
                  Coat condition (optional) — 0 worst … 5 best
                </label>
                <input
                  id="condition_score"
                  type="number"
                  min={0}
                  max={5}
                  inputMode="numeric"
                  placeholder="0–5"
                  value={conditionScore}
                  onChange={(e) => setConditionScore(e.target.value)}
                />
              </div>
              <label className="checkbox-row" htmlFor="shaved_down">
                <input
                  id="shaved_down"
                  type="checkbox"
                  checked={shavedDown}
                  onChange={(e) => setShavedDown(e.target.checked)}
                  disabled={isBusy}
                />
                Shaved down
              </label>
              <div className="field">
                <label htmlFor="surprise">What surprised me (optional)</label>
                <input
                  id="surprise"
                  type="text"
                  value={surprise}
                  onChange={(e) => setSurprise(e.target.value)}
                />
              </div>

              <PhotoPicker
                label="After photo (optional)"
                inputId="after-photo"
                file={afterFile}
                onPick={setAfterFile}
                disabled={isBusy}
              />

              <div className="actions stack">
                <button
                  type="button"
                  className="primary"
                  onClick={saveVisit}
                  disabled={isBusy}
                >
                  {isBusy ? 'Saving…' : 'Save visit'}
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => setVisitStep(2)}
                  disabled={isBusy}
                >
                  Back
                </button>
              </div>
            </>
          )}

          <button
            type="button"
            className="ghost"
            onClick={requestExitCapture}
            disabled={isBusy}
          >
            Cancel visit
          </button>
        </section>
      )}
        </>
      )}
    </main>
  )
}

export default App