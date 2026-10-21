import { useEffect, useState } from 'react'
import {
  deleteVisit,
  errorMessage,
  fetchVisit,
  listServices,
  patchVisit,
  type ServiceListItem,
  type VisitDetail,
} from './api'

const STATUS_OPTIONS = [
  { value: '', label: '—' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'no_show', label: 'No-show' },
] as const

type VisitForm = {
  visitDate: string
  actualMinutes: string
  conditionScore: string
  actualServiceId: string
  whatSurprisedMe: string
  quotedPrice: string
  finalPrice: string
  tip: string
  shavedDown: boolean
  status: string
}

function formFromVisit(v: VisitDetail): VisitForm {
  return {
    visitDate: v.visit_date,
    actualMinutes: String(v.actual_minutes),
    conditionScore: v.condition_score !== null ? String(v.condition_score) : '',
    actualServiceId:
      v.actual_service_id !== null ? String(v.actual_service_id) : '',
    whatSurprisedMe: v.what_surprised_me ?? '',
    quotedPrice: v.quoted_price !== null ? String(v.quoted_price) : '',
    finalPrice: v.final_price !== null ? String(v.final_price) : '',
    tip: v.tip !== null ? String(v.tip) : '',
    shavedDown: v.shaved_down === true,
    status: v.status ?? '',
  }
}

function textOrNull(s: string): string | null {
  const t = s.trim()
  return t === '' ? null : t
}

function moneyOrNull(s: string): number | null {
  const t = s.trim().replace(',', '.')
  if (t === '') return null
  const n = Number(t)
  return Number.isFinite(n) && n >= 0 ? n : Number.NaN
}

function formatVisitDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

type VisitEditViewProps = {
  visitId: number
  dogName: string
  onBack: () => void
  /** After save or delete — parent reloads the dog profile. */
  onDone: () => void
}

/**
 * Edit or hard-delete one visit (#193).
 * Layout matches Directory profiles: one panel, sticky Save / Back / Delete.
 */
export function VisitEditView({
  visitId,
  dogName,
  onBack,
  onDone,
}: VisitEditViewProps) {
  const [visit, setVisit] = useState<VisitDetail | null>(null)
  const [form, setForm] = useState<VisitForm | null>(null)
  const [services, setServices] = useState<ServiceListItem[]>([])
  const [isBusy, setIsBusy] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const [v, svc] = await Promise.all([
          fetchVisit(visitId),
          listServices(),
        ])
        if (!cancelled) {
          setVisit(v)
          setForm(formFromVisit(v))
          setServices(svc)
        }
      } catch (err) {
        if (!cancelled) {
          setMessage(errorMessage(err))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [visitId])

  function set<K extends keyof VisitForm>(key: K, value: VisitForm[K]): void {
    setForm((f) => (f === null ? f : { ...f, [key]: value }))
  }

  async function save(): Promise<void> {
    if (isBusy || form === null || visit === null) return

    const minutes = Number(form.actualMinutes)
    if (!Number.isFinite(minutes) || minutes <= 0) {
      setMessage('Minutes must be a positive number')
      return
    }

    const quoted = moneyOrNull(form.quotedPrice)
    const final = moneyOrNull(form.finalPrice)
    const tip = moneyOrNull(form.tip)
    if ([quoted, final, tip].some((n) => Number.isNaN(n))) {
      setMessage('Prices must be empty or ≥ 0')
      return
    }

    let condition: number | null = null
    if (form.conditionScore.trim() !== '') {
      condition = Number(form.conditionScore)
      if (!Number.isInteger(condition) || condition < 0 || condition > 5) {
        setMessage('Condition must be 0–5 or empty')
        return
      }
    }

    const body: Record<string, unknown> = {
      visit_date: form.visitDate,
      actual_minutes: minutes,
      condition_score: condition,
      actual_service_id:
        form.actualServiceId === '' ? null : Number(form.actualServiceId),
      what_surprised_me: textOrNull(form.whatSurprisedMe),
      quoted_price: quoted,
      final_price: final,
      tip,
      shaved_down: form.shavedDown,
      status: form.status === '' ? null : form.status,
    }

    setIsBusy(true)
    setMessage('')
    try {
      const updated = await patchVisit(visitId, body)
      setVisit(updated)
      setForm(formFromVisit(updated))
      setMessage('Saved')
      onDone()
    } catch (err) {
      setMessage(errorMessage(err))
    } finally {
      setIsBusy(false)
    }
  }

  async function remove(): Promise<void> {
    if (isBusy) return
    const ok = window.confirm(
      'Delete this visit permanently? Photos for it will be removed too. This cannot be undone in the app (backups only).',
    )
    if (!ok) return

    setIsBusy(true)
    setMessage('')
    try {
      await deleteVisit(visitId)
      onDone()
    } catch (err) {
      setMessage(errorMessage(err))
      setIsBusy(false)
    }
  }

  if (form === null && message === '') {
    return (
      <section className="panel profile-panel">
        <p className="step-meta">Loading visit…</p>
      </section>
    )
  }

  if (form === null) {
    return (
      <>
        <p className="status" role="alert">
          {message}
        </p>
        <section className="panel profile-panel">
          <div className="actions profile-actions">
            <button type="button" className="ghost" onClick={onBack}>
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
      <section className="panel profile-panel">
        <header className="profile-hero profile-hero-owner">
          <div className="profile-hero-text">
            <h2>Edit visit</h2>
            <p className="step-meta">
              {dogName}
              {visit !== null ? ` · ${formatVisitDate(visit.visit_date)}` : ''}
            </p>
          </div>
        </header>

        <form
          id="visit-edit-form"
          className="section-grid profile-sections"
          onSubmit={(e) => {
            e.preventDefault()
            void save()
          }}
        >
          <div className="profile-block">
            <h3 className="profile-section">When</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="edit_visit_date">Visit date</label>
                <input
                  id="edit_visit_date"
                  type="date"
                  value={form.visitDate}
                  onChange={(e) => set('visitDate', e.target.value)}
                  disabled={isBusy}
                />
              </div>
              <div className="field">
                <label htmlFor="edit_minutes">Minutes</label>
                <input
                  id="edit_minutes"
                  type="number"
                  min={1}
                  value={form.actualMinutes}
                  onChange={(e) => set('actualMinutes', e.target.value)}
                  disabled={isBusy}
                />
              </div>
              <div className="field">
                <label htmlFor="edit_service">Service</label>
                <select
                  id="edit_service"
                  value={form.actualServiceId}
                  onChange={(e) => set('actualServiceId', e.target.value)}
                  disabled={isBusy || services.length === 0}
                >
                  <option value="">—</option>
                  {services.map((s) => (
                    <option key={s.service_id} value={String(s.service_id)}>
                      {s.name_en ?? s.slug ?? `Service ${s.service_id}`}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="edit_status">Status</label>
                <select
                  id="edit_status"
                  value={form.status}
                  onChange={(e) => set('status', e.target.value)}
                  disabled={isBusy}
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value || 'empty'} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Money</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="edit_final">Final price (€)</label>
                <input
                  id="edit_final"
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.finalPrice}
                  onChange={(e) => set('finalPrice', e.target.value)}
                  disabled={isBusy}
                />
              </div>
              <div className="field">
                <label htmlFor="edit_tip">Tip (€)</label>
                <input
                  id="edit_tip"
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.tip}
                  onChange={(e) => set('tip', e.target.value)}
                  disabled={isBusy}
                />
              </div>
              <div className="field">
                <label htmlFor="edit_quoted">Quoted price (€)</label>
                <input
                  id="edit_quoted"
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.quotedPrice}
                  onChange={(e) => set('quotedPrice', e.target.value)}
                  disabled={isBusy}
                />
              </div>
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Coat & notes</h3>
            <div className="field-stack">
              <div className="field">
                <label htmlFor="edit_condition">Coat condition (0–5)</label>
                <input
                  id="edit_condition"
                  type="number"
                  min={0}
                  max={5}
                  value={form.conditionScore}
                  onChange={(e) => set('conditionScore', e.target.value)}
                  disabled={isBusy}
                  placeholder="Optional"
                />
              </div>
              <label className="checkbox-row" htmlFor="edit_shaved">
                <input
                  id="edit_shaved"
                  type="checkbox"
                  checked={form.shavedDown}
                  onChange={(e) => set('shavedDown', e.target.checked)}
                  disabled={isBusy}
                />
                Shaved down
              </label>
              <div className="field">
                <label htmlFor="edit_surprise">What surprised me</label>
                <input
                  id="edit_surprise"
                  type="text"
                  value={form.whatSurprisedMe}
                  onChange={(e) => set('whatSurprisedMe', e.target.value)}
                  disabled={isBusy}
                />
              </div>
              {visit !== null && (
                <p className="step-meta visit-edit-meta">
                  At create: P50 {visit.predicted_min_p50 ?? '—'} / P90{' '}
                  {visit.predicted_min_p90 ?? '—'}
                  {visit.days_since_last !== null
                    ? ` · ${visit.days_since_last}d since last`
                    : ''}
                  . Not editable.
                </p>
              )}
            </div>
          </div>
        </form>

        <div className="actions profile-actions">
          <button
            type="submit"
            form="visit-edit-form"
            className="primary"
            disabled={isBusy}
          >
            {isBusy ? 'Saving…' : 'Save'}
          </button>
          <button type="button" disabled={isBusy} onClick={onBack}>
            Back
          </button>
          <button
            type="button"
            className="danger"
            disabled={isBusy}
            onClick={() => void remove()}
          >
            Delete
          </button>
        </div>
      </section>
    </>
  )
}
