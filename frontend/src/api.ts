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

export type DogSearchItem = {
  dog_id: number
  name: string
  owner_id: number
  owner_name: string
  last_visit_date: string | null
}

export type ServiceListItem = {
  service_id: number
  slug: string | null
  name_en: string | null
  name_de: string | null
  base_minutes: number | null
  price_base: number | null
}

export type BreedListItem = {
  breed_id: number
  name_de: string | null
  name_en: string | null
}

export type VisitSummary = {
  visit_id: number
  visit_date: string
  actual_minutes: number
  condition_score: number | null
  status: string | null
}

export type DogProfile = {
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

export type OwnerDogItem = {
  dog_id: number
  name: string
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
  dogs: OwnerDogItem[]
}

export type CreatedOwner = { owner_id: number; name: string }
export type CreatedDog = { dog_id: number; name: string }
export type CreatedVisit = { visit_id: number }

/** Full visit row after create/get/patch (#193). */
export type VisitDetail = {
  visit_id: number
  dog_id: number
  owner_id: number
  visit_date: string
  actual_minutes: number
  condition_score: number | null
  booked_service_id: number | null
  actual_service_id: number | null
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

export type WeekSummary = {
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
  week_start: string
  week_end: string
  buffer_minutes: number
  min_n: number
  summary: WeekSummary
  eur_per_hour: EurPerHourCell[]
  overrun: OverrunOut
  p90_miss: P90MissOut
  utilization: UtilizationDay[]
  utilization_weeks: UtilizationWeek[]
}

export type MetricsPeriodOut = MetricsPeriodBlock & {
  previous_week?: MetricsPeriodBlock | null
  previous_period?: MetricsPeriodBlock | null
}

// ---------------------------------------------------------------------------
// Plumbing
// ---------------------------------------------------------------------------

function jsonHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY,
  }
}

function keyOnlyHeaders(): HeadersInit {
  // No Content-Type: for multipart uploads the browser must set it itself,
  // because it has to append the boundary marker that separates the parts.
  return { 'X-API-Key': import.meta.env.VITE_API_KEY }
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
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    headers: keyOnlyHeaders(),
    body: form,
  })
  return (await readJson(res)) as T
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export function searchDogs(q: string): Promise<DogSearchItem[]> {
  const params = new URLSearchParams()
  if (q.trim() !== '') {
    params.set('q', q.trim())
  }
  const qs = params.toString()
  return getJson(qs ? `/dogs?${qs}` : '/dogs')
}

export function listServices(): Promise<ServiceListItem[]> {
  return getJson('/services')
}

export function listBreeds(): Promise<BreedListItem[]> {
  return getJson('/breeds')
}

export function fetchDogProfile(dogId: number): Promise<DogProfile> {
  return getJson(`/dogs/${dogId}`)
}

export function patchDog(dogId: number, body: Record<string, unknown>): Promise<DogProfile> {
  return sendJson('PATCH', `/dogs/${dogId}`, body)
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

/** Create-or-get by name (#21): an existing owner comes back with 200. */
export function createOwner(name: string): Promise<CreatedOwner> {
  return sendJson('POST', '/owners', { name })
}

/** Create-or-get by (owner_id, name) (#21). */
export function createDog(ownerId: number, name: string): Promise<CreatedDog> {
  return sendJson('POST', '/dogs', { owner_id: ownerId, name })
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

export function uploadDogProfilePhoto(
  dogId: number,
  file: File,
): Promise<{ photo_id: number }> {
  const form = new FormData()
  form.append('file', file)
  return uploadFile(`/dogs/${dogId}/photos`, form)
}

/**
 * The JPEG bytes of one photo, or null if it can't be loaded. An `<img src>`
 * can't send the API key, so the caller turns the blob into an object URL.
 */
export async function fetchPhotoBlob(photoId: number): Promise<Blob | null> {
  const res = await fetch(`/api/photos/${photoId}`, { headers: keyOnlyHeaders() })
  return res.ok ? res.blob() : null
}

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
