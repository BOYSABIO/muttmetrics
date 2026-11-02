/**
 * The in-progress visit, saved to localStorage so a killed phone tab or a
 * reload can resume it (#88). Photos can't be saved (a File isn't
 * serializable), so the draft only remembers that there was one.
 */

import type { Species } from './api'

export type TimerStatus = 'idle' | 'running' | 'stopped'

export type VisitStep = 1 | 2 | 3

/** The pet a visit is for, with the names shown in the header. */
export type SelectedPet = {
  pet_id: number
  owner_id: number
  pet_name: string
  owner_name: string
  species: Species
}

const DRAFT_KEY = 'muttmetrics.draftVisit'
const DRAFT_MAX_AGE_MS = 12 * 60 * 60 * 1000 // 12 hours

export type DraftVisit = {
  selectedPet: SelectedPet
  visitStep: VisitStep
  timerStatus: TimerStatus
  startedAt: number | null
  actualMinutes: string
  visitDate: string
  conditionScore: string
  surprise: string
  serviceId: string
  /** Selected add-on catalog ids (#192). Missing on older drafts → treat as []. */
  addOnIds: number[]
  finalPrice: string
  tip: string
  quotedPrice: string
  shavedDown: boolean
  hadIntakeFile: boolean
  hadAfterFile: boolean
  savedAt: number
}

export function clearDraft(): void {
  localStorage.removeItem(DRAFT_KEY)
}

export function saveDraft(draft: Omit<DraftVisit, 'savedAt'>): void {
  const full: DraftVisit = {
    ...draft,
    savedAt: Date.now(),
  }
  localStorage.setItem(DRAFT_KEY, JSON.stringify(full))
}

function coerceSelected(raw: unknown): SelectedPet | null {
  if (raw === null || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  const petId =
    typeof o.pet_id === 'number'
      ? o.pet_id
      : typeof o.dog_id === 'number'
        ? o.dog_id
        : null
  const petName =
    typeof o.pet_name === 'string'
      ? o.pet_name
      : typeof o.dog_name === 'string'
        ? o.dog_name
        : null
  const ownerId = typeof o.owner_id === 'number' ? o.owner_id : null
  const ownerName = typeof o.owner_name === 'string' ? o.owner_name : null
  if (petId === null || petName === null || ownerId === null || ownerName === null) {
    return null
  }
  return {
    pet_id: petId,
    owner_id: ownerId,
    pet_name: petName,
    owner_name: ownerName,
    species: o.species === 'cat' ? 'cat' : 'dog',
  }
}

export function loadDraft(): DraftVisit | null {
  const raw = localStorage.getItem(DRAFT_KEY)
  if (raw === null) {
    return null
  }

  let parsed: Record<string, unknown>
  try {
    parsed = JSON.parse(raw) as Record<string, unknown>
  } catch {
    clearDraft()
    return null
  }

  const selectedPet = coerceSelected(parsed.selectedPet ?? parsed.selectedDog)
  if (selectedPet === null) {
    clearDraft()
    return null
  }

  const draft: DraftVisit = {
    ...(parsed as unknown as DraftVisit),
    selectedPet,
    addOnIds: Array.isArray(parsed.addOnIds) ? (parsed.addOnIds as number[]) : [],
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
export function resumeMessage(draft: DraftVisit): string {
  const lost: string[] = []
  if (draft.hadIntakeFile) lost.push('before')
  if (draft.hadAfterFile) lost.push('after')
  if (lost.length === 0) {
    return `Resumed timer for ${draft.selectedPet.pet_name}`
  }
  const many = lost.length > 1
  return (
    `Resumed timer for ${draft.selectedPet.pet_name} — the ${lost.join(' and ')} ` +
    `photo${many ? 's' : ''} could not be kept, please pick ${many ? 'them' : 'it'} again`
  )
}
