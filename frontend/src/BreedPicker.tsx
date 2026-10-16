import { useEffect, useId, useMemo, useRef, useState } from 'react'

export type BreedOption = {
  breed_id: number
  name_de: string | null
  name_en: string | null
}

type BreedPickerProps = {
  id?: string
  label: string
  breeds: BreedOption[]
  /** Selected breed id as string, or '' for none (optional). */
  value: string
  onChange: (next: string) => void
  disabled?: boolean
}

function breedLabel(b: BreedOption): string {
  if (b.name_de && b.name_en && b.name_de !== b.name_en) {
    return `${b.name_de} / ${b.name_en}`
  }
  return b.name_de || b.name_en || `Breed ${b.breed_id}`
}

/**
 * Type-to-filter breed control. Value is always optional (empty = clear).
 * Filters the in-memory catalog from GET /api/breeds — no server search.
 */
export function BreedPicker({
  id: idProp,
  label,
  breeds,
  value,
  onChange,
  disabled = false,
}: BreedPickerProps) {
  const reactId = useId()
  const inputId = idProp ?? `breed-${reactId}`
  const listId = `${inputId}-list`

  const selected = useMemo(
    () => breeds.find((b) => String(b.breed_id) === value) ?? null,
    [breeds, value],
  )

  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const matches = useMemo(() => {
    const q = filter.trim().toLowerCase()
    if (q === '') return breeds
    return breeds.filter((b) => breedLabel(b).toLowerCase().includes(q))
  }, [breeds, filter])

  useEffect(() => {
    if (!open) return
    function onDocPointer(e: MouseEvent): void {
      if (rootRef.current === null) return
      if (!rootRef.current.contains(e.target as Node)) {
        setOpen(false)
        setFilter('')
      }
    }
    document.addEventListener('mousedown', onDocPointer)
    return () => document.removeEventListener('mousedown', onDocPointer)
  }, [open])

  useEffect(() => {
    setActiveIndex(0)
  }, [filter, open])

  function openList(): void {
    if (disabled) return
    setOpen(true)
    setFilter('')
  }

  function pick(breedId: number): void {
    onChange(String(breedId))
    setOpen(false)
    setFilter('')
    inputRef.current?.blur()
  }

  function clear(): void {
    onChange('')
    setOpen(false)
    setFilter('')
    inputRef.current?.focus()
  }

  const displayValue = open
    ? filter
    : selected !== null
      ? breedLabel(selected)
      : ''

  return (
    <div
      className={open ? 'field breed-picker breed-picker-open' : 'field breed-picker'}
      ref={rootRef}
    >
      <label htmlFor={inputId}>{label}</label>
      <div className="breed-picker-controls">
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          autoComplete="off"
          disabled={disabled}
          placeholder="Type to search… (optional)"
          value={displayValue}
          onChange={(e) => {
            setFilter(e.target.value)
            if (!open) setOpen(true)
          }}
          onFocus={openList}
          onClick={openList}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.preventDefault()
              setOpen(false)
              setFilter('')
              return
            }
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              if (!open) {
                openList()
                return
              }
              setActiveIndex((i) =>
                matches.length === 0 ? 0 : Math.min(i + 1, matches.length - 1),
              )
              return
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault()
              setActiveIndex((i) => Math.max(i - 1, 0))
              return
            }
            if (e.key === 'Enter' && open && matches[activeIndex]) {
              e.preventDefault()
              pick(matches[activeIndex].breed_id)
            }
          }}
        />
        {value !== '' && !disabled && (
          <button
            type="button"
            className="breed-picker-clear"
            aria-label={`Clear ${label}`}
            onClick={clear}
          >
            Clear
          </button>
        )}
      </div>
      {open && (
        <ul id={listId} className="breed-picker-list" role="listbox">
          {matches.length === 0 ? (
            <li className="breed-picker-empty" role="presentation">
              No matches
            </li>
          ) : (
            matches.map((b, i) => (
              <li key={b.breed_id} role="option" aria-selected={i === activeIndex}>
                <button
                  type="button"
                  className={
                    i === activeIndex
                      ? 'breed-picker-option breed-picker-option-active'
                      : 'breed-picker-option'
                  }
                  onMouseEnter={() => setActiveIndex(i)}
                  onClick={() => pick(b.breed_id)}
                >
                  {breedLabel(b)}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
