/**
 * Every call the SPA makes to the API, in one place (#180).
 *
 * Components import functions from here and never call `fetch` themselves, so
 * the API-key header, error handling and response types can't drift between
 * screens. The Vite proxy forwards `/api/*` to FastAPI on :8000.
 */

// ---------------------------------------------------------------------------
// Response types (mirror the Pydantic schemas in src/muttmetrics/api/schemas)
// ---------------------------------------------------------------------------

export type Species = 'dog' | 'cat'

export type PetSearchItem = {
  pet_id: number
  name: string
  species: Species
  owner_id: number
  owner_name: string
  last_visit_date: string | null
}

export type ServiceListItem = {
  service_id: number
  slug: string | null
  species: string | null
  name_en: string | null
  name_de: string | null
  base_minutes: number | null
  price_base: number | null
}

/** Technique / add-on catalog row (#192). */
export type AddOnListItem = {
  add_on_id: number
  slug: string
  name_en: string | null
  name_de: string | null
  pricing: string
  price_base: number | null
}

/** Add-on nested on a visit / dog recent visit (#192). */
export type AddOnSummary = {
  add_on_id: number
  slug: string
  name_en: string | null
  name_de: string | null
  pricing: string
}

export type BreedListItem = {
  breed_id: number
  species: Species
  name_de: string | null
  name_en: string | null
}

export type VisitSummary = {
  visit_id: number
  visit_date: string
  actual_minutes: number
  condition_score: number | null
  status: string | null
  add_ons: AddOnSummary[]
}

export type PetProfile = {
  pet_id: number
  owner_id: number
  name: string
  species: Species
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

export type OwnerPetItem = {
  pet_id: number
  name: string
  species: Species
}

export type OwnerProfile = {
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
  pets: OwnerPetItem[]
}

export type CreatedOwner = {
  owner_id: number
  name: string
  phone?: string | null
  email?: string | null
}
export type CreatedPet = { pet_id: number; name: string; species: Species }
export type CreatedVisit = { visit_id: number }

/** One hit from GET /owners?q= (#191). */
export type OwnerSearchItem = {
  owner_id: number
  name: string
  phone: string | null
  pet_count: number
}

export type OwnerConflictCandidate = {
  owner_id: number
  name: string
  phone: string | null
}

/** POST /owners returned 409 — name exists; pick or add a phone (#187). */
export class OwnerNameConflictError extends Error {
  readonly candidates: OwnerConflictCandidate[]

  constructor(message: string, candidates: OwnerConflictCandidate[]) {
    super(message)
    this.name = 'OwnerNameConflictError'
    this.candidates = candidates
  }
}

export type UpsertOwnerResult = {
  owner: CreatedOwner
  /** true = HTTP 201 (new row); false = HTTP 200 (reused by name+phone). */
  created: boolean
}

/** Full visit row after create/get/patch (#193). */
export type VisitDetail = {
  visit_id: number
  pet_id: number
  owner_id: number
  visit_date: string
  actual_minutes: number
  condition_score: number | null
  booked_service_id: number | null
  actual_service_id: number | null
  add_ons: AddOnSummary[]
  what_surprised_me: string | null
  quoted_price: number | null
  final_price: number | null
  tip: number | null
  shaved_down: boolean | null
  status: 'completed' | 'cancelled' | 'no_show' | null
  days_since_last: number | null
  predicted_min_p50: number | null
  predicted_min_p90: number | null
}

// --- metrics (#156 / #170 / #178) ---

/** A rate or average: `value` is null when n < MIN_N (decided in SQL). */
export type MetricValue = {
  value: number | null
  reason: string | null
}

/** Headline totals for one inclusive range (#187; was WeekSummary). */
export type PeriodSummary = {
  visit_count: number
  groomed_minutes: number
  revenue_ex_tip: number
  revenue_inc_tip: number
  eur_per_hour_n: number
  eur_per_hour_ex_tip: MetricValue
  eur_per_hour_inc_tip: MetricValue
}

export type EurPerHourCell = {
  condition_score: number
  shaved_down: boolean
  n: number
  groomed_minutes: number | null
  hours: number | null
  revenue_ex_tip: number | null
  revenue_inc_tip: number | null
  eur_per_hour_ex_tip: MetricValue
  eur_per_hour_inc_tip: MetricValue
}

export type OverrunOut = {
  n: number
  avg_minutes: MetricValue
}

export type P90MissOut = {
  n: number
  miss_count: number
  rate: MetricValue
}

export type UtilizationDay = {
  visit_date: string
  n: number
  planned_p50: number
  planned_p90: number
  actual_minutes: number
  missing_prediction: number
  over_buffer: boolean
}

/** One ISO week from metric_utilization_weeks (#178), clipped to the period. */
export type UtilizationWeek = {
  week_start: string
  range_start: string
  range_end: string
  day_count: number
  n: number
  planned_p90: number
  actual_minutes: number
  missing_prediction: number
  over_buffer_days: number
}

export type MetricsPeriodBlock = {
  period: 'week' | 'month' | 'custom'
  /** Inclusive range bounds (#187; was week_start / week_end). */
  start: string
  end: string
  buffer_minutes: number
  min_n: number
  summary: PeriodSummary
  eur_per_hour: EurPerHourCell[]
  overrun: OverrunOut
  p90_miss: P90MissOut
  utilization: UtilizationDay[]
  utilization_weeks: UtilizationWeek[]
}

export type MetricsPeriodOut = MetricsPeriodBlock & {
  /** Present on /metrics/week only (thin wrapper). */
  previous_week?: MetricsPeriodBlock | null
  /** Present on /metrics/period (what the SPA uses). */
  previous_period?: MetricsPeriodBlock | null
  /** True while the range is running: previous is clipped to the same elapsed days. */
  previous_is_partial?: boolean
  /** The last `recent_days` up to the range end (or today): coat €/hour, estimates. */
  recent_days?: number | null
  recent?: MetricsPeriodBlock | null
  /** Totals since the first completed visit; null before any. */
  all_time?: AllTimeOut | null
}

export type AllTimeOut = {
  first_visit_date: string
  through: string
  summary: PeriodSummary
}

// ---------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------

function jsonHeaders(): HeadersInit {
  // Auth is added by the Vite /api proxy from server-side API_KEY (#194).
  // Never send X-API-Key from the browser — it would bake into dist/.
  return { 'Content-Type': 'application/json' }
}

/**
 * Parse a response, or throw an Error whose message is safe to show.
 * 5xx → "Server error (500)"; 4xx → the API's `detail` text when it has one.
 */
export async function readJson(res: Response): Promise<unknown> {
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
    } else if (typeof data === 'object' && data !== null && 'detail' in data) {
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

/**
 * Any caught error → one line for the status bar. `fetch` throws a TypeError
 * when the request never got an answer (offline, server down).
 */
export function errorMessage(error: unknown): string {
  if (error instanceof TypeError) {
    return "Can't reach server — check your connection"
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { method: 'GET', headers: jsonHeaders() })
  return (await readJson(res)) as T
}

async function sendJson<T>(method: 'POST' | 'PATCH', path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  })
  return (await readJson(res)) as T
}

async function sendDelete(path: string): Promise<void> {
  const res = await fetch(`/api${path}`, {
    method: 'DELETE',
    headers: jsonHeaders(),
  })
  await readJson(res)
}

async function uploadFile<T>(path: string, form: FormData): Promise<T> {
  // No Content-Type: the browser must set multipart boundary itself.
  // No X-API-Key: the Vite proxy injects it (#194).
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    body: form,
  })
  return (await readJson(res)) as T
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export function searchPets(q: string): Promise<PetSearchItem[]> {
  const params = new URLSearchParams()
  if (q.trim() !== '') {
    params.set('q', q.trim())
  }
  const qs = params.toString()
  return getJson(qs ? `/pets?${qs}` : '/pets')
}

/** Browse/search owners for capture "Already a client?" (#191). */
export function searchOwners(q: string): Promise<OwnerSearchItem[]> {
  const params = new URLSearchParams()
  if (q.trim() !== '') {
    params.set('q', q.trim())
  }
  const qs = params.toString()
  return getJson(qs ? `/owners?${qs}` : '/owners')
}

export function listServices(species?: Species): Promise<ServiceListItem[]> {
  const params = new URLSearchParams()
  if (species) params.set('species', species)
  const qs = params.toString()
  return getJson(qs ? `/services?${qs}` : '/services')
}

export function listAddOns(): Promise<AddOnListItem[]> {
  return getJson('/add-ons')
}

export function listBreeds(species?: Species): Promise<BreedListItem[]> {
  const params = new URLSearchParams()
  if (species) params.set('species', species)
  const qs = params.toString()
  return getJson(qs ? `/breeds?${qs}` : '/breeds')
}

export function fetchPetProfile(petId: number): Promise<PetProfile> {
  return getJson(`/pets/${petId}`)
}

export function patchPet(petId: number, body: Record<string, unknown>): Promise<PetProfile> {
  return sendJson('PATCH', `/pets/${petId}`, body)
}

export function fetchOwnerProfile(ownerId: number): Promise<OwnerProfile> {
  return getJson(`/owners/${ownerId}`)
}

export function patchOwner(
  ownerId: number,
  body: Record<string, unknown>,
): Promise<OwnerProfile> {
  return sendJson('PATCH', `/owners/${ownerId}`, body)
}

/**
 * Create an owner, or reuse when name+phone clearly match (#187).
 *
 * 409 with candidates → throws OwnerNameConflictError (SPA must pick / add phone).
 * 201 → created: true; 200 → created: false (same person via phone).
 */
export async function createOwner(
  name: string,
  phone?: string | null,
): Promise<UpsertOwnerResult> {
  const body: Record<string, unknown> = { name }
  const trimmedPhone = phone?.trim()
  if (trimmedPhone) {
    body.phone = trimmedPhone
  }

  const res = await fetch('/api/owners', {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  })

  if (res.status === 409) {
    const text = await res.text()
    let message = 'An owner with this name already exists.'
    let candidates: OwnerConflictCandidate[] = []
    try {
      const parsed = JSON.parse(text) as {
        detail?: {
          message?: string
          candidates?: OwnerConflictCandidate[]
        }
      }
      if (typeof parsed.detail?.message === 'string') {
        message = parsed.detail.message
      }
      if (Array.isArray(parsed.detail?.candidates)) {
        candidates = parsed.detail.candidates
      }
    } catch {
      /* plain body */
    }
    throw new OwnerNameConflictError(message, candidates)
  }

  const data = (await readJson(res)) as CreatedOwner
  return { owner: data, created: res.status === 201 }
}

/** Create-or-get by (owner_id, name, species) (#21 / #190). */
export function createPet(
  ownerId: number,
  name: string,
  species: Species = 'dog',
): Promise<CreatedPet> {
  return sendJson('POST', '/pets', { owner_id: ownerId, name, species })
}

export function createVisit(body: Record<string, unknown>): Promise<CreatedVisit> {
  return sendJson('POST', '/visits', body)
}

export function fetchVisit(visitId: number): Promise<VisitDetail> {
  return getJson(`/visits/${visitId}`)
}

export function patchVisit(
  visitId: number,
  body: Record<string, unknown>,
): Promise<VisitDetail> {
  return sendJson('PATCH', `/visits/${visitId}`, body)
}

export function deleteVisit(visitId: number): Promise<void> {
  return sendDelete(`/visits/${visitId}`)
}

export async function uploadVisitPhoto(
  visitId: number,
  file: File,
  kind: 'intake' | 'after',
): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  form.append('kind', kind)
  await uploadFile(`/visits/${visitId}/photos`, form)
}

export function uploadPetProfilePhoto(
  petId: number,
  file: File,
): Promise<{ photo_id: number }> {
  const form = new FormData()
  form.append('file', file)
  return uploadFile(`/pets/${petId}/photos`, form)
}

/** Prefer ``fetchMetricsPeriod`` — SPA uses /period for week and month (#187). */
export function fetchMetricsWeek(
  start: string,
  bufferMinutes: number,
): Promise<MetricsPeriodOut> {
  const params = new URLSearchParams({ start, buffer_minutes: String(bufferMinutes) })
  return getJson(`/metrics/week?${params}`)
}

export function fetchMetricsPeriod(
  start: string,
  end: string,
  bufferMinutes: number,
): Promise<MetricsPeriodOut> {
  const params = new URLSearchParams({
    start,
    end,
    buffer_minutes: String(bufferMinutes),
  })
  return getJson(`/metrics/period?${params}`)
}
