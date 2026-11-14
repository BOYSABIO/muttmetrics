import type { Option } from './petVocab'

type ChoiceChipsProps = {
  id: string
  label: string
  options: Option<string>[]
  /** '' = not set */
  value: string
  onChange: (next: string) => void
  disabled?: boolean
  /** Shown under the chips, e.g. the selected option's hint */
  note?: string
  /**
   * Equal-width grid columns on a phone. Leave out for long words: the chips
   * then size to their words and wrap. From 560px wide they always do.
   */
  columns?: 2 | 3 | 4 | 5 | 6
}

/**
 * One tap per answer for a fixed list (the codes are the API's). Tapping the
 * selected chip again clears it: blank means "nobody checked", so it has to
 * stay reachable.
 */
export function ChoiceChips({
  id,
  label,
  options,
  value,
  onChange,
  disabled = false,
  note,
  columns,
}: ChoiceChipsProps) {
  return (
    <div className="field">
      <span id={`${id}-label`} className="field-label">
        {label}
      </span>
      <div
        className={`chip-row choice-chips ${columns ? `choice-chips-${columns}` : 'choice-chips-flow'}`}
        role="group"
        aria-labelledby={`${id}-label`}
      >
        {options.map((o) => {
          const on = value === o.value
          return (
            <button
              key={o.value}
              type="button"
              className={`chip ${on ? 'chip-on' : ''}`}
              aria-pressed={on}
              disabled={disabled}
              title={o.hint}
              onClick={() => onChange(on ? '' : o.value)}
            >
              {o.label}
            </button>
          )
        })}
      </div>
      {note !== undefined && note !== '' && <span className="step-meta">{note}</span>}
    </div>
  )
}

type YesNoProps = {
  id: string
  label: string
  /** null = nobody checked */
  value: boolean | null
  onChange: (next: boolean | null) => void
  disabled?: boolean
}

/** Yes / No with a real "not checked" (neither selected), unlike a checkbox. */
export function YesNo({ id, label, value, onChange, disabled = false }: YesNoProps) {
  return (
    <div className="yes-no">
      <span id={`${id}-label`} className="yes-no-label">
        {label}
      </span>
      <div className="chip-row" role="group" aria-labelledby={`${id}-label`}>
        {([true, false] as const).map((v) => {
          const on = value === v
          return (
            <button
              key={String(v)}
              type="button"
              className={`chip ${on ? 'chip-on' : ''}`}
              aria-pressed={on}
              disabled={disabled}
              onClick={() => onChange(on ? null : v)}
            >
              {v ? 'Yes' : 'No'}
            </button>
          )
        })}
      </div>
    </div>
  )
}
