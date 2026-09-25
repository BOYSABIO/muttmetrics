import { useEffect, useState } from 'react'
import './App.css'

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

function apiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY,
  }
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
  const [beforePhotoUrl, setBeforePhotoUrl] = useState('')
  const [timerStatus, setTimerStatus] = useState<TimerStatus>('idle')
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [tickNow, setTickNow] = useState(() => Date.now())

  useEffect(() => {
    if (timerStatus !== 'running') return
  
    const id = window.setInterval(() => {
      setTickNow(Date.now())
    }, 250)
  
    return () => window.clearInterval(id)
  }, [timerStatus])

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
    setTimerStatus('idle')
    setStartedAt(null)
    setTickNow(Date.now())
    setActualMinutes('')
    setMessage('')
  }

  async function saveVisit() {
    if (selectedDog === null) {
      setMessage('No dog selected - go back and pick one.')
      return
    }

    setMessage('Saving...')
    try {
      const visitBody: Record<string, unknown> = {
        owner_id: selectedDog.owner_id,
        dog_id: selectedDog.dog_id,
        visit_date: visitDate,
        actual_minutes: Number(actualMinutes),
        status: 'completed',
      }
      if (conditionScore.trim() !== '') {
        visitBody.condition_score = Number(conditionScore)
      }
      if (surprise.trim() !== '') {
        visitBody.what_surprised_me = surprise.trim()
      }
      if (beforePhotoUrl.trim() !== '') {
        visitBody.intake_photos = [beforePhotoUrl.trim()]
      }

      const visitRes = await fetch('/api/visits', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify(visitBody),
      })
      const visit = (await readJson(visitRes)) as { visit_id: number }

      setMessage(
        `Saved visit_id=${visit.visit_id} (${selectedDog.dog_name} · ${selectedDog.owner_name})`,
      )
      setSelectedDog(null)
      setConditionScore('')
      setSurprise('')
      setVisitStep(1)
      setBeforePhotoUrl('')
      setVisitDate(todayISODate())
      resetTimer()
      setMode('search')
    } catch (error) {
      setMessage(`Not saved — try again`)
      console.error(error)
    }
  }

  async function continueNewClient() {
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
      setVisitStep(1)
      setBeforePhotoUrl('')
      setVisitDate(todayISODate())
      resetTimer()
      setMode('visit')
      setMessage(`Ready: ${dog.name} · ${owner.name}`)
    } catch (error) {
      setMessage(`Could not create client — try again`)
      console.error(error)
    }
  }

  const elapsedMs =
    startedAt !== null &&
    (timerStatus === 'running' || timerStatus === 'stopped')
      ? tickNow - startedAt
      : 0

  return (
    <main>
      <h1>MuttMetrics</h1>
      <p>{message}</p>

      {mode === 'search' && (
        <section>
          <h2>Find a dog</h2>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Dog name"
          />
          <button
            type="button"
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
                  setMessage(error.message) // e.g. "Server error (500) or FastAPI detail"
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
          <ul>
            {results.map((dog) => (
              <li key={dog.dog_id}>
                {dog.name} · {dog.owner_name}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDog({
                      dog_id: dog.dog_id,
                      owner_id: dog.owner_id,
                      dog_name: dog.name,
                      owner_name: dog.owner_name,
                    })
                    setMode('visit')
                    setMessage('')
                    setVisitStep(1)
                    setBeforePhotoUrl('')
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
        <section>
          <h2>New client</h2>
          <p>
            <label htmlFor="owner_name">Owner name</label>
            <br />
            <input
              id="owner_name"
              type="text"
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
            />
          </p>
          <p>
            <label htmlFor="dog_name">Dog name</label>
            <br />
            <input
              id="dog_name"
              type="text"
              value={dogName}
              onChange={(e) => setDogName(e.target.value)}
            />
          </p>
          <button type="button" onClick={continueNewClient}>
            Continue to visit
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('search')
              setMessage('')
            }}
          >
            Back
          </button>
        </section>
      )}

      {mode === 'visit' && selectedDog !== null && (
        <section>
          <h2>
            Visit — {selectedDog.dog_name} · {selectedDog.owner_name}
          </h2>
          <p>
            Step {visitStep} of 3
          </p>

          {visitStep === 1 && (
            <>
              <p>
                <label htmlFor="before_photo">
                  Before photo link (optional — upload later)
                </label>
                <br />
                <input
                  id="before_photo"
                  type="url"
                  value={beforePhotoUrl}
                  onChange={(e) => setBeforePhotoUrl(e.target.value)}
                  placeholder="https://…"
                />
              </p>
              <button type="button" onClick={() => setVisitStep(2)}>
                Continue
              </button>
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
              <p>
                <label htmlFor="actual_minutes">Actual minutes (editable)</label>
                <br />
                <input
                  id="actual_minutes"
                  type="number"
                  min={1}
                  value={actualMinutes}
                  onChange={(e) => setActualMinutes(e.target.value)}
                />
              </p>
              <button
                type="button"
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
              <button type="button" onClick={() => setVisitStep(1)}>
                Back
              </button>
            </>
          )}

          {visitStep === 3 && (
            <>
              <p>
                <label htmlFor="visit_date">Visit date</label>
                <br />
                <input
                  id="visit_date"
                  type="date"
                  value={visitDate}
                  onChange={(e) => setVisitDate(e.target.value)}
                />
              </p>
              <p>
                <label htmlFor="condition_score">Condition (0–5, optional)</label>
                <br />
                <input
                  id="condition_score"
                  type="number"
                  min={0}
                  max={5}
                  value={conditionScore}
                  onChange={(e) => setConditionScore(e.target.value)}
                />
              </p>
              <p>
                <label htmlFor="surprise">What surprised me (optional)</label>
                <br />
                <input
                  id="surprise"
                  type="text"
                  value={surprise}
                  onChange={(e) => setSurprise(e.target.value)}
                />
              </p>
              <button type="button" onClick={saveVisit}>
                Save visit
              </button>
              <button type="button" onClick={() => setVisitStep(2)}>
                Back
              </button>
            </>
          )}

          <button
            type="button"
            onClick={() => {
              setSelectedDog(null)
              setVisitStep(1)
              setBeforePhotoUrl('')
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