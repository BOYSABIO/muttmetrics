export type Species = 'dog' | 'cat'

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

/** Dog / cat picker. Default is dog (ADR-004). */
export function SpeciesChips({
  value,
  onChange,
  disabled = false,
  name = 'species',
}: SpeciesChipsProps) {
  return (
    <div className="field">
      <span id={`${name}-label`}>Species</span>
      <div className="chip-row" role="radiogroup" aria-labelledby={`${name}-label`}>
        {OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className={`chip ${value === opt.value ? 'chip-on' : ''}`}
          >
            <input
              type="radio"
              name={name}
              checked={value === opt.value}
              disabled={disabled}
              onChange={() => onChange(opt.value)}
            />
            {opt.label}
          </label>
        ))}
      </div>
    </div>
  )
}

export function speciesLabel(species: string): string {
  if (species === 'cat') return 'Cat'
  if (species === 'dog') return 'Dog'
  return species
}
