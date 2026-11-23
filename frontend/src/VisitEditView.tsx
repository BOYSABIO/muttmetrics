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
import { ConditionPicker } from './ConditionPicker'
import { MoneyFields } from './MoneyFields'
import { changedFrom, parseMoney, quoteToSave, type Money } from './money'
import { PageBack } from './PageBack'
import { PixelDog } from './PixelDogs'
import { ListSkeleton, Toast } from './ui'

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
  /** The price changed from what the customer was told (see money.ts). */
  priceChanged: boolean
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
    priceChanged: changedFrom(
      v.quoted_price === null ? null : Number(v.quoted_price),
      v.final_price === null ? null : Number(v.final_price),
    ),
    shavedDown: v.shaved_down === true,
    status: v.status ?? '',
  }
}

/** The form's three money boxes as one value for MoneyFields. */
function moneyOf(form: VisitForm): Money {
  return {
    price: form.finalPrice,
    tip: form.tip,
    changed: form.priceChanged,
    told: form.quotedPrice,
  }
}

function textOrNull(s: string): string | null {
  const t = s.trim()
  return t === '' ? null : t
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
  petName: string
  onBack: () => void
  /** After save or delete — parent reloads the dog profile. */
  /** After a save or a delete; `message` says which, for the screen behind. */
  onDone: (message: string) => void
}

/**
 * Edit or hard-delete one visit (#193).
 * Layout matches Directory profiles: Back top left, Save in the sticky bar,
 * Delete at the end of the page (docs/architecture/ui-conventions.md).
 */
export function VisitEditView({
  visitId,
  petName,
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

    const money = moneyOf(form)
    const quoted = quoteToSave(money)
    const final = parseMoney(form.finalPrice)
    const tip = parseMoney(form.tip)
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
      onDone('Saved the visit')
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
      onDone('Deleted the visit')
    } catch (err) {
      setMessage(errorMessage(err))
      setIsBusy(false)
    }
  }

  if (form === null && message === '') {
    return (
      <section className="panel profile-panel">
        <ListSkeleton rows={5} label="Loading visit…" />
      </section>
    )
  }

  if (form === null) {
    return (
      <>
        <Toast message={message} />
        <section className="panel profile-panel">
          <PageBack onClick={onBack} />
        </section>
      </>
    )
  }

  return (
    <>
      <Toast message={message} onClear={() => setMessage('')} />
      <section className="panel profile-panel">
        <PageBack onClick={onBack} disabled={isBusy} />
        <header className="profile-hero profile-hero-owner">
          <div className="profile-hero-text">
            <h2>Edit visit</h2>
            <p className="step-meta">
              {petName}
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
              <MoneyFields
                idPrefix="edit_"
                value={moneyOf(form)}
                onChange={(m) =>
                  setForm((f) =>
                    f === null
                      ? f
                      : {
                          ...f,
                          finalPrice: m.price,
                          tip: m.tip,
                          priceChanged: m.changed,
                          quotedPrice: m.told,
                        },
                  )
                }
                disabled={isBusy}
              />
            </div>
          </div>

          <div className="profile-block">
            <h3 className="profile-section">Coat & notes</h3>
            <div className="field-stack">
              <ConditionPicker
                id="edit_condition"
                value={form.conditionScore}
                onChange={(next) => set('conditionScore', next)}
                disabled={isBusy}
              />
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

        {/* Destructive actions live at the end of the page, never in the action bar. */}
        <div className="danger-zone">
          <PixelDog who="guard" className="danger-zone-guard" />
          <div>
            <p className="danger-zone-title">Delete this visit</p>
            <p className="step-meta">Removes the visit and its photos. It can't be undone in the app.</p>
          </div>
          <button type="button" className="danger" disabled={isBusy} onClick={() => void remove()}>
            Delete visit
          </button>
        </div>

        <div className="actions action-bar">
          <button
            type="submit"
            form="visit-edit-form"
            className={isBusy ? 'primary btn-busy' : 'primary'}
            aria-busy={isBusy}
            disabled={isBusy}
          >
            Save changes
          </button>
        </div>
      </section>
    </>
  )
}
