import { useState } from 'react'
import {
  errorMessage,
  fetchDogProfile,
  patchDog,
  uploadDogProfilePhoto,
  type BreedListItem,
  type DogProfile,
} from './api'
import { BreedPicker } from './BreedPicker'
import { DogAvatar } from './DogAvatar'
import type { SelectedDog } from './draft'
import { VisitEditView } from './VisitEditView'

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

/** Editable fields, as the inputs hold them (strings for selects/text). */
type DogForm = {
  name: string
  breedId: string
  breedSecondaryId: string
  sex: string
  weightKg: string
  coatType: string
  hairOrFur: string
  coatDensity: string
  undercoat: boolean
  sheds: boolean
  handlingScore: string
  muzzleRequired: boolean
  twoPersonJob: boolean
  temperamentNotes: string
  seniorFlag: boolean
  mobilityNotes: string
  vetNotes: string
}

function formFromProfile(p: DogProfile): DogForm {
  return {
    name: p.name,
    breedId: p.breed_id !== null ? String(p.breed_id) : '',
    breedSecondaryId: p.breed_secondary_id !== null ? String(p.breed_secondary_id) : '',
    sex: p.sex ?? '',
    weightKg: p.weight_kg != null ? String(p.weight_kg) : '',
    coatType: p.coat_type ?? '',
    hairOrFur: p.hair_or_fur ?? '',
    coatDensity: p.coat_density ?? '',
    undercoat: p.undercoat === true,
    sheds: p.sheds === true,
    handlingScore: p.handling_score !== null ? String(p.handling_score) : '',
    muzzleRequired: p.muzzle_required === true,
    twoPersonJob: p.two_person_job === true,
    temperamentNotes: p.temperament_notes ?? '',
    seniorFlag: p.senior_flag === true,
    mobilityNotes: p.mobility_notes ?? '',
    vetNotes: p.vet_notes ?? '',
  }
}

/** Trimmed text, or null when empty (PATCH clears the field). */
function textOrNull(s: string): string | null {
  const t = s.trim()
  return t === '' ? null : t
}

function numberOrNull(s: string): number | null {
  return s.trim() === '' ? null : Number(s)
}

/** "16 Oct 2026" — readable on the profile list (ISO stays in the API). */
function formatVisitDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatVisitStatus(status: string | null): string {
  if (status === null || status === '') return 'No status'
  if (status === 'no_show') return 'No-show'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatCoatCondition(score: number | null): string {
  if (score === null) return 'Coat —'
  return `Coat ${score}`
}

type DogProfileViewProps = {
  profile: DogProfile
  breeds: BreedListItem[]
  onBack: () => void
  onOpenOwner: (ownerId: number) => void
  onStartVisit?: (dog: SelectedDog) => void
  /** After a save, so the client list can refresh names. */
  onSaved: () => void
}

/** One dog's profile: read, safe PATCH (#131/#132), avatar upload. */
export function DogProfileView({
  profile: initial,
  breeds,
  onBack,
  onOpenOwner,
  onStartVisit,
  onSaved,
}: DogProfileViewProps) {
  const [profile, setProfile] = useState(initial)
  const [form, setForm] = useState(() => formFromProfile(initial))
  const [isBusy, setIsBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [editingVisitId, setEditingVisitId] = useState<number | null>(null)

  function set<K extends keyof DogForm>(key: K, value: DogForm[K]): void {
    setForm((f) => ({ ...f, [key]: value }))
  }

  function show(updated: DogProfile): void {
    setProfile(updated)
    setForm(formFromProfile(updated))
  }

  async function reloadAfterVisitChange(): Promise<void> {
    setEditingVisitId(null)
    try {
      const updated = await fetchDogProfile(profile.dog_id)
      show(updated)
      onSaved()
    } catch (err) {
      setMessage(errorMessage(err))
    }
  }

  if (editingVisitId !== null) {
    return (
      <VisitEditView
        visitId={editingVisitId}
        dogName={profile.name}
        onBack={() => setEditingVisitId(null)}
        onDone={() => {
          void reloadAfterVisitChange()
        }}
      />
    )
  }

  async function save(): Promise<void> {
    if (isBusy) return
    if (form.name.trim() === '') {
      setMessage('Dog name cannot be empty')
      return
    }
    const weightKg = parseWeightKg(form.weightKg)
    if (weightKg === 'invalid') {
      setMessage('Weight must be a number in kg, e.g. 7,5')
      return
    }
    setIsBusy(true)
    setMessage('Saving…')
    try {
      show(
        await patchDog(profile.dog_id, {
          name: form.name.trim(),
          breed_id: numberOrNull(form.breedId),
          breed_secondary_id: numberOrNull(form.breedSecondaryId),
          sex: textOrNull(form.sex),
          weight_kg: weightKg,
          coat_type: textOrNull(form.coatType),
          hair_or_fur: textOrNull(form.hairOrFur),
          coat_density: textOrNull(form.coatDensity),
          undercoat: form.undercoat,
          sheds: form.sheds,
          handling_score: numberOrNull(form.handlingScore),
          muzzle_required: form.muzzleRequired,
          two_person_job: form.twoPersonJob,
          temperament_notes: textOrNull(form.temperamentNotes),
          senior_flag: form.seniorFlag,
          mobility_notes: textOrNull(form.mobilityNotes),
          vet_notes: textOrNull(form.vetNotes),
        }),
      )
      setMessage('Saved')
      onSaved()
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  async function onAvatarPick(file: File): Promise<void> {
    if (isBusy) return
    setIsBusy(true)
    setMessage('Uploading photo…')
    try {
      await uploadDogProfilePhoto(profile.dog_id, file)
      show(await fetchDogProfile(profile.dog_id))
      setMessage('Photo updated')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

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
            photoId={profile.avatar_photo_id}
            name={profile.name}
            size="lg"
            disabled={isBusy}
            onPickFile={(file) => {
              void onAvatarPick(file)
            }}
          />
          <div className="profile-hero-text">
            <h2>{profile.name}</h2>
            <button
              type="button"
              className="linkish"
              disabled={isBusy}
              onClick={() => {
                onOpenOwner(profile.owner.owner_id)
              }}
            >
              {profile.owner.name}
              {profile.owner.phone
                ? ` · ${profile.owner.phone}`
                : ''}
            </button>
            <p className="step-meta">
              {profile.size_band ?? '—'} size
              {' · '}
              {profile.visit_count ?? 0}{' '}
              {(profile.visit_count ?? 0) === 1 ? 'visit' : 'visits'}
              {profile.last_visit_date
                ? ` · last ${profile.last_visit_date}`
                : ''}
            </p>
          </div>
        </header>

        <form
          id="dog-profile-form"
          className="section-grid profile-sections"
          onSubmit={(e) => {
            e.preventDefault()
            void save()
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
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
              />
            </div>
            <BreedPicker
              id="dir_breed"
              label="Breed"
              breeds={breeds}
              value={form.breedId}
              onChange={(v) => set('breedId', v)}
              disabled={isBusy}
            />
            <BreedPicker
              id="dir_breed_secondary"
              label="Secondary breed (optional)"
              breeds={breeds}
              value={form.breedSecondaryId}
              onChange={(v) => set('breedSecondaryId', v)}
              disabled={isBusy}
            />
            <div className="field-grid field-grid-compact">
              <div className="field">
                <label htmlFor="dir_sex">Sex</label>
                <select
                  id="dir_sex"
                  value={form.sex}
                  onChange={(e) => set('sex', e.target.value)}
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
                  value={form.weightKg}
                  onChange={(e) => set('weightKg', e.target.value)}
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
                value={form.coatType}
                onChange={(e) => set('coatType', e.target.value)}
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
                value={form.hairOrFur}
                onChange={(e) => set('hairOrFur', e.target.value)}
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
                value={form.coatDensity}
                onChange={(e) => set('coatDensity', e.target.value)}
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
            <label className={`chip ${form.undercoat ? 'chip-on' : ''}`}>
              <input
                type="checkbox"
                checked={form.undercoat}
                onChange={(e) => set('undercoat', e.target.checked)}
              />
              Undercoat
            </label>
            <label className={`chip ${form.sheds ? 'chip-on' : ''}`}>
              <input
                type="checkbox"
                checked={form.sheds}
                onChange={(e) => set('sheds', e.target.checked)}
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
                value={form.handlingScore}
                onChange={(e) => set('handlingScore', e.target.value)}
              >
                {HANDLING_OPTIONS.map((o) => (
                  <option key={o.value || 'empty'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="chip-row">
              <label className={`chip ${form.muzzleRequired ? 'chip-on' : ''}`}>
                <input
                  type="checkbox"
                  checked={form.muzzleRequired}
                  onChange={(e) => set('muzzleRequired', e.target.checked)}
                />
                Muzzle
              </label>
              <label className={`chip ${form.twoPersonJob ? 'chip-on' : ''}`}>
                <input
                  type="checkbox"
                  checked={form.twoPersonJob}
                  onChange={(e) => set('twoPersonJob', e.target.checked)}
                />
                Two-person
              </label>
            </div>
            <div className="field">
              <label htmlFor="dir_temp_notes">Temperament notes</label>
              <textarea
                id="dir_temp_notes"
                rows={3}
                value={form.temperamentNotes}
                onChange={(e) => set('temperamentNotes', e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>
        </div>

        <div className="profile-block">
          <h3 className="profile-section">Medical</h3>
          <div className="field-stack">
            <div className="chip-row">
              <label className={`chip ${form.seniorFlag ? 'chip-on' : ''}`}>
                <input
                  type="checkbox"
                  checked={form.seniorFlag}
                  onChange={(e) => set('seniorFlag', e.target.checked)}
                />
                Senior
              </label>
            </div>
            <div className="field">
              <label htmlFor="dir_mobility">Mobility notes</label>
              <textarea
                id="dir_mobility"
                rows={2}
                value={form.mobilityNotes}
                onChange={(e) => set('mobilityNotes', e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="field">
              <label htmlFor="dir_vet">Vet notes</label>
              <textarea
                id="dir_vet"
                rows={2}
                value={form.vetNotes}
                onChange={(e) => set('vetNotes', e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>
        </div>

        <div className="profile-block">
          <h3 className="profile-section">Recent visits</h3>
          {profile.recent_visits.length === 0 ? (
            <p className="step-meta">No visits yet.</p>
          ) : (
            <ul className="dir-visit-list">
              {profile.recent_visits.map((v) => (
                <li key={v.visit_id}>
                  <button
                    type="button"
                    className="dir-visit-row"
                    disabled={isBusy}
                    onClick={() => setEditingVisitId(v.visit_id)}
                    aria-label={`Edit visit on ${formatVisitDate(v.visit_date)}, ${v.actual_minutes} minutes`}
                  >
                    <span className="dir-visit-main">
                      <span className="dir-visit-date">
                        {formatVisitDate(v.visit_date)}
                      </span>
                      <span className="dir-visit-duration">
                        {v.actual_minutes} min
                      </span>
                    </span>
                    <span className="dir-visit-meta">
                      <span>{formatCoatCondition(v.condition_score)}</span>
                      <span className="dir-visit-dot" aria-hidden>
                        ·
                      </span>
                      <span>{formatVisitStatus(v.status)}</span>
                      <span className="dir-visit-edit">Edit</span>
                    </span>
                  </button>
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
                  dog_id: profile.dog_id,
                  owner_id: profile.owner_id,
                  dog_name: profile.name,
                  owner_name: profile.owner.name,
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
            onClick={onBack}
          >
            Back
          </button>
        </div>
      </section>
    </>
  )
}
