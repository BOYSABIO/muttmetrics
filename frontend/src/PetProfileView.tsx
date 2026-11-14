import { useRef, useState } from 'react'
import {
  errorMessage,
  fetchPetProfile,
  patchPet,
  uploadPetProfilePhoto,
  type BreedListItem,
  type PetProfile,
  type Species,
} from './api'
import { BreedPicker } from './BreedPicker'
import { PetAvatar } from './PetAvatar'
import type { SelectedPet } from './draft'
import { SpeciesChips } from './SpeciesChips'
import { VisitEditView } from './VisitEditView'
import { conditionWord } from './condition'
import { PageBack } from './PageBack'
import { ChoiceChips, YesNo } from './ChoiceChips'
import {
  COAT_THICKNESS,
  COAT_TYPES,
  HANDLING,
  SEXES,
  SIZES,
  coatTypeLabel,
  handlingLabel,
  sizeLabel,
} from './petVocab'

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

/**
 * Editable fields, as the inputs hold them (strings for selects/text).
 * Yes/no fields keep null ("nobody checked") until someone taps them.
 */
type DogForm = {
  name: string
  species: Species
  breedId: string
  breedSecondaryId: string
  sex: string
  weightKg: string
  sizeBand: string
  coatType: string
  coatThickness: string
  usualCut: string
  handlingScore: string
  muzzleRequired: boolean | null
  twoPersonJob: boolean | null
  temperamentNotes: string
  seniorFlag: boolean | null
  healthNotes: string
}

function formFromProfile(p: PetProfile): DogForm {
  return {
    name: p.name,
    species: p.species,
    breedId: p.breed_id !== null ? String(p.breed_id) : '',
    breedSecondaryId: p.breed_secondary_id !== null ? String(p.breed_secondary_id) : '',
    sex: p.sex ?? '',
    weightKg: p.weight_kg != null ? String(p.weight_kg) : '',
    sizeBand: p.size_band ?? '',
    coatType: p.coat_type ?? '',
    coatThickness: p.coat_thickness !== null ? String(p.coat_thickness) : '',
    usualCut: p.usual_cut ?? '',
    handlingScore: p.handling_score !== null ? String(p.handling_score) : '',
    muzzleRequired: p.muzzle_required,
    twoPersonJob: p.two_person_job,
    temperamentNotes: p.temperament_notes ?? '',
    seniorFlag: p.senior_flag,
    healthNotes: p.health_notes ?? '',
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

/** The PATCH body a form stands for (weight already parsed). */
function payloadFromForm(f: DogForm, weightKg: number | null): Record<string, unknown> {
  return {
    name: f.name.trim(),
    species: f.species,
    breed_id: numberOrNull(f.breedId),
    breed_secondary_id: numberOrNull(f.breedSecondaryId),
    sex: textOrNull(f.sex),
    weight_kg: weightKg,
    size_band: textOrNull(f.sizeBand),
    coat_type: textOrNull(f.coatType),
    coat_thickness: numberOrNull(f.coatThickness),
    usual_cut: textOrNull(f.usualCut),
    handling_score: numberOrNull(f.handlingScore),
    muzzle_required: f.muzzleRequired,
    two_person_job: f.twoPersonJob,
    temperament_notes: textOrNull(f.temperamentNotes),
    senior_flag: f.seniorFlag,
    health_notes: textOrNull(f.healthNotes),
  }
}

/**
 * Only the fields that differ from what was loaded. Saving one field never
 * rewrites the others, so blank stays blank and the change log only gets
 * real changes (docs/architecture/pet-data.md).
 */
function changedFields(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(after)) {
    if (before[key] !== value) out[key] = value
  }
  return out
}

function weightOf(p: PetProfile): number | null {
  return p.weight_kg != null ? Number(p.weight_kg) : null
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
  return score === null ? '—' : conditionWord(score)
}

/** "2 visits · last 3 wk ago" */
function visitsLine(count: number, last: string | null): string {
  const visits = `${count} ${count === 1 ? 'visit' : 'visits'}`
  if (last === null) return visits
  const [y, m, d] = last.split('-').map(Number)
  const days = Math.round((Date.now() - new Date(y, m - 1, d).getTime()) / 86_400_000)
  const ago =
    days <= 0
      ? 'today'
      : days === 1
        ? 'yesterday'
        : days < 14
          ? `${days} days ago`
          : days < 60
            ? `${Math.round(days / 7)} wk ago`
            : `${Math.round(days / 30)} mo ago`
  return `${visits} · last ${ago}`
}

type PetProfileViewProps = {
  profile: PetProfile
  breeds: BreedListItem[]
  onBack: () => void
  onOpenOwner: (ownerId: number) => void
  onStartVisit?: (dog: SelectedPet) => void
  /** After a save, so the client list can refresh names. */
  onSaved: () => void
  /** Add a breed the catalog lacks; the parent keeps the breed list. */
  onAddBreed?: (species: Species, name: string) => Promise<BreedListItem>
}

/** One dog's profile: read, safe PATCH (#131/#132), avatar upload. */
export function PetProfileView({
  profile: initial,
  breeds,
  onBack,
  onOpenOwner,
  onStartVisit,
  onSaved,
  onAddBreed,
}: PetProfileViewProps) {
  const [profile, setProfile] = useState(initial)
  const [form, setForm] = useState(() => formFromProfile(initial))
  const [isBusy, setIsBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [editingVisitId, setEditingVisitId] = useState<number | null>(null)
  const moreRef = useRef<HTMLDetailsElement>(null)

  function set<K extends keyof DogForm>(key: K, value: DogForm[K]): void {
    setForm((f) => ({ ...f, [key]: value }))
  }

  const addBreed =
    onAddBreed === undefined
      ? undefined
      : async (name: string): Promise<BreedListItem> => {
          try {
            const breed = await onAddBreed(form.species, name)
            setMessage(
              breed.source === 'salon' && breed.name_en !== null
                ? `Added ${breed.name_en}. Save to keep it on ${form.name || 'this pet'}.`
                : `Picked ${breed.name_en ?? 'the existing breed'}. Save to keep it.`,
            )
            return breed
          } catch (error) {
            setMessage(errorMessage(error))
            throw error
          }
        }

  function show(updated: PetProfile): void {
    setProfile(updated)
    setForm(formFromProfile(updated))
  }

  async function reloadAfterVisitChange(): Promise<void> {
    setEditingVisitId(null)
    try {
      const updated = await fetchPetProfile(profile.pet_id)
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
        petName={profile.name}
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
      setMessage('Pet name cannot be empty')
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
      const changes = changedFields(
        payloadFromForm(formFromProfile(profile), weightOf(profile)),
        payloadFromForm(form, weightKg),
      )
      if (Object.keys(changes).length === 0) {
        setMessage('Nothing changed')
        return
      }
      show(await patchPet(profile.pet_id, changes))
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
      await uploadPetProfilePhoto(profile.pet_id, file)
      show(await fetchPetProfile(profile.pet_id))
      setMessage('Photo updated')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  const weightTyped = form.weightKg.trim() !== ''
  const parsedWeight = parseWeightKg(form.weightKg)
  const dirty =
    parsedWeight === 'invalid' ||
    Object.keys(
      changedFields(
        payloadFromForm(formFromProfile(profile), weightOf(profile)),
        payloadFromForm(form, parsedWeight),
      ),
    ).length > 0

  // The four facts the estimate (and later the model) leans on most.
  const basicsFilled = [
    form.breedId !== '',
    weightTyped || form.sizeBand !== '',
    form.coatType !== '',
    form.handlingScore !== '',
  ].filter(Boolean).length

  const breedName =
    breeds.find((b) => String(b.breed_id) === String(profile.breed_id ?? ''))?.name_en ?? null
  const summary = [
    breedName,
    sizeLabel(profile.size_band),
    coatTypeLabel(profile.species, profile.coat_type),
    handlingLabel(profile.handling_score),
  ].filter((x): x is string => x !== null)
  const flags = [
    profile.muzzle_required === true ? 'Muzzle' : null,
    profile.two_person_job === true ? 'Two people' : null,
    profile.senior_flag === true ? 'Senior' : null,
    profile.health_notes ? 'Health note' : null,
  ].filter((x): x is string => x !== null)

  const coatHint = COAT_TYPES[form.species].find((o) => o.value === form.coatType)?.hint

  const weightChanged =
    weightTyped && (parsedWeight === 'invalid' || parsedWeight !== weightOf(profile))

  /** "Change" next to a size from the weight: open More details at the weight. */
  function openWeight(): void {
    if (moreRef.current) moreRef.current.open = true
    requestAnimationFrame(() => {
      const input = document.getElementById('dir_weight')
      input?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      input?.focus({ preventScroll: true })
    })
  }

  function leave(): void {
    if (dirty && !window.confirm('Leave without saving your changes?')) return
    onBack()
  }

  return (
    <>
      {message !== '' && (
        <p className="status" role="status">
          {message}
        </p>
      )}
      <section className="panel profile-panel">
        <PageBack onClick={leave} disabled={isBusy} />
        <header className="profile-hero">
          <PetAvatar
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
              {profile.owner.phone ? ` · ${profile.owner.phone}` : ''}
            </button>
            <p className="profile-summary">
              {summary.length > 0 ? summary.join(' · ') : 'No basics yet'}
            </p>
            <p className="step-meta">
              {visitsLine(profile.visit_count ?? 0, profile.last_visit_date)}
            </p>
            {flags.length > 0 && (
              <ul className="profile-flags" aria-label="Heads-up">
                {flags.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            )}
          </div>
          {onStartVisit !== undefined && (
            <button
              type="button"
              className="primary profile-hero-action"
              disabled={isBusy}
              onClick={() => {
                onStartVisit({
                  pet_id: profile.pet_id,
                  owner_id: profile.owner_id,
                  pet_name: profile.name,
                  owner_name: profile.owner.name,
                  species: profile.species,
                })
              }}
            >
              Start visit
            </button>
          )}
        </header>

        <form
          id="dog-profile-form"
          className="profile-layout"
          onSubmit={(e) => {
            e.preventDefault()
            void save()
          }}
        >
          <div className="profile-col">
            <div className="profile-block profile-basics">
              <div className="profile-block-head">
                <h3 className="profile-section">Basics</h3>
                <span
                  className={`basics-count ${basicsFilled === 4 ? 'basics-count-done' : ''}`}
                >
                  {basicsFilled} of 4
                </span>
              </div>
              {basicsFilled < 4 && (
                <p className="step-meta">Each one makes the time estimate better.</p>
              )}
              <div className="field-stack">
                <BreedPicker
                  id="dir_breed"
                  label="Breed"
                  breeds={breeds.filter((b) => b.species === form.species)}
                  value={form.breedId}
                  onChange={(v) => set('breedId', v)}
                  onAdd={addBreed}
                  disabled={isBusy}
                />
                {weightTyped ? (
                  <div className="field">
                    <span className="field-label">Size</span>
                    <div className="size-from-weight">
                      <span className="chip chip-on chip-static">
                        {weightChanged ? '—' : (sizeLabel(profile.size_band) ?? '—')}
                      </span>
                      <span className="step-meta">
                        {weightChanged
                          ? 'From the weight, on save'
                          : `From ${form.weightKg.trim()} kg`}
                      </span>
                      <button type="button" className="linkish" onClick={openWeight}>
                        Change
                      </button>
                    </div>
                  </div>
                ) : (
                  <ChoiceChips
                    id="dir_size"
                    label="Size"
                    columns={4}
                    options={SIZES}
                    value={form.sizeBand}
                    onChange={(v) => set('sizeBand', v)}
                    disabled={isBusy}
                    note={
                      form.sizeBand === ''
                        ? 'By eye is fine; a weight sets it exactly.'
                        : sizeLabel(form.sizeBand) ?? undefined
                    }
                  />
                )}
                <ChoiceChips
                  id="dir_coat_type"
                  label="Coat"
                  columns={2}
                  options={COAT_TYPES[form.species]}
                  value={form.coatType}
                  onChange={(v) => set('coatType', v)}
                  disabled={isBusy}
                  note={coatHint}
                />
                <ChoiceChips
                  id="dir_handling"
                  label="Handling"
                  options={HANDLING}
                  value={form.handlingScore}
                  onChange={(v) => set('handlingScore', v)}
                  disabled={isBusy}
                />
              </div>
            </div>

            <div className="profile-block">
              <h3 className="profile-section">Grooming notes</h3>
              <div className="field-stack">
                <div className="field">
                  <label htmlFor="dir_usual_cut">Usual cut</label>
                  <textarea
                    id="dir_usual_cut"
                    rows={2}
                    value={form.usualCut}
                    onChange={(e) => set('usualCut', e.target.value)}
                    placeholder="e.g. teddy face, 1 cm body, tidy feet"
                  />
                </div>
                <ChoiceChips
                  id="dir_coat_thickness"
                  label="Coat thickness (optional)"
                  columns={3}
                  options={COAT_THICKNESS}
                  value={form.coatThickness}
                  onChange={(v) => set('coatThickness', v)}
                  disabled={isBusy}
                />
                <div className="field">
                  <label htmlFor="dir_temp_notes">Temperament</label>
                  <textarea
                    id="dir_temp_notes"
                    rows={2}
                    value={form.temperamentNotes}
                    onChange={(e) => set('temperamentNotes', e.target.value)}
                    placeholder="e.g. hates the dryer, fine with nails"
                  />
                </div>
                <div className="field">
                  <label htmlFor="dir_health">Health</label>
                  <textarea
                    id="dir_health"
                    rows={2}
                    value={form.healthNotes}
                    onChange={(e) => set('healthNotes', e.target.value)}
                    placeholder="Mobility, skin, allergies, vet…"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="profile-col">
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
                          <span className="dir-visit-date">{formatVisitDate(v.visit_date)}</span>
                          <span className="dir-visit-duration">{v.actual_minutes} min</span>
                        </span>
                        <span className="dir-visit-meta">
                          <span>{formatCoatCondition(v.condition_score)}</span>
                          <span className="dir-visit-dot" aria-hidden>
                            ·
                          </span>
                          <span>{formatVisitStatus(v.status)}</span>
                          {(v.add_ons?.length ?? 0) > 0 && (
                            <>
                              <span className="dir-visit-dot" aria-hidden>
                                ·
                              </span>
                              <span>{v.add_ons.map((a) => a.name_en ?? a.slug).join(', ')}</span>
                            </>
                          )}
                          <span className="dir-visit-edit">Edit</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <details ref={moreRef} className="profile-block profile-more">
              <summary>
                <span className="profile-section">More details</span>
                <span className="step-meta">Name, species, mix, weight, sex, safety</span>
              </summary>
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
                <SpeciesChips
                  name="dir_species"
                  value={form.species}
                  disabled={isBusy}
                  onChange={(next) => {
                    setForm((f) => {
                      const breedOk = breeds.some(
                        (b) => String(b.breed_id) === f.breedId && b.species === next,
                      )
                      const secondaryOk = breeds.some(
                        (b) => String(b.breed_id) === f.breedSecondaryId && b.species === next,
                      )
                      const coatOk = COAT_TYPES[next].some((o) => o.value === f.coatType)
                      return {
                        ...f,
                        species: next,
                        breedId: breedOk ? f.breedId : '',
                        breedSecondaryId: secondaryOk ? f.breedSecondaryId : '',
                        coatType: coatOk ? f.coatType : '',
                      }
                    })
                  }}
                />
                <BreedPicker
                  id="dir_breed_secondary"
                  label="Crossed with (optional)"
                  breeds={breeds.filter((b) => b.species === form.species)}
                  value={form.breedSecondaryId}
                  onChange={(v) => set('breedSecondaryId', v)}
                  onAdd={addBreed}
                  disabled={isBusy}
                />
                <div className="field-grid field-grid-compact more-pair">
                  <div className="field">
                    <label htmlFor="dir_weight">Weight (kg)</label>
                    <input
                      id="dir_weight"
                      type="text"
                      inputMode="decimal"
                      value={form.weightKg}
                      onChange={(e) => set('weightKg', e.target.value)}
                      placeholder="If weighed"
                    />
                  </div>
                  <ChoiceChips
                    id="dir_sex"
                    label="Sex"
                    columns={2}
                    options={SEXES}
                    value={form.sex}
                    onChange={(v) => set('sex', v)}
                    disabled={isBusy}
                  />
                </div>
                <div className="yes-no-list">
                  <YesNo
                    id="dir_muzzle"
                    label="Needs a muzzle"
                    value={form.muzzleRequired}
                    onChange={(v) => set('muzzleRequired', v)}
                    disabled={isBusy}
                  />
                  <YesNo
                    id="dir_two_person"
                    label="Two-person job"
                    value={form.twoPersonJob}
                    onChange={(v) => set('twoPersonJob', v)}
                    disabled={isBusy}
                  />
                  <YesNo
                    id="dir_senior"
                    label="Senior"
                    value={form.seniorFlag}
                    onChange={(v) => set('seniorFlag', v)}
                    disabled={isBusy}
                  />
                </div>
              </div>
            </details>
          </div>
        </form>

        <div className="actions action-bar">
          {dirty && <span className="action-bar-note">Unsaved changes</span>}
          <button type="submit" form="dog-profile-form" className="primary" disabled={isBusy}>
            Save changes
          </button>
        </div>
      </section>
    </>
  )
}
