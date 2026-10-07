import { useEffect, useState } from 'react'
import './App.css'
import { PhotoPicker } from './PhotoPicker'

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

function todayISODate(): string {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

type Mode = 'search' | 'new' | 'visit'

type SelectedDog = {
  dog_id: number
  owner_id: number
  dog_name: string
  owner_name: string
}

type DogSearchItem = {
  dog_id: number
  name: string
  owner_id: number
  owner_name: string
  last_visit_date: string | null
}

type ServiceListItem = {
  service_id: number
  slug: string | null
  name_en: string | null
  name_de: string | null
  base_minutes: number | null
  price_base: number | null
}

function apiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY,
  }
}

function apiKeyOnlyHeaders(): HeadersInit {
  // No Content-Type: the browser must set multipart/form-data itself
  // because it has to append the boundary marker that separates parts
  return { 'X-API-Key': import.meta.env.VITE_API_KEY }
}

async function readJson(res: Response): Promise<unknown> {
  const text = await res.text()
  let data: unknown = null
  if (text !== '') {
    try {
      data = JSON.parse(text)
    } catch {
      data = text // plain-text body (e.g. "Internal Server Error")
    }
  }

  if (!res.ok) {
    let message: string

    if (res.status >= 500) {
      message = `Server error (${res.status})`
    } else if (
      typeof data === 'object' &&
      data !== null &&
      'detail' in data
    ) {
      const detail = (data as { detail: unknown }).detail
      message =
        typeof detail === 'string'
        ? detail
        : `Request failed (${res.status}): ${JSON.stringify(detail)}`
    } else if (typeof data === 'string' && data !== '') {
      message = `Request failed (${res.status}): ${data}`
    } else {
      message = `Request failed (${res.status})`
    }

    throw new Error(message)
  }

  return data
}

async function searchDogs(q: string): Promise<DogSearchItem[]> {
  const params = new URLSearchParams()
  if (q.trim() !== '') {
    params.set('q', q.trim())
  }
  const qs = params.toString()
  const url = qs ? `/api/dogs?${qs}` : '/api/dogs'

  const res = await fetch(url, {
    method: 'GET',
    headers: apiHeaders(),
  })
  const data = await readJson(res)
  return data as DogSearchItem[]
}

async function listServices(): Promise<ServiceListItem[]> {
  const res = await fetch('/api/services', {
    method: 'GET',
    headers: apiHeaders(),
  })
  const data = await readJson(res)
  return data as ServiceListItem[]
}

async function uploadPhoto(
  visitId: number,
  file: File,
  kind: 'intake' | 'after',
): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  form.append('kind', kind)

  const res = await fetch(`/api/visits/${visitId}/photos`, {
    method: 'POST',
    headers: apiKeyOnlyHeaders(),
    body: form,
  })
  await readJson(res) // throws with the honest message
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

function App() {
  const [ownerName, setOwnerName] = useState('')
  const [dogName, setDogName] = useState('')
  const [visitDate, setVisitDate] = useState(todayISODate())
  const [actualMinutes, setActualMinutes] = useState('')
  const [conditionScore, setConditionScore] = useState('')
  const [surprise, setSurprise] = useState('')
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DogSearchItem[]>([])
  const [mode, setMode] = useState<Mode>('search')
  const [selectedDog, setSelectedDog] = useState<SelectedDog | null>(null)
  const [visitStep, setVisitStep] = useState<VisitStep>(1)
  const [intakeFile, setIntakeFile] = useState<File | null>(null)
  const [afterFile, setAfterFile] = useState<File | null>(null)
  const [timerStatus, setTimerStatus] = useState<TimerStatus>('idle')
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [tickNow, setTickNow] = useState(() => Date.now())
  const [services, setServices] = useState<ServiceListItem[]>([])
  const [serviceId, setServiceId] = useState('')
  const [finalPrice, setFinalPrice] = useState('')
  const [tip, setTip] = useState('')
  const [quotedPrice, setQuotedPrice] = useState('')
  const [shavedDown, setShavedDown] = useState(false)
  // One in-flight guard for both write flows: a second tap while a request
  // is running creates duplicate visits / owners (#92 phone trial).
  const [isBusy, setIsBusy] = useState(false)

  useEffect(() => {
    const draft = loadDraft()
    if (draft === null) {
      return
    }

    setSelectedDog(draft.selectedDog)
    setVisitStep(draft.visitStep)
    setTimerStatus(draft.timerStatus)
    setStartedAt(draft.startedAt)
    setActualMinutes(draft.actualMinutes)
    setVisitDate(draft.visitDate)
    setConditionScore(draft.conditionScore)
    setSurprise(draft.surprise)
    setServiceId(draft.serviceId ?? '')
    setFinalPrice(draft.finalPrice ?? '')
    setTip(draft.tip ?? '')
    setQuotedPrice(draft.quotedPrice ?? '')
    setShavedDown(draft.shavedDown ?? false)
    setMode('visit')
    setTickNow(Date.now())
    
    const lost: string[] = []
    if (draft.hadIntakeFile) {
      lost.push('before')
      if (draft.hadAfterFile) {
        lost.push('after')
      }

      setMessage(
        lost.length === 0
        ? `Resumed timer for ${draft.selectedDog.dog_name}`
        : `Resumed timer for ${draft.selectedDog.dog_name} - the ${lost.join(' and ')} ` +
          `photo${lost.length > 1 ? 's' : ''} could not be kept, please pick ` +
          `${lost.length > 1 ? 'them' : 'it'} again`,
      )
    }
  }, []) // empty deps = run once after first paint

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

      const visitRes = await fetch('/api/visits', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify(visitBody),
      })
      const visit = (await readJson(visitRes)) as { visit_id: number }
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
            await uploadPhoto(savedId, file, kind)
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
      setMessage(
        `Saved visit_id=${savedId} (${selectedDog.dog_name} · ${selectedDog.owner_name})${photoNote}`,
      )
    } catch (error) {
      setMessage(`Not saved — try again`)
      console.error(error)
    } finally {
      // Always re-enable, or one failed save locks the screen until a reload.
      setIsBusy(false)
    }
  }

  async function continueNewClient() {
    if (isBusy) {
      return
    }

    setIsBusy(true)
    setMessage('Creating...')
    try {
      const ownerRes = await fetch('/api/owners', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ name: ownerName }),
      })
      const owner = (await readJson(ownerRes)) as {
        owner_id: number
        name: string
      }
      
      const dogRes = await fetch('/api/dogs', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({
          owner_id: owner.owner_id,
          name: dogName,
        }),
      })
      const dog = (await readJson(dogRes)) as {
        dog_id: number
        name: string
      }

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
    } catch (error) {
      setMessage(`Could not create client — try again`)
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

  return (
    <main className="app">
      <header className="app-header">
        <h1>MuttMetrics</h1>
        <p className="tagline">Salon capture</p>
      </header>

      {message !== '' && <p className="status" role="status">{message}</p>}

      {mode === 'search' && (
        <section className="panel">
          <h2>Find a dog</h2>
          <div className="field">
            <label htmlFor="dog_search">Dog name</label>
            <input
              id="dog_search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search…"
              autoComplete="off"
            />
          </div>
          <div className="actions">
            <button
              type="button"
              className="primary"
              onClick={async () => {
                try {
                  setMessage('Searching…')
                  const rows = await searchDogs(query)
                  setResults(rows)
                  setMessage(`Found ${rows.length}`)
                } catch (error) {
                  console.error(error)
                  if (error instanceof TypeError) {
                    setMessage("Can't reach server — check your connection")
                  } else if (error instanceof Error) {
                    setMessage(error.message)
                  } else {
                    setMessage(String(error))
                  }
                }
              }}
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('new')
                setMessage('')
              }}
            >
              New client
            </button>
          </div>
          <ul className="dog-list">
            {results.map((dog) => (
              <li key={dog.dog_id}>
                <div className="dog-meta">
                  {dog.name}
                  <span>{dog.owner_name}</span>
                </div>
                <button
                  type="button"
                  className="primary"
                  onClick={() => {
                    setSelectedDog({
                      dog_id: dog.dog_id,
                      owner_id: dog.owner_id,
                      dog_name: dog.name,
                      owner_name: dog.owner_name,
                    })
                    resetVisitDetails()
                    setMode('visit')
                    setMessage('')
                    setVisitStep(1)
                    setIntakeFile(null)
                    setAfterFile(null)
                    setVisitDate(todayISODate())
                    resetTimer()
                  }}
                >
                  Use this dog
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {mode === 'new' && (
        <section className="panel">
          <h2>New client</h2>
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
          <h2 className="visit-title">
            {selectedDog.dog_name}
            <span>{selectedDog.owner_name}</span>
          </h2>
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
                <button type="button" onClick={resetTimer}>
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
                >
                  Back
                </button>
              </div>
            </>
          )}

          <button
            type="button"
            className="ghost"
            onClick={() => {
              clearDraft()
              setSelectedDog(null)
              resetVisitDetails()
              setVisitStep(1)
              setIntakeFile(null)
              setAfterFile(null)
              resetTimer()
              setMode('search')
              setMessage('')
            }}
          >
            Cancel to search
          </button>
        </section>
      )}
    </main>
  )
}

export default App