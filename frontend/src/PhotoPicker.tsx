import { useEffect, useState } from 'react'

type PhotoPickerProps = {
    label: string
    inputId: string
    file: File | null
    onPick: (file: File | null) => void
    disabled?: boolean
}

export function PhotoPicker({
    label,
    inputId,
    file,
    onPick,
    disabled = false,
}: PhotoPickerProps) {
    const [blobUrl, setBlobUrl] = useState<string | null>(null)
    // No file → no preview, derived during render rather than set in the effect.
    const previewUrl = file === null ? null : blobUrl

    useEffect(() => {
        if (file === null) return

        // A blob URL is a handle into browser memory - it must be released,
        // or every re-pick leaks the prev image.
        const url = URL.createObjectURL(file)
        // Creating the URL is the external side effect and the cleanup below
        // must revoke the same one, so this setState has to live in the effect.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setBlobUrl(url)
        return () => URL.revokeObjectURL(url)
    }, [file])

    function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
        //files is a FileList and can be empty if the user cancels the picker.
        onPick(event.target.files?.[0] ?? null)
    }

  return (
    <div className="photo-picker">
      <p className="photo-picker-label">{label}</p>

      {previewUrl !== null ? (
        <img src={previewUrl} alt={label} className="photo-preview" />
      ) : (
        // The empty frame is itself the camera button: the biggest target on
        // the step is the thing you came here to do.
        <label className="photo-frame" htmlFor={`${inputId}-camera`}>
          <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true">
            <path
              d="M4 8.5h3.2l1.3-2h7l1.3 2H20a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5a1 1 0 0 1 1-1z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
            <circle cx="12" cy="13.5" r="3.3" fill="none" stroke="currentColor" strokeWidth="1.8" />
          </svg>
          <span>No photo yet</span>
        </label>
      )}

      <div className="photo-picker-buttons">
        <label className="photo-button" htmlFor={`${inputId}-camera`}>
          Take photo
        </label>
        <input
          id={`${inputId}-camera`}
          type="file"
          accept="image/*"
          capture="environment"
          disabled={disabled}
          onChange={handleChange}
          className="visually-hidden"
        />

        <label className="photo-button" htmlFor={`${inputId}-library`}>
          Choose photo
        </label>
        <input
          id={`${inputId}-library`}
          type="file"
          accept="image/*"
          disabled={disabled}
          onChange={handleChange}
          className="visually-hidden"
        />
      </div>

      {file !== null && (
        <p className="photo-picker-file">
          {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB{' '}
          <button type="button" onClick={() => onPick(null)} disabled={disabled}>
            Remove
          </button>
        </p>
      )}
    </div>
  )
}