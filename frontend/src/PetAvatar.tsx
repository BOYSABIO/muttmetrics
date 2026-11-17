import { useId, useRef, useState } from 'react'

type PetAvatarProps = {
  photoId: number | null | undefined
  name: string
  size?: 'md' | 'lg'
  /** Which word gives the initial: a pet's last ("Mr Biscuit" → B), a person's first. */
  initialFrom?: 'first' | 'last'
  /** When set, tapping the avatar opens the device photo picker. */
  onPickFile?: (file: File) => void
  disabled?: boolean
}

const TINTS = ['sun', 'pine', 'clay', 'sky', 'plum', 'moss'] as const

/** The same name always gets the same colour. */
function tintFor(name: string): (typeof TINTS)[number] {
  let h = 0
  for (const ch of name) h = (h * 31 + ch.codePointAt(0)!) >>> 0
  return TINTS[h % TINTS.length]
}

/** "Bella" → B; "Mr Biscuit" → B (the last word is the one people say). */
function initialOf(name: string, from: 'first' | 'last'): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  const word = (from === 'first' ? words[0] : words[words.length - 1]) ?? ''
  const first = [...word][0] ?? '?'
  return first.toLocaleUpperCase()
}

/** No photo yet: the pet's initial on its own colour, so a list isn't a wall
 *  of identical faces. */
function Initial({ name, from }: { name: string; from: 'first' | 'last' }) {
  return (
    <span className="dog-avatar-initial" aria-hidden="true">
      {initialOf(name, from)}
    </span>
  )
}

function CameraBadge() {
  return (
    <span className="dog-avatar-badge" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
        <path d="M9 3.5 7.8 5H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2.8L15 3.5H9zm3 4.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9zm0 2a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z" />
      </svg>
    </span>
  )
}

export function PetAvatar({
  photoId,
  name,
  size = 'md',
  initialFrom = 'last',
  onPickFile,
  disabled = false,
}: PetAvatarProps) {
  // Remember which photoId failed so a new id retries automatically (#194).
  const [failedPhotoId, setFailedPhotoId] = useState<number | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()
  const editable = onPickFile !== undefined

  // Proxy injects X-API-Key for /api/photos/* — plain <img> is enough.
  const src =
    photoId != null && failedPhotoId !== photoId
      ? `/api/photos/${photoId}`
      : null

  const className = [
    'dog-avatar',
    size === 'lg' ? 'dog-avatar-lg' : '',
    editable ? 'dog-avatar-editable' : '',
  ]
    .filter(Boolean)
    .join(' ')

  const face = (
    <span
      className={
        src !== null ? 'dog-avatar-face' : `dog-avatar-face dog-avatar-tint-${tintFor(name)}`
      }
    >
      {src !== null ? (
        <img
          src={src}
          alt=""
          className="dog-avatar-img"
          onError={() => {
            if (photoId != null) {
              setFailedPhotoId(photoId)
            }
          }}
        />
      ) : (
        <Initial name={name} from={initialFrom} />
      )}
    </span>
  )

  if (!editable) {
    return (
      <div className={className} aria-label={`${name} photo`}>
        {face}
      </div>
    )
  }

  return (
    <div className="dog-avatar-wrap">
      <button
        type="button"
        className={className}
        disabled={disabled}
        aria-label={
          photoId != null
            ? `Change photo for ${name}`
            : `Add photo for ${name}`
        }
        onClick={() => inputRef.current?.click()}
      >
        {face}
        <CameraBadge />
      </button>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept="image/*"
        className="visually-hidden"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file !== undefined) {
            onPickFile(file)
          }
        }}
      />
      <p className="dog-avatar-hint">
        {photoId != null ? 'Tap to change photo' : 'Tap to add photo'}
      </p>
    </div>
  )
}
