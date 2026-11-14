import { useId, useMemo, useRef, useState } from 'react'

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
  /**
   * Offer "Add 'X' as a breed" when nothing matches exactly. Resolves to the
   * new breed (or the existing one, if the server says it's a twin).
   */
  onAdd?: (name: string) => Promise<BreedOption>
  disabled?: boolean
}

/** On screen: the English name (the groomer works in English). */
function breedLabel(b: BreedOption): string {
  return b.name_en || b.name_de || `Breed ${b.breed_id}`
}

/** Lower-case, accents off: "schaferhund" finds "Schäferhund", "frise" "Frisé". */
function fold(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

type Row = { kind: 'breed'; breed: BreedOption } | { kind: 'add'; name: string }

/**
 * Type-to-filter breed control. Value is always optional (empty = clear).
 * Filters the in-memory catalog (English and German names); names starting
 * with what you typed come first. With `onAdd`, when nothing matches, a row
 * offers to add what was typed as a new breed.
 */
export function BreedPicker({
  id: idProp,
  label,
  breeds,
  value,
  onChange,
  onAdd,
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
  const [adding, setAdding] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const rows = useMemo<Row[]>(() => {
    const q = fold(filter)
    const sorted = [...breeds].sort((a, b) => breedLabel(a).localeCompare(breedLabel(b)))
    if (q === '') return sorted.map((breed) => ({ kind: 'breed', breed }))
    const starts: BreedOption[] = []
    const contains: BreedOption[] = []
    for (const b of sorted) {
      const names = [b.name_en, b.name_de].filter((n): n is string => !!n).map(fold)
      if (names.some((n) => n.startsWith(q) || n.includes(` ${q}`))) starts.push(b)
      else if (names.some((n) => n.includes(q))) contains.push(b)
    }
    const out: Row[] = [...starts, ...contains].map((breed) => ({ kind: 'breed', breed }))
    // Only when nothing matches at all: a partial match ("schafer" ->
    // German Shepherd) is far more likely the breed than a new one.
    if (onAdd !== undefined && out.length === 0 && filter.trim().length >= 2) {
      out.push({ kind: 'add', name: filter.trim().replace(/\s+/g, ' ') })
    }
    return out
  }, [breeds, filter, onAdd])

  // The highlighted row resets whenever the list opens or the filter changes.
  // Done in those handlers, not in an effect, so there's no extra render.
  function openList(): void {
    if (disabled) return
    setOpen(true)
    setFilter('')
    setActiveIndex(0)
  }

  function pick(breedId: number): void {
    onChange(String(breedId))
    setOpen(false)
    setFilter('')
    inputRef.current?.blur()
  }

  async function add(name: string): Promise<void> {
    if (onAdd === undefined || adding) return
    setAdding(true)
    try {
      const breed = await onAdd(name)
      pick(breed.breed_id)
    } catch {
      // The parent shows the error (onAdd reports it before rejecting).
    } finally {
      setAdding(false)
    }
  }

  function choose(row: Row): void {
    if (row.kind === 'breed') pick(row.breed.breed_id)
    else void add(row.name)
  }

  function clear(): void {
    onChange('')
    setOpen(false)
    setFilter('')
    inputRef.current?.focus()
  }

  const displayValue = open ? filter : selected !== null ? breedLabel(selected) : ''

  return (
    <div className={open ? 'field breed-picker breed-picker-open' : 'field breed-picker'}>
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
          aria-activedescendant={
            open && rows[activeIndex] !== undefined ? `${listId}-${activeIndex}` : undefined
          }
          autoComplete="off"
          disabled={disabled || adding}
          placeholder={adding ? 'Adding…' : 'Type to search…'}
          value={displayValue}
          onChange={(e) => {
            setFilter(e.target.value)
            setActiveIndex(0)
            if (!open) setOpen(true)
          }}
          onFocus={openList}
          // Close as soon as focus leaves the input: a click elsewhere, or Tab
          // (a document mousedown listener missed Tab). Options never take
          // focus, so there is nothing inside the list to stay open for.
          onBlur={() => {
            setOpen(false)
            setFilter('')
          }}
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
              setActiveIndex((i) => (rows.length === 0 ? 0 : Math.min(i + 1, rows.length - 1)))
              return
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault()
              setActiveIndex((i) => Math.max(i - 1, 0))
              return
            }
            if (e.key === 'Enter' && open && rows[activeIndex]) {
              e.preventDefault()
              choose(rows[activeIndex])
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
          {rows.length === 0 ? (
            <li className="breed-picker-empty" role="presentation">
              No matches
            </li>
          ) : (
            rows.map((row, i) => (
              // An option is not a button: focus stays in the input (the
              // combobox pattern), and mousedown + preventDefault picks before
              // the input's blur could close the list.
              <li
                key={row.kind === 'breed' ? row.breed.breed_id : 'add'}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === activeIndex}
                className={[
                  'breed-picker-option',
                  i === activeIndex ? 'breed-picker-option-active' : '',
                  row.kind === 'add' ? 'breed-picker-add' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onMouseEnter={() => setActiveIndex(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  choose(row)
                }}
              >
                {row.kind === 'breed' ? (
                  breedLabel(row.breed)
                ) : (
                  <>
                    <span aria-hidden>＋</span> Add “{row.name}” as a breed
                  </>
                )}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
