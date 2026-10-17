import { useState } from 'react'
import { errorMessage, patchOwner, type OwnerProfile } from './api'
import { DogAvatar } from './DogAvatar'

type OwnerForm = {
  name: string
  phone: string
  email: string
  locale: string
  addressArea: string
  preferredChannel: string
  clientSince: string
  notes: string
}

function formFromProfile(p: OwnerProfile): OwnerForm {
  return {
    name: p.name,
    phone: p.phone ?? '',
    email: p.email ?? '',
    locale: p.locale || 'de',
    addressArea: p.address_area ?? '',
    preferredChannel: p.preferred_channel ?? '',
    clientSince: p.client_since ?? '',
    notes: p.notes ?? '',
  }
}

/** Trimmed text, or null when empty (PATCH clears the field). */
function textOrNull(s: string): string | null {
  const t = s.trim()
  return t === '' ? null : t
}

type OwnerProfileViewProps = {
  profile: OwnerProfile
  onBack: () => void
  onOpenDog: (dogId: number) => void
  /** After a save, so the client list can refresh names. */
  onSaved: () => void
}

/** One owner's profile: read, safe PATCH (#131/#132), their dogs. */
export function OwnerProfileView({
  profile: initial,
  onBack,
  onOpenDog,
  onSaved,
}: OwnerProfileViewProps) {
  const [profile, setProfile] = useState(initial)
  const [form, setForm] = useState(() => formFromProfile(initial))
  const [isBusy, setIsBusy] = useState(false)
  const [message, setMessage] = useState('')

  function set<K extends keyof OwnerForm>(key: K, value: OwnerForm[K]): void {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function save(): Promise<void> {
    if (isBusy) return
    if (form.name.trim() === '') {
      setMessage('Owner name cannot be empty')
      return
    }
    setIsBusy(true)
    setMessage('Saving…')
    try {
      const updated = await patchOwner(profile.owner_id, {
        name: form.name.trim(),
        phone: textOrNull(form.phone),
        email: textOrNull(form.email),
        locale: textOrNull(form.locale) ?? 'de',
        address_area: textOrNull(form.addressArea),
        preferred_channel: textOrNull(form.preferredChannel),
        client_since: textOrNull(form.clientSince),
        notes: textOrNull(form.notes),
      })
      setProfile(updated)
      setForm(formFromProfile(updated))
      setMessage('Saved')
      onSaved()
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
        <header className="profile-hero profile-hero-owner">
          <div className="dog-avatar dog-avatar-lg owner-avatar" aria-hidden>
            <span className="owner-avatar-initial">
              {(profile.name.trim()[0] || '?').toUpperCase()}
            </span>
          </div>
          <div className="profile-hero-text">
            <h2>{profile.name}</h2>
            <p className="step-meta">
              {profile.visit_count ?? 0} total{' '}
              {(profile.visit_count ?? 0) === 1 ? 'visit' : 'visits'}
              {profile.lifetime_value != null
                ? ` · LTV ${profile.lifetime_value}`
                : ''}
            </p>
          </div>
        </header>

        <form
          id="owner-profile-form"
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
              <label htmlFor="own_name">Name</label>
              <input
                id="own_name"
                type="text"
                autoComplete="name"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="own_phone">Phone</label>
              <input
                id="own_phone"
                type="tel"
                autoComplete="tel"
                value={form.phone}
                onChange={(e) => set('phone', e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="field">
              <label htmlFor="own_email">Email</label>
              <input
                id="own_email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) => set('email', e.target.value)}
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
                value={form.preferredChannel}
                onChange={(e) => set('preferredChannel', e.target.value)}
                placeholder="WhatsApp, phone…"
              />
            </div>
            <div className="field">
              <label htmlFor="own_area">Address area</label>
              <input
                id="own_area"
                type="text"
                value={form.addressArea}
                onChange={(e) => set('addressArea', e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="field">
              <label htmlFor="own_locale">Locale</label>
              <input
                id="own_locale"
                type="text"
                value={form.locale}
                onChange={(e) => set('locale', e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="own_since">Client since</label>
              <input
                id="own_since"
                type="date"
                value={form.clientSince}
                onChange={(e) => set('clientSince', e.target.value)}
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
                value={form.notes}
                onChange={(e) => set('notes', e.target.value)}
                placeholder="Optional notes"
              />
            </div>
          </div>
        </div>

        <div className="profile-block">
          <h3 className="profile-section">Dogs</h3>
          {profile.dogs.length === 0 ? (
            <p className="step-meta">No dogs on this owner.</p>
          ) : (
            <ul className="dir-card-list">
              {profile.dogs.map((d) => (
                <li key={d.dog_id}>
                  <button
                    type="button"
                    className="dir-card"
                    disabled={isBusy}
                    onClick={() => {
                      onOpenDog(d.dog_id)
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
            onClick={onBack}
          >
            Back
          </button>
        </div>
      </section>
    </>
  )
}
