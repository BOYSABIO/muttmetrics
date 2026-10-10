import { useEffect, useId, useRef, useState } from 'react'

type DogAvatarProps = {
  photoId: number | null | undefined
  name: string
  size?: 'md' | 'lg'
  /** When set, tapping the avatar opens the device photo picker. */
  onPickFile?: (file: File) => void
  disabled?: boolean
}

function apiKeyHeaders(): HeadersInit {
  return { 'X-API-Key': import.meta.env.VITE_API_KEY }
}

function StockDogIcon() {
  return (
    <svg
      className="dog-avatar-stock"
      viewBox="0 0 64 64"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="32" cy="32" r="30" fill="currentColor" opacity="0.12" />
      <path
        fill="currentColor"
        d="M20 28c-3 0-5-2.5-5-5.5S17 17 20 17s5 2.5 5 5.5S23 28 20 28zm24 0c-3 0-5-2.5-5-5.5S41 17 44 17s5 2.5 5 5.5S47 28 44 28zM18 36c2 8 8 12 14 12s12-4 14-12c-4 2-9 3-14 3s-10-1-14-3z"
        opacity="0.55"
      />
    </svg>
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

export function DogAvatar({
  photoId,
  name,
  size = 'md',
  onPickFile,
  disabled = false,
}: DogAvatarProps) {
  const [src, setSrc] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()
  const editable = onPickFile !== undefined

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    async function load() {
      if (photoId == null) {
        setSrc(null)
        return
      }
      try {
        const res = await fetch(`/api/photos/${photoId}`, {
          headers: apiKeyHeaders(),
        })
        if (!res.ok) {
          if (!cancelled) setSrc(null)
          return
        }
        const blob = await res.blob()
        objectUrl = URL.createObjectURL(blob)
        if (!cancelled) setSrc(objectUrl)
      } catch {
        if (!cancelled) setSrc(null)
      }
    }

    void load()
    return () => {
      cancelled = true
      if (objectUrl !== null) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [photoId])

  const className = [
    'dog-avatar',
    size === 'lg' ? 'dog-avatar-lg' : '',
    editable ? 'dog-avatar-editable' : '',
  ]
    .filter(Boolean)
    .join(' ')

  const face = (
    <span className="dog-avatar-face">
      {src !== null ? (
        <img src={src} alt="" className="dog-avatar-img" />
      ) : (
        <StockDogIcon />
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
