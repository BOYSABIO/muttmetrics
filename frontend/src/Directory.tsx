import { useEffect, useMemo, useState } from 'react'
import {
  errorMessage,
  fetchDogProfile,
  fetchOwnerProfile,
  listBreeds,
  patchDog,
  patchOwner,
  searchDogs,
  uploadDogProfilePhoto,
  type BreedListItem,
  type DogProfile,
  type DogSearchItem,
  type OwnerProfile,
} from './api'
import { BreedPicker } from './BreedPicker'
import { formatLastVisit } from './dates'
import { DogAvatar } from './DogAvatar'

export type VisitDogRef = {
  dog_id: number
  owner_id: number
  dog_name: string
  owner_name: string
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

/**
 * Weight field → kg for the API. A German keypad types "7,5", and
 * Number("7,5") is NaN, which JSON turns into null and silently wipes the
 * weight. Accept the comma; refuse anything that still isn't a number.
 */
function parseWeightKg(raw: string): number | null | 'invalid' {
  const cleaned = raw.trim().replace(',', '.')
  if (cleaned === '') return null
  const kg = Number(cleaned)
  return Number.isFinite(kg) && kg > 0 ? kg : 'invalid'
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
  // Kept apart so the list never says "No clients yet" while it is loading
  // or after a failed load.
  const [listStatus, setListStatus] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )

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
  const [dirBreedSecondaryId, setDirBreedSecondaryId] = useState('')
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
        setListStatus('ready')
      } catch (error) {
        console.error(error)
        setListStatus('error')
        setMessage(errorMessage(error))
      }
    })()
  }, [])

  /** Reload the client list, e.g. after a rename, so Back shows fresh rows. */
  async function refreshList(): Promise<void> {
    try {
      setResults(await searchDogs(''))
      setListStatus('ready')
    } catch (error) {
      console.error(error)
      setListStatus('error')
    }
  }

  function fillDirFormFromProfile(profile: DogProfile): void {
    setDirName(profile.name)
    setDirBreedId(profile.breed_id !== null ? String(profile.breed_id) : '')
    setDirBreedSecondaryId(
      profile.breed_secondary_id !== null
        ? String(profile.breed_secondary_id)
        : '',
    )
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
    const weightKg = parseWeightKg(dirWeightKg)
    if (weightKg === 'invalid') {
      setMessage('Weight must be a number in kg, e.g. 7,5')
      return
    }
    setIsBusy(true)
    setMessage('Saving…')
    try {
      const body: Record<string, unknown> = {
        name: dirName.trim(),
        breed_id: dirBreedId.trim() === '' ? null : Number(dirBreedId),
        breed_secondary_id:
          dirBreedSecondaryId.trim() === ''
            ? null
            : Number(dirBreedSecondaryId),
        sex: dirSex.trim() === '' ? null : dirSex.trim(),
        weight_kg: weightKg,
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
      void refreshList()
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
      void refreshList()
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

          <form
            id="dog-profile-form"
            className="section-grid profile-sections"
            onSubmit={(e) => {
              e.preventDefault()
              void saveDirectoryDog()
            }}
          >
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
              <BreedPicker
                id="dir_breed"
                label="Breed"
                breeds={breeds}
                value={dirBreedId}
                onChange={setDirBreedId}
                disabled={isBusy}
              />
              <BreedPicker
                id="dir_breed_secondary"
                label="Secondary breed (optional)"
                breeds={breeds}
                value={dirBreedSecondaryId}
                onChange={setDirBreedSecondaryId}
                disabled={isBusy}
              />
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
          </form>

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
              type="submit"
              form="dog-profile-form"
              className={onStartVisit !== undefined ? undefined : 'primary'}
              disabled={isBusy}
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

          <form
            id="owner-profile-form"
            className="section-grid profile-sections"
            onSubmit={(e) => {
              e.preventDefault()
              void saveDirectoryOwner()
            }}
          >
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
          </form>

          <div className="actions profile-actions">
            <button
              type="submit"
              form="owner-profile-form"
              className="primary"
              disabled={isBusy}
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
        {listStatus === 'loading' ? (
          <p className="step-meta empty-state">Loading clients…</p>
        ) : listStatus === 'error' && results.length === 0 ? (
          <div className="empty-state">
            <p className="step-meta">Could not load clients.</p>
            <button
              type="button"
              className="ghost"
              onClick={() => {
                setListStatus('loading')
                setMessage('')
                void refreshList()
              }}
            >
              Try again
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <p className="step-meta empty-state">
            {results.length === 0
              ? 'No clients yet — tap + to start a visit.'
              : 'No matches.'}
          </p>
        ) : (
          <>
            <div className="client-list-head" aria-hidden>
              <span>
                {filtered.length} {filtered.length === 1 ? 'dog' : 'dogs'}
              </span>
              <span>Last visit</span>
            </div>
            <ul className="dir-card-list client-list">
              {filtered.map((dog) => (
                <li key={dog.dog_id}>
                  {/* The whole row opens the dog. The name button keeps it
                      reachable by keyboard; its click bubbles up to here. */}
                  <div
                    className="dir-card dir-card-row client-row"
                    onClick={() => {
                      if (!isBusy) void openDirectoryDog(dog.dog_id)
                    }}
                  >
                    <button
                      type="button"
                      className="dir-card-avatar-hit"
                      disabled={isBusy}
                      aria-label={`Open ${dog.name}`}
                      tabIndex={-1}
                    >
                      <DogAvatar photoId={null} name={dog.name} />
                    </button>
                    <div className="dir-card-body">
                      <button
                        type="button"
                        className="dir-card-title-btn"
                        disabled={isBusy}
                      >
                        {dog.name}
                      </button>
                      <div className="dir-card-meta">
                        <button
                          type="button"
                          className="linkish"
                          disabled={isBusy}
                          onClick={(e) => {
                            e.stopPropagation()
                            void openDirectoryOwner(dog.owner_id)
                          }}
                        >
                          {dog.owner_name}
                        </button>
                      </div>
                    </div>
                    <span
                      className="client-last"
                      title={dog.last_visit_date ?? 'No visit date recorded'}
                    >
                      {formatLastVisit(dog.last_visit_date)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  )
}
