/**
 * The in-progress visit, saved to localStorage so a killed phone tab or a
 * reload can resume it (#88). Photos can't be saved (a File isn't
 * serializable), so the draft only remembers that there was one.
 */

export type TimerStatus = 'idle' | 'running' | 'stopped'

export type VisitStep = 1 | 2 | 3

/** The dog a visit is for, with the names shown in the header. */
export type SelectedDog = {
  dog_id: number
  owner_id: number
  dog_name: string
  owner_name: string
}

const DRAFT_KEY = 'muttmetrics.draftVisit'
const DRAFT_MAX_AGE_MS = 12 * 60 * 60 * 1000 // 12 hours

export type DraftVisit = {
  selectedDog: SelectedDog
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

export function loadDraft(): DraftVisit | null {
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

  // Older drafts (#192) may omit addOnIds
  if (!Array.isArray(draft.addOnIds)) {
    draft = { ...draft, addOnIds: [] }
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
    return `Resumed timer for ${draft.selectedDog.dog_name}`
  }
  const many = lost.length > 1
  return (
    `Resumed timer for ${draft.selectedDog.dog_name} — the ${lost.join(' and ')} ` +
    `photo${many ? 's' : ''} could not be kept, please pick ${many ? 'them' : 'it'} again`
  )
}
