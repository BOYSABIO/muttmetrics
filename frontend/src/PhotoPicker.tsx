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
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)

    useEffect(() => {
        if (file === null) {
            setPreviewUrl(null)
            return
        }

        // A blob URL is a handle into browser memory - it must be released,
        // or every re-pick leaks the prev image.
        const url = URL.createObjectURL(file)
        setPreviewUrl(url)
        return () => URL.revokeObjectURL(url)
    }, [file])

    function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
        //files is a FileList and can be empty if the user cancels the picker.
        onPick(event.target.files?.[0] ?? null)
    }

  return (
    <div className="photo-picker">
      <p className="photo-picker-label">{label}</p>

      {previewUrl !== null && (
        <img src={previewUrl} alt={label} className="photo-preview" />
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