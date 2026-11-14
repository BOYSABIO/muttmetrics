import type { Species } from './species'

const OPTIONS: { value: Species; label: string }[] = [
  { value: 'dog', label: 'Dog' },
  { value: 'cat', label: 'Cat' },
]

type SpeciesChipsProps = {
  value: Species
  onChange: (next: Species) => void
  disabled?: boolean
  name?: string
}

/**
 * Dog / cat picker. Default is dog (ADR-004). Same chips as every other
 * fixed list (ChoiceChips), but one is always selected: species is required.
 */
export function SpeciesChips({
  value,
  onChange,
  disabled = false,
  name = 'species',
}: SpeciesChipsProps) {
  return (
    <div className="field">
      <span id={`${name}-label`} className="field-label">
        Species
      </span>
      <div
        className="chip-row choice-chips choice-chips-2"
        role="radiogroup"
        aria-labelledby={`${name}-label`}
      >
        {OPTIONS.map((opt) => {
          const on = value === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={on}
              className={`chip ${on ? 'chip-on' : ''}`}
              disabled={disabled}
              onClick={() => {
                if (!on) onChange(opt.value)
              }}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
