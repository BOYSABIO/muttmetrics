import { useEffect, useMemo, useState } from 'react'
import { DogAvatar } from './DogAvatar'

export type VisitDogRef = {
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

type VisitSummary = {
  visit_id: number
  visit_date: string
  actual_minutes: number
  condition_score: number | null
  status: string | null
}

type DogProfile = {
  dog_id: number
  owner_id: number
  name: string
  breed_id: number | null
  breed_secondary_id: number | null
  sex: string | null
  date_of_birth: string | null
  weight_kg: string | number | null
  coat_type: string | null
  hair_or_fur: string | null
  coat_density: string | null
  undercoat: boolean | null
  sheds: boolean | null
  handling_score: number | null
  muzzle_required: boolean | null
  two_person_job: boolean | null
  temperament_notes: string | null
  senior_flag: boolean | null
  mobility_notes: string | null
  vet_notes: string | null
  size_band: string | null
  visit_count: number | null
  last_visit_date: string | null
  avatar_photo_id: number | null
  owner: {
    owner_id: number
    name: string
    phone: string | null
    email: string | null
  }
  recent_visits: VisitSummary[]
}

type OwnerDogItem = {
  dog_id: number
  name: string
}

type OwnerProfile = {
  owner_id: number
  name: string
  phone: string | null
  email: string | null
  locale: string
  address_area: string | null
  preferred_channel: string | null
  client_since: string | null
  notes: string | null
  visit_count: number | null
  lifetime_value: number | null
  dogs: OwnerDogItem[]
}

type BreedListItem = {
  breed_id: number
  name_de: string | null
  name_en: string | null
}

const SEX_OPTIONS = [
  { value: '', label: '—' },
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
  { value: 'unknown', label: 'Unknown' },
] as const

const HAIR_OR_FUR_OPTIONS = [
  { value: '', label: '—' },
  { value: 'hair', label: 'Hair' },
  { value: 'fur', label: 'Fur' },
] as const

const COAT_TYPE_OPTIONS = [
  { value: '', label: '—' },
  { value: 'smooth', label: 'Smooth' },
  { value: 'double', label: 'Double' },
  { value: 'curly', label: 'Curly' },
  { value: 'single', label: 'Single' },
] as const

const COAT_DENSITY_OPTIONS = [
  { value: '', label: '—' },
  { value: 'light', label: 'Light' },
  { value: 'medium', label: 'Medium' },
  { value: 'dense', label: 'Dense' },
] as const

const HANDLING_OPTIONS = [
  { value: '', label: '—' },
  { value: '1', label: '1 — easy' },
  { value: '2', label: '2' },
  { value: '3', label: '3 — neutral' },
  { value: '4', label: '4' },
  { value: '5', label: '5 — difficult' },
] as const

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
      data = text
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
  const res = await fetch(url, { method: 'GET', headers: apiHeaders() })
  return (await readJson(res)) as DogSearchItem[]
}

async function listBreeds(): Promise<BreedListItem[]> {
  const res = await fetch('/api/breeds', { method: 'GET', headers: apiHeaders() })
  return (await readJson(res)) as BreedListItem[]
}

async function fetchDogProfile(dogId: number): Promise<DogProfile> {
  const res = await fetch(`/api/dogs/${dogId}`, {
    method: 'GET',
    headers: apiHeaders(),
  })
  return (await readJson(res)) as DogProfile
}

async function patchDog(
  dogId: number,
  body: Record<string, unknown>,
): Promise<DogProfile> {
  const res = await fetch(`/api/dogs/${dogId}`, {
    method: 'PATCH',
    headers: apiHeaders(),
    body: JSON.stringify(body),
  })
  return (await readJson(res)) as DogProfile
}

async function fetchOwnerProfile(ownerId: number): Promise<OwnerProfile> {
  const res = await fetch(`/api/owners/${ownerId}`, {
    method: 'GET',
    headers: apiHeaders(),
  })
  return (await readJson(res)) as OwnerProfile
}

async function patchOwner(
  ownerId: number,
  body: Record<string, unknown>,
): Promise<OwnerProfile> {
  const res = await fetch(`/api/owners/${ownerId}`, {
    method: 'PATCH',
    headers: apiHeaders(),
    body: JSON.stringify(body),
  })
  return (await readJson(res)) as OwnerProfile
}

async function uploadDogProfilePhoto(
  dogId: number,
  file: File,
): Promise<{ photo_id: number }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`/api/dogs/${dogId}/photos`, {
    method: 'POST',
    headers: { 'X-API-Key': import.meta.env.VITE_API_KEY },
    body: form,
  })
  return (await readJson(res)) as { photo_id: number }
}

function breedLabel(b: BreedListItem): string {
  if (b.name_de && b.name_en && b.name_de !== b.name_en) {
    return `${b.name_de} / ${b.name_en}`
  }
  return b.name_de || b.name_en || `Breed ${b.breed_id}`
}

function errorMessage(error: unknown): string {
  if (error instanceof TypeError) {
    return "Can't reach server — check your connection"
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

type DirectoryProps = {
  onStartVisit?: (dog: VisitDogRef) => void
}

export function Directory({ onStartVisit }: DirectoryProps) {
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DogSearchItem[]>([])
  const [breeds, setBreeds] = useState<BreedListItem[]>([])
  const [isBusy, setIsBusy] = useState(false)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q === '') return results
    return results.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.owner_name.toLowerCase().includes(q),
    )
  }, [query, results])

  const [directoryProfile, setDirectoryProfile] = useState<DogProfile | null>(
    null,
  )
  const [directoryOwner, setDirectoryOwner] = useState<OwnerProfile | null>(null)

  const [dirName, setDirName] = useState('')
  const [dirBreedId, setDirBreedId] = useState('')
  const [dirSex, setDirSex] = useState('')
  const [dirWeightKg, setDirWeightKg] = useState('')
  const [dirCoatType, setDirCoatType] = useState('')
  const [dirHairOrFur, setDirHairOrFur] = useState('')
  const [dirCoatDensity, setDirCoatDensity] = useState('')
  const [dirUndercoat, setDirUndercoat] = useState(false)
  const [dirSheds, setDirSheds] = useState(false)
  const [dirHandlingScore, setDirHandlingScore] = useState('')
  const [dirMuzzleRequired, setDirMuzzleRequired] = useState(false)
  const [dirTwoPersonJob, setDirTwoPersonJob] = useState(false)
  const [dirTemperamentNotes, setDirTemperamentNotes] = useState('')
  const [dirSeniorFlag, setDirSeniorFlag] = useState(false)
  const [dirMobilityNotes, setDirMobilityNotes] = useState('')
  const [dirVetNotes, setDirVetNotes] = useState('')

  const [ownName, setOwnName] = useState('')
  const [ownPhone, setOwnPhone] = useState('')
  const [ownEmail, setOwnEmail] = useState('')
  const [ownLocale, setOwnLocale] = useState('de')
  const [ownAddressArea, setOwnAddressArea] = useState('')
  const [ownPreferredChannel, setOwnPreferredChannel] = useState('')
  const [ownClientSince, setOwnClientSince] = useState('')
  const [ownNotes, setOwnNotes] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const [dogs, breedRows] = await Promise.all([searchDogs(''), listBreeds()])
        setResults(dogs)
        setBreeds(breedRows)
      } catch (error) {
        console.error(error)
        setMessage(errorMessage(error))
      }
    })()
  }, [])

  function fillDirFormFromProfile(profile: DogProfile): void {
    setDirName(profile.name)
    setDirBreedId(profile.breed_id !== null ? String(profile.breed_id) : '')
    setDirSex(profile.sex ?? '')
    setDirWeightKg(
      profile.weight_kg !== null && profile.weight_kg !== undefined
        ? String(profile.weight_kg)
        : '',
    )
    setDirCoatType(profile.coat_type ?? '')
    setDirHairOrFur(profile.hair_or_fur ?? '')
    setDirCoatDensity(profile.coat_density ?? '')
    setDirUndercoat(profile.undercoat === true)
    setDirSheds(profile.sheds === true)
    setDirHandlingScore(
      profile.handling_score !== null ? String(profile.handling_score) : '',
    )
    setDirMuzzleRequired(profile.muzzle_required === true)
    setDirTwoPersonJob(profile.two_person_job === true)
    setDirTemperamentNotes(profile.temperament_notes ?? '')
    setDirSeniorFlag(profile.senior_flag === true)
    setDirMobilityNotes(profile.mobility_notes ?? '')
    setDirVetNotes(profile.vet_notes ?? '')
  }

  function fillOwnerFormFromProfile(profile: OwnerProfile): void {
    setOwnName(profile.name)
    setOwnPhone(profile.phone ?? '')
    setOwnEmail(profile.email ?? '')
    setOwnLocale(profile.locale || 'de')
    setOwnAddressArea(profile.address_area ?? '')
    setOwnPreferredChannel(profile.preferred_channel ?? '')
    setOwnClientSince(profile.client_since ?? '')
    setOwnNotes(profile.notes ?? '')
  }

  async function openDirectoryDog(dogId: number): Promise<void> {
    if (isBusy) return
    setIsBusy(true)
    setMessage('Loading…')
    try {
      const profile = await fetchDogProfile(dogId)
      fillDirFormFromProfile(profile)
      setDirectoryOwner(null)
      setDirectoryProfile(profile)
      setMessage('')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  async function openDirectoryOwner(ownerId: number): Promise<void> {
    if (isBusy) return
    setIsBusy(true)
    setMessage('Loading…')
    try {
      const profile = await fetchOwnerProfile(ownerId)
      fillOwnerFormFromProfile(profile)
      setDirectoryProfile(null)
      setDirectoryOwner(profile)
      setMessage('')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  function closeProfiles(): void {
    setDirectoryProfile(null)
    setDirectoryOwner(null)
    setMessage('')
  }

  async function saveDirectoryDog(): Promise<void> {
    if (directoryProfile === null || isBusy) return
    if (dirName.trim() === '') {
      setMessage('Dog name cannot be empty')
      return
    }
    setIsBusy(true)
    setMessage('Saving…')
    try {
      const body: Record<string, unknown> = {
        name: dirName.trim(),
        breed_id: dirBreedId.trim() === '' ? null : Number(dirBreedId),
        sex: dirSex.trim() === '' ? null : dirSex.trim(),
        weight_kg: dirWeightKg.trim() === '' ? null : Number(dirWeightKg),
        coat_type: dirCoatType.trim() === '' ? null : dirCoatType.trim(),
        hair_or_fur: dirHairOrFur.trim() === '' ? null : dirHairOrFur.trim(),
        coat_density: dirCoatDensity.trim() === '' ? null : dirCoatDensity.trim(),
        undercoat: dirUndercoat,
        sheds: dirSheds,
        handling_score:
          dirHandlingScore.trim() === '' ? null : Number(dirHandlingScore),
        muzzle_required: dirMuzzleRequired,
        two_person_job: dirTwoPersonJob,
        temperament_notes:
          dirTemperamentNotes.trim() === '' ? null : dirTemperamentNotes.trim(),
        senior_flag: dirSeniorFlag,
        mobility_notes:
          dirMobilityNotes.trim() === '' ? null : dirMobilityNotes.trim(),
        vet_notes: dirVetNotes.trim() === '' ? null : dirVetNotes.trim(),
      }
      const updated = await patchDog(directoryProfile.dog_id, body)
      fillDirFormFromProfile(updated)
      setDirectoryProfile(updated)
      setMessage('Saved')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  async function saveDirectoryOwner(): Promise<void> {
    if (directoryOwner === null || isBusy) return
    if (ownName.trim() === '') {
      setMessage('Owner name cannot be empty')
      return
    }
    setIsBusy(true)
    setMessage('Saving…')
    try {
      const body: Record<string, unknown> = {
        name: ownName.trim(),
        phone: ownPhone.trim() === '' ? null : ownPhone.trim(),
        email: ownEmail.trim() === '' ? null : ownEmail.trim(),
        locale: ownLocale.trim() === '' ? 'de' : ownLocale.trim(),
        address_area: ownAddressArea.trim() === '' ? null : ownAddressArea.trim(),
        preferred_channel:
          ownPreferredChannel.trim() === '' ? null : ownPreferredChannel.trim(),
        client_since: ownClientSince.trim() === '' ? null : ownClientSince.trim(),
        notes: ownNotes.trim() === '' ? null : ownNotes.trim(),
      }
      const updated = await patchOwner(directoryOwner.owner_id, body)
      fillOwnerFormFromProfile(updated)
      setDirectoryOwner(updated)
      setMessage('Saved')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  async function onAvatarPick(file: File): Promise<void> {
    if (directoryProfile === null || isBusy) return
    setIsBusy(true)
    setMessage('Uploading photo…')
    try {
      await uploadDogProfilePhoto(directoryProfile.dog_id, file)
      const profile = await fetchDogProfile(directoryProfile.dog_id)
      fillDirFormFromProfile(profile)
      setDirectoryProfile(profile)
      setMessage('Photo updated')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  if (directoryProfile !== null) {
    return (
      <>
        {message !== '' && (
          <p className="status" role="status">
            {message}
          </p>
        )}
        <section className="panel profile-panel">
          <header className="profile-hero">
            <DogAvatar
              photoId={directoryProfile.avatar_photo_id}
              name={directoryProfile.name}
              size="lg"
              disabled={isBusy}
              onPickFile={(file) => {
                void onAvatarPick(file)
              }}
            />
            <div className="profile-hero-text">
              <h2>{directoryProfile.name}</h2>
              <button
                type="button"
                className="linkish"
                disabled={isBusy}
                onClick={() => {
                  void openDirectoryOwner(directoryProfile.owner.owner_id)
                }}
              >
                {directoryProfile.owner.name}
                {directoryProfile.owner.phone
                  ? ` · ${directoryProfile.owner.phone}`
                  : ''}
              </button>
              <p className="step-meta">
                {directoryProfile.size_band ?? '—'} size
                {' · '}
                {directoryProfile.visit_count ?? 0}{' '}
                {(directoryProfile.visit_count ?? 0) === 1 ? 'visit' : 'visits'}
                {directoryProfile.last_visit_date
                  ? ` · last ${directoryProfile.last_visit_date}`
                  : ''}
              </p>
            </div>
          </header>

          <div className="profile-block">
            <h3 className="profile-section">Identity</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="dir_name">Name</label>
                <input
                  id="dir_name"
                  type="text"
                  value={dirName}
                  onChange={(e) => setDirName(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="dir_breed">Breed</label>
                <select
                  id="dir_breed"
                  value={dirBreedId}
                  onChange={(e) => setDirBreedId(e.target.value)}
                >
                  <option value="">—</option>
                  {breeds.map((b) => (
                    <option key={b.breed_id} value={b.breed_id}>
                      {breedLabel(b)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field-grid field-grid-compact">
                <div className="field">
                  <label htmlFor="dir_sex">Sex</label>
                  <select
                    id="dir_sex"
                    value={dirSex}
                    onChange={(e) => setDirSex(e.target.value)}
                  >
                    {SEX_OPTIONS.map((o) => (
                      <option key={o.value || 'empty'} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="dir_weight">Weight (kg)</label>
                  <input
                    id="dir_weight"
                    type="text"
                    inputMode="decimal"
                    value={dirWeightKg}
                    onChange={(e) => setDirWeightKg(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Coat</h3>
            <div className="field-stack">
            <div className="field-grid field-grid-compact">
              <div className="field">
                <label htmlFor="dir_coat_type">Type</label>
                <select
                  id="dir_coat_type"
                  value={dirCoatType}
                  onChange={(e) => setDirCoatType(e.target.value)}
                >
                  {COAT_TYPE_OPTIONS.map((o) => (
                    <option key={o.value || 'empty'} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="dir_hair_or_fur">Hair / fur</label>
                <select
                  id="dir_hair_or_fur"
                  value={dirHairOrFur}
                  onChange={(e) => setDirHairOrFur(e.target.value)}
                >
                  {HAIR_OR_FUR_OPTIONS.map((o) => (
                    <option key={o.value || 'empty'} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="dir_coat_density">Density</label>
                <select
                  id="dir_coat_density"
                  value={dirCoatDensity}
                  onChange={(e) => setDirCoatDensity(e.target.value)}
                >
                  {COAT_DENSITY_OPTIONS.map((o) => (
                    <option key={o.value || 'empty'} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="chip-row">
              <label className={`chip ${dirUndercoat ? 'chip-on' : ''}`}>
                <input
                  type="checkbox"
                  checked={dirUndercoat}
                  onChange={(e) => setDirUndercoat(e.target.checked)}
                />
                Undercoat
              </label>
              <label className={`chip ${dirSheds ? 'chip-on' : ''}`}>
                <input
                  type="checkbox"
                  checked={dirSheds}
                  onChange={(e) => setDirSheds(e.target.checked)}
                />
                Sheds
              </label>
            </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Handling</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="dir_handling">Handling score</label>
                <select
                  id="dir_handling"
                  value={dirHandlingScore}
                  onChange={(e) => setDirHandlingScore(e.target.value)}
                >
                  {HANDLING_OPTIONS.map((o) => (
                    <option key={o.value || 'empty'} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="chip-row">
                <label className={`chip ${dirMuzzleRequired ? 'chip-on' : ''}`}>
                  <input
                    type="checkbox"
                    checked={dirMuzzleRequired}
                    onChange={(e) => setDirMuzzleRequired(e.target.checked)}
                  />
                  Muzzle
                </label>
                <label className={`chip ${dirTwoPersonJob ? 'chip-on' : ''}`}>
                  <input
                    type="checkbox"
                    checked={dirTwoPersonJob}
                    onChange={(e) => setDirTwoPersonJob(e.target.checked)}
                  />
                  Two-person
                </label>
              </div>
              <div className="field">
                <label htmlFor="dir_temp_notes">Temperament notes</label>
                <textarea
                  id="dir_temp_notes"
                  rows={3}
                  value={dirTemperamentNotes}
                  onChange={(e) => setDirTemperamentNotes(e.target.value)}
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Medical</h3>
            <div className="field-stack">
              <div className="chip-row">
                <label className={`chip ${dirSeniorFlag ? 'chip-on' : ''}`}>
                  <input
                    type="checkbox"
                    checked={dirSeniorFlag}
                    onChange={(e) => setDirSeniorFlag(e.target.checked)}
                  />
                  Senior
                </label>
              </div>
              <div className="field">
                <label htmlFor="dir_mobility">Mobility notes</label>
                <textarea
                  id="dir_mobility"
                  rows={2}
                  value={dirMobilityNotes}
                  onChange={(e) => setDirMobilityNotes(e.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div className="field">
                <label htmlFor="dir_vet">Vet notes</label>
                <textarea
                  id="dir_vet"
                  rows={2}
                  value={dirVetNotes}
                  onChange={(e) => setDirVetNotes(e.target.value)}
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Recent visits</h3>
            {directoryProfile.recent_visits.length === 0 ? (
              <p className="step-meta">No visits yet.</p>
            ) : (
              <ul className="dir-visit-list">
                {directoryProfile.recent_visits.map((v) => (
                  <li key={v.visit_id}>
                    <span>
                      {v.visit_date} · {v.actual_minutes} min
                    </span>
                    <span className="step-meta">
                      condition {v.condition_score ?? '—'} · {v.status ?? '—'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="actions profile-actions">
            {onStartVisit !== undefined && (
              <button
                type="button"
                className="primary"
                disabled={isBusy}
                onClick={() => {
                  onStartVisit({
                    dog_id: directoryProfile.dog_id,
                    owner_id: directoryProfile.owner_id,
                    dog_name: directoryProfile.name,
                    owner_name: directoryProfile.owner.name,
                  })
                }}
              >
                Start visit
              </button>
            )}
            <button
              type="button"
              className={onStartVisit !== undefined ? undefined : 'primary'}
              disabled={isBusy}
              onClick={() => {
                void saveDirectoryDog()
              }}
            >
              Save
            </button>
            <button
              type="button"
              className="ghost"
              disabled={isBusy}
              onClick={closeProfiles}
            >
              Back
            </button>
          </div>
        </section>
      </>
    )
  }

  if (directoryOwner !== null) {
    return (
      <>
        {message !== '' && (
          <p className="status" role="status">
            {message}
          </p>
        )}
        <section className="panel profile-panel">
          <header className="profile-hero profile-hero-owner">
            <div className="dog-avatar dog-avatar-lg owner-avatar" aria-hidden>
              <span className="owner-avatar-initial">
                {(directoryOwner.name.trim()[0] || '?').toUpperCase()}
              </span>
            </div>
            <div className="profile-hero-text">
              <h2>{directoryOwner.name}</h2>
              <p className="step-meta">
                {directoryOwner.visit_count ?? 0} total{' '}
                {(directoryOwner.visit_count ?? 0) === 1 ? 'visit' : 'visits'}
                {directoryOwner.lifetime_value != null
                  ? ` · LTV ${directoryOwner.lifetime_value}`
                  : ''}
              </p>
            </div>
          </header>

          <div className="profile-block">
            <h3 className="profile-section">Identity</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="own_name">Name</label>
                <input
                  id="own_name"
                  type="text"
                  autoComplete="name"
                  value={ownName}
                  onChange={(e) => setOwnName(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="own_phone">Phone</label>
                <input
                  id="own_phone"
                  type="tel"
                  autoComplete="tel"
                  value={ownPhone}
                  onChange={(e) => setOwnPhone(e.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div className="field">
                <label htmlFor="own_email">Email</label>
                <input
                  id="own_email"
                  type="email"
                  autoComplete="email"
                  value={ownEmail}
                  onChange={(e) => setOwnEmail(e.target.value)}
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Preferences</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="own_channel">Preferred channel</label>
                <input
                  id="own_channel"
                  type="text"
                  value={ownPreferredChannel}
                  onChange={(e) => setOwnPreferredChannel(e.target.value)}
                  placeholder="WhatsApp, phone…"
                />
              </div>
              <div className="field">
                <label htmlFor="own_area">Address area</label>
                <input
                  id="own_area"
                  type="text"
                  value={ownAddressArea}
                  onChange={(e) => setOwnAddressArea(e.target.value)}
                  placeholder="Optional"
                />
              </div>
              <div className="field">
                <label htmlFor="own_locale">Locale</label>
                <input
                  id="own_locale"
                  type="text"
                  value={ownLocale}
                  onChange={(e) => setOwnLocale(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="own_since">Client since</label>
                <input
                  id="own_since"
                  type="date"
                  value={ownClientSince}
                  onChange={(e) => setOwnClientSince(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Notes</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="own_notes" className="visually-hidden">
                  Notes
                </label>
                <textarea
                  id="own_notes"
                  rows={3}
                  value={ownNotes}
                  onChange={(e) => setOwnNotes(e.target.value)}
                  placeholder="Optional notes"
                />
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Dogs</h3>
            {directoryOwner.dogs.length === 0 ? (
              <p className="step-meta">No dogs on this owner.</p>
            ) : (
              <ul className="dir-card-list">
                {directoryOwner.dogs.map((d) => (
                  <li key={d.dog_id}>
                    <button
                      type="button"
                      className="dir-card"
                      disabled={isBusy}
                      onClick={() => {
                        void openDirectoryDog(d.dog_id)
                      }}
                    >
                      <DogAvatar photoId={null} name={d.name} />
                      <div className="dir-card-body">
                        <span className="dir-card-title">{d.name}</span>
                        <span className="dir-card-meta">Open profile</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="actions profile-actions">
            <button
              type="button"
              className="primary"
              disabled={isBusy}
              onClick={() => {
                void saveDirectoryOwner()
              }}
            >
              Save
            </button>
            <button
              type="button"
              className="ghost"
              disabled={isBusy}
              onClick={closeProfiles}
            >
              Back
            </button>
          </div>
        </section>
      </>
    )
  }

  return (
    <>
      {message !== '' && (
        <p className="status" role="status">
          {message}
        </p>
      )}
      <section className="panel home-panel">
        <div className="search-bar">
          <label className="visually-hidden" htmlFor="directory_dog_search">
            Search clients
          </label>
          <input
            id="directory_dog_search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search dogs or owners…"
            autoComplete="off"
          />
        </div>
        {filtered.length === 0 ? (
          <p className="step-meta empty-state">
            {results.length === 0
              ? 'No clients yet — tap + to start a visit.'
              : 'No matches.'}
          </p>
        ) : (
          <ul className="dir-card-list">
            {filtered.map((dog) => (
              <li key={dog.dog_id}>
                <div className="dir-card dir-card-split">
                  <button
                    type="button"
                    className="dir-card-main"
                    disabled={isBusy}
                    onClick={() => {
                      void openDirectoryDog(dog.dog_id)
                    }}
                  >
                    <DogAvatar photoId={null} name={dog.name} />
                    <div className="dir-card-body">
                      <span className="dir-card-title">{dog.name}</span>
                      <span className="dir-card-meta">
                        {dog.owner_name}
                        {dog.last_visit_date
                          ? ` · ${dog.last_visit_date}`
                          : ''}
                      </span>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="dir-card-owner"
                    disabled={isBusy}
                    onClick={() => {
                      void openDirectoryOwner(dog.owner_id)
                    }}
                  >
                    Owner
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
