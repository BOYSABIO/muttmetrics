import { useEffect, useMemo, useState } from 'react'
import {
  createDog,
  createOwner,
  createVisit,
  errorMessage,
  fetchOwnerProfile,
  listAddOns,
  listServices,
  OwnerNameConflictError,
  searchDogs,
  searchOwners,
  uploadVisitPhoto,
  type AddOnListItem,
  type CreatedOwner,
  type DogSearchItem,
  type OwnerConflictCandidate,
  type OwnerDogItem,
  type OwnerSearchItem,
  type ServiceListItem,
} from './api'
import { todayISODate } from './dates'
import {
  clearDraft,
  resumeMessage,
  saveDraft,
  type DraftVisit,
  type SelectedDog,
  type TimerStatus,
  type VisitStep,
} from './draft'
import { PhotoPicker } from './PhotoPicker'

function formatElapsed(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function floorMinutes(ms: number): number {
  return Math.floor(ms / 60000)
}

type Mode = 'search' | 'new' | 'visit' | 'after_save'

type AfterSaveState = {
  owner_id: number
  owner_name: string
  visit_date: string
  saved_dog_id: number
  saved_dog_name: string
  dogs: OwnerDogItem[]
  statusLine: string
}

type CaptureProps = {
  /** A saved in-progress visit to resume, if the tab was killed mid-groom. */
  draft: DraftVisit | null
  /** Start straight at the visit wizard for this dog (from Clients). */
  startDog: SelectedDog | null
  /** Leave capture. `message` is shown on the home screen ('' for none). */
  onDone: (message: string) => void
}

/**
 * The capture flow: pick or create a dog, then the 3-step visit wizard
 * (before photo, timer, details). Mounted only while capturing, so every
 * visit starts from fresh state; the draft in localStorage is what survives.
 */
export function Capture({ draft, startDog, onDone }: CaptureProps) {
  const [ownerName, setOwnerName] = useState('')
  const [ownerPhone, setOwnerPhone] = useState('')
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
  const [mode, setMode] = useState<Mode>(
    draft !== null || startDog !== null ? 'visit' : 'search',
  )
  const [selectedDog, setSelectedDog] = useState<SelectedDog | null>(
    draft?.selectedDog ?? startDog,
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
  const [addOns, setAddOns] = useState<AddOnListItem[]>([])
  const [addOnIds, setAddOnIds] = useState<number[]>(draft?.addOnIds ?? [])
  const [finalPrice, setFinalPrice] = useState(draft?.finalPrice ?? '')
  const [tip, setTip] = useState(draft?.tip ?? '')
  const [quotedPrice, setQuotedPrice] = useState(draft?.quotedPrice ?? '')
  const [shavedDown, setShavedDown] = useState(draft?.shavedDown ?? false)
  // Owner created by a "new client" attempt whose dog step failed. A retry with
  // the same owner name reuses it instead of creating the owner again.
  const [pendingOwner, setPendingOwner] = useState<
    (CreatedOwner & { typed: string }) | null
  >(null)
  // Picked from GET /owners search — skip POST /owners (#191).
  const [pickedOwner, setPickedOwner] = useState<OwnerSearchItem | null>(null)
  // Live owner search hits while typing a new-client name.
  const [ownerHits, setOwnerHits] = useState<OwnerSearchItem[]>([])
  // 409 candidates when create would silently merge (#187).
  const [nameConflicts, setNameConflicts] = useState<OwnerConflictCandidate[]>(
    [],
  )
  // One in-flight guard for both write flows: a second tap while a request
  // is running creates duplicate visits / owners (#92 phone trial).
  const [isBusy, setIsBusy] = useState(false)
  // After a save: offer another dog from the same owner (#191).
  const [afterSave, setAfterSave] = useState<AfterSaveState | null>(null)
  const [nextDogName, setNextDogName] = useState('')

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
      addOnIds,
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
    addOnIds,
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

  // Load the dog list (search mode) and the service catalog once, on open.
  useEffect(() => {
    void (async () => {
      try {
        setResults(await searchDogs(''))
      } catch (error) {
        console.error(error)
        setMessage(errorMessage(error))
      }
    })()
  }, [])

  useEffect(() => {
    void (async () => {
      try {
        const [svc, extras] = await Promise.all([listServices(), listAddOns()])
        setServices(svc)
        setAddOns(extras)
      } catch (error) {
        console.error(error)
        setMessage('Could not load services - check API / seed')
      }
    })()
  }, [])

  // Debounced owner search on the new-client screen (#191).
  // Do not clear hits synchronously in the effect (react-hooks/set-state-in-effect);
  // hide stale rows via ownerHitsVisible below.
  useEffect(() => {
    if (mode !== 'new' || pickedOwner !== null) {
      return
    }
    const q = ownerName.trim()
    if (q.length < 2) {
      return
    }
    let cancelled = false
    const handle = window.setTimeout(() => {
      void (async () => {
        try {
          const hits = await searchOwners(q)
          if (!cancelled) {
            setOwnerHits(hits)
          }
        } catch (error) {
          console.error(error)
        }
      })()
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(handle)
    }
  }, [mode, ownerName, pickedOwner])

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
    // Updater form: avoid impure Date.now() as a direct setState arg (react-hooks/purity).
    setTickNow(() => Date.now())
    setActualMinutes('')
    // Do not clear `message` here — saveVisit sets a success line then calls
    // resetTimer; wiping it made successful saves look like a no-op.
  }

  function resetVisitDetails() {
    setConditionScore('')
    setSurprise('')
    setServiceId('')
    setAddOnIds([])
    setFinalPrice('')
    setTip('')
    setQuotedPrice('')
    setShavedDown(false)
  }

  function toggleAddOn(id: number) {
    setAddOnIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
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
        add_on_ids: addOnIds,
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
      const statusLine = `Saved ${selectedDog.dog_name} · ${selectedDog.owner_name}${photoNote}`
      try {
        const profile = await fetchOwnerProfile(selectedDog.owner_id)
        setAfterSave({
          owner_id: selectedDog.owner_id,
          owner_name: selectedDog.owner_name,
          visit_date: visitDate,
          saved_dog_id: selectedDog.dog_id,
          saved_dog_name: selectedDog.dog_name,
          dogs: profile.dogs,
          statusLine,
        })
        setSelectedDog(null)
        setMode('after_save')
        setNextDogName('')
        setMessage(statusLine)
      } catch (profileError) {
        // Visit is saved; if the follow-up list fails, still leave with success.
        console.error(profileError)
        onDone(statusLine)
      }
    } catch (error) {
      setMessage(`Not saved: ${errorMessage(error)}. Try again.`)
      console.error(error)
    } finally {
      // Always re-enable, or one failed save locks the screen until a reload.
      setIsBusy(false)
    }
  }

  function beginVisitForOwnerDog(
    dog: { dog_id: number; name: string },
    owner: { owner_id: number; name: string },
    keepDate: string,
  ): void {
    setSelectedDog({
      dog_id: dog.dog_id,
      owner_id: owner.owner_id,
      dog_name: dog.name,
      owner_name: owner.name,
    })
    setVisitDate(keepDate)
    resetVisitDetails()
    setVisitStep(1)
    setIntakeFile(null)
    setAfterFile(null)
    resetTimer()
    setAfterSave(null)
    setNextDogName('')
    setMode('visit')
    setMessage(`Next: ${dog.name} · ${owner.name}`)
  }

  async function addDogThenVisitFromAfterSave(): Promise<void> {
    if (afterSave === null || isBusy) return
    const name = nextDogName.trim()
    if (name === '') {
      setMessage('Enter a dog name.')
      return
    }
    setIsBusy(true)
    try {
      const dog = await createDog(afterSave.owner_id, name)
      beginVisitForOwnerDog(
        { dog_id: dog.dog_id, name: dog.name },
        { owner_id: afterSave.owner_id, name: afterSave.owner_name },
        afterSave.visit_date,
      )
    } catch (error) {
      setMessage(errorMessage(error))
      console.error(error)
    } finally {
      setIsBusy(false)
    }
  }

  function exitCapture(): void {
    clearDraft()
    setAfterSave(null)
    onDone('')
  }

  /**
   * Close / Cancel visit. Never while a save is running (the draft would be
   * cleared under it), and ask first if the timer is still going: one stray
   * tap would otherwise end a groom.
   */
  function requestExitCapture(): void {
    if (isBusy) return
    if (mode === 'after_save' && afterSave !== null) {
      const line = afterSave.statusLine
      setAfterSave(null)
      onDone(line)
      return
    }
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
    setMode('visit')
    setMessage('')
  }

  function pickExistingOwner(hit: OwnerSearchItem | OwnerConflictCandidate): void {
    setPickedOwner({
      owner_id: hit.owner_id,
      name: hit.name,
      phone: hit.phone,
      dog_count: 'dog_count' in hit ? hit.dog_count : 0,
    })
    setOwnerName(hit.name)
    setOwnerPhone(hit.phone ?? '')
    setOwnerHits([])
    setNameConflicts([])
    setPendingOwner(null)
    setMessage(`Using existing client: ${hit.name}`)
  }

  function clearPickedOwner(): void {
    setPickedOwner(null)
    setOwnerPhone('')
    setNameConflicts([])
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
    setNameConflicts([])
    try {
      let owner: CreatedOwner
      let ownerNote = ''

      if (pickedOwner !== null) {
        // Already a client — only add the dog (#191).
        owner = {
          owner_id: pickedOwner.owner_id,
          name: pickedOwner.name,
          phone: pickedOwner.phone,
        }
        ownerNote = 'existing owner'
      } else if (pendingOwner !== null && pendingOwner.typed === ownerTyped) {
        // Owner already exists from the last attempt: only the dog is left.
        owner = pendingOwner
        ownerNote = 'existing owner'
      } else {
        const result = await createOwner(ownerTyped, ownerPhone)
        owner = result.owner
        setPendingOwner({ ...owner, typed: ownerTyped })
        ownerNote = result.created ? 'new owner' : 'existing owner (matched phone)'
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
      setMessage(`Ready: ${dog.name} · ${owner.name} (${ownerNote})`)
      setPendingOwner(null)
      setPickedOwner(null)
      setOwnerHits([])
      setNameConflicts([])
      setOwnerName('')
      setOwnerPhone('')
      setDogName('')
    } catch (error) {
      if (error instanceof OwnerNameConflictError) {
        setNameConflicts(error.candidates)
        setMessage(
          'That name is already a client. Pick one below, or add a phone to create another.',
        )
      } else {
        setMessage(`Could not create client: ${errorMessage(error)}`)
      }
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

  const ownerHitsVisible =
    mode === 'new' &&
    pickedOwner === null &&
    ownerName.trim().length >= 2
      ? ownerHits
      : []

  return (
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
                : mode === 'after_save'
                  ? 'Saved'
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
            {/* Chunky + — not ghost (ghost becomes an underline in the retro theme). */}
            <button
              type="button"
              className="primary search-bar-new"
              aria-label="New client"
              title="New client"
              onClick={() => {
                setMode('new')
                setMessage('')
                setPickedOwner(null)
                setOwnerHits([])
                setNameConflicts([])
                setOwnerPhone('')
                setPendingOwner(null)
              }}
            >
              +
            </button>
          </div>
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
          <p className="step-meta">
            Already a client? Pick them as you type. Or create new — phone is
            optional unless the name already exists.
          </p>
          <div className="field">
            <label htmlFor="owner_name">Owner name</label>
            <input
              id="owner_name"
              type="text"
              value={ownerName}
              onChange={(e) => {
                const next = e.target.value
                setOwnerName(next)
                if (
                  pickedOwner !== null &&
                  next.trim().toLowerCase() !== pickedOwner.name.toLowerCase()
                ) {
                  clearPickedOwner()
                }
                setNameConflicts([])
              }}
              disabled={isBusy}
              autoComplete="off"
            />
          </div>

          {pickedOwner !== null && (
            <p className="step-meta">
              Using existing client (id {pickedOwner.owner_id}
              {pickedOwner.dog_count > 0
                ? ` · ${pickedOwner.dog_count} dog${pickedOwner.dog_count === 1 ? '' : 's'}`
                : ''}
              ).{' '}
              <button
                type="button"
                className="linkish"
                disabled={isBusy}
                onClick={clearPickedOwner}
              >
                Clear
              </button>
            </p>
          )}

          {ownerHitsVisible.length > 0 && (
            <ul className="dir-card-list">
              {ownerHitsVisible.map((hit) => (
                <li key={hit.owner_id}>
                  <button
                    type="button"
                    className="dir-card"
                    disabled={isBusy}
                    onClick={() => pickExistingOwner(hit)}
                  >
                    <div className="dir-card-body">
                      <span className="dir-card-title">{hit.name}</span>
                      <span className="dir-card-meta">
                        {hit.phone ?? 'No phone'}
                        {hit.dog_count > 0
                          ? ` · ${hit.dog_count} dog${hit.dog_count === 1 ? '' : 's'}`
                          : ''}
                      </span>
                    </div>
                    <span className="dir-card-action">Use</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {nameConflicts.length > 0 && (
            <>
              <p className="step-meta">Did you mean…?</p>
              <ul className="dir-card-list">
                {nameConflicts.map((c) => (
                  <li key={c.owner_id}>
                    <button
                      type="button"
                      className="dir-card"
                      disabled={isBusy}
                      onClick={() => pickExistingOwner(c)}
                    >
                      <div className="dir-card-body">
                        <span className="dir-card-title">{c.name}</span>
                        <span className="dir-card-meta">
                          {c.phone ?? 'No phone'}
                        </span>
                      </div>
                      <span className="dir-card-action">Use</span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {pickedOwner === null && (
            <div className="field">
              <label htmlFor="owner_phone">
                Phone (optional — needed to create a second person with the same
                name)
              </label>
              <input
                id="owner_phone"
                type="tel"
                value={ownerPhone}
                onChange={(e) => setOwnerPhone(e.target.value)}
                disabled={isBusy}
                autoComplete="tel"
              />
            </div>
          )}

          <div className="field">
            <label htmlFor="dog_name">Dog name</label>
            <input
              id="dog_name"
              type="text"
              value={dogName}
              onChange={(e) => setDogName(e.target.value)}
              disabled={isBusy}
            />
          </div>
          <div className="actions stack">
            <button
              type="button"
              className="primary"
              onClick={() => void continueNewClient()}
              disabled={isBusy}
            >
              {isBusy
                ? 'Creating…'
                : pickedOwner !== null
                  ? 'Add dog & continue'
                  : 'Continue to visit'}
            </button>
            <button
              type="button"
              className="ghost"
              disabled={isBusy}
              onClick={() => {
                setMode('search')
                setMessage('')
                setPickedOwner(null)
                setOwnerHits([])
                setNameConflicts([])
                setOwnerPhone('')
              }}
            >
              Back
            </button>
          </div>
        </section>
      )}

      {mode === 'after_save' && afterSave !== null && (
        <section className="panel">
          <p className="step-meta">
            Next: another dog from {afterSave.owner_name}? Same visit date (
            {afterSave.visit_date}). Each dog gets its own timer.
          </p>
          <ul className="dir-card-list">
            {afterSave.dogs
              .filter((d) => d.dog_id !== afterSave.saved_dog_id)
              .map((d) => (
                <li key={d.dog_id}>
                  <button
                    type="button"
                    className="dir-card"
                    disabled={isBusy}
                    onClick={() =>
                      beginVisitForOwnerDog(
                        d,
                        {
                          owner_id: afterSave.owner_id,
                          name: afterSave.owner_name,
                        },
                        afterSave.visit_date,
                      )
                    }
                  >
                    <div className="dir-card-body">
                      <span className="dir-card-title">{d.name}</span>
                      <span className="dir-card-meta">Start visit</span>
                    </div>
                    <span className="dir-card-action">Visit</span>
                  </button>
                </li>
              ))}
          </ul>
          {afterSave.dogs.filter((d) => d.dog_id !== afterSave.saved_dog_id)
            .length === 0 && (
            <p className="step-meta">No other dogs yet — add one below.</p>
          )}
          <div className="field">
            <label htmlFor="next_dog_name">Add a dog</label>
            <input
              id="next_dog_name"
              type="text"
              value={nextDogName}
              onChange={(e) => setNextDogName(e.target.value)}
              disabled={isBusy}
              placeholder="New dog name"
            />
          </div>
          <div className="actions stack">
            <button
              type="button"
              className="primary"
              disabled={isBusy || nextDogName.trim() === ''}
              onClick={() => void addDogThenVisitFromAfterSave()}
            >
              {isBusy ? 'Adding…' : 'Add dog & start visit'}
            </button>
            <button
              type="button"
              disabled={isBusy}
              onClick={() => {
                const line = afterSave.statusLine
                setAfterSave(null)
                onDone(line)
              }}
            >
              Done
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
              {addOns.length > 0 && (
                <div className="field">
                  <label id="add_ons_label">Add-ons (optional)</label>
                  <div
                    className="chip-row"
                    role="group"
                    aria-labelledby="add_ons_label"
                  >
                    {addOns.map((a) => {
                      const on = addOnIds.includes(a.add_on_id)
                      return (
                        <label
                          key={a.add_on_id}
                          className={`chip ${on ? 'chip-on' : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={on}
                            disabled={isBusy}
                            onChange={() => toggleAddOn(a.add_on_id)}
                          />
                          {a.name_en ?? a.slug}
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}
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
  )
}
