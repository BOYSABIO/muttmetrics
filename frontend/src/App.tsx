import { useState } from 'react'
import './App.css'

function apiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY,
  }
}

function App() {
  const [ownerName, setOwnerName] = useState('')
  const [dogName, setDogName] = useState('')
  const [visitDate, setVisitDate] = useState('')
  const [actualMinutes, setActualMinutes] = useState('')
  const [conditionScore, setConditionScore] = useState('')
  const [surprise, setSurprise] = useState('')
  const [message, setMessage] = useState('')

  async function saveVisit() {
    setMessage('Saving…')
    try {
      // 1) Owner
      const ownerRes = await fetch('/api/owners', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ name: ownerName }),
      })
      const owner = await ownerRes.json()
      if (!ownerRes.ok) {
        setMessage(`Owner error ${ownerRes.status}: ${JSON.stringify(owner)}`)
        return
      }

      // 2) Dog
      const dogRes = await fetch('/api/dogs', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({
          owner_id: owner.owner_id,
          name: dogName,
        }),
      })
      const dog = await dogRes.json()
      if (!dogRes.ok) {
        setMessage(`Dog error ${dogRes.status}: ${JSON.stringify(dog)}`)
        return
      }

      // 3) Visit
      const visitBody: Record<string, unknown> = {
        owner_id: owner.owner_id,
        dog_id: dog.dog_id,
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

      const visitRes = await fetch('/api/visits', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify(visitBody),
      })
      const visit = await visitRes.json()
      if (!visitRes.ok) {
        setMessage(`Visit error ${visitRes.status}: ${JSON.stringify(visit)}`)
        return
      }

      setMessage(
        `Saved visit_id=${visit.visit_id} (owner ${owner.owner_id}, dog ${dog.dog_id})`,
      )
    } catch (error) {
      setMessage(`Network error: ${String(error)}`)
    }
  }

  return (
    <main>
      <h1>MuttMetrics</h1>
      <p>Capture a visit</p>

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
        <label htmlFor="actual_minutes">Actual minutes</label>
        <br />
        <input
          id="actual_minutes"
          type="number"
          min={1}
          value={actualMinutes}
          onChange={(e) => setActualMinutes(e.target.value)}
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

      <p>
        <button type="button" onClick={saveVisit}>
          Save visit
        </button>
      </p>

      <p>{message}</p>
    </main>
  )
}

export default App