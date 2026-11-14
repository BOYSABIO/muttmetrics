import { CONDITION_WORDS } from './condition'

type ConditionPickerProps = {
  /** '' = not assessed, otherwise '0'…'5' (the form keeps it as text) */
  value: string
  onChange: (next: string) => void
  disabled?: boolean
  id: string
  label?: string
}

/**
 * Six tap targets instead of a number field: one tap with a dog on the table.
 * Tapping the selected word again clears it (the field is optional).
 */
export function ConditionPicker({
  value,
  onChange,
  disabled = false,
  id,
  label = 'Coat condition on arrival (optional)',
}: ConditionPickerProps) {
  return (
    <div className="field">
      <span id={`${id}-label`} className="field-label">
        {label}
      </span>
      <div className="chip-row condition-picker" role="group" aria-labelledby={`${id}-label`}>
        {CONDITION_WORDS.map((word, score) => {
          const on = value === String(score)
          return (
            <button
              key={word}
              type="button"
              className={`chip ${on ? 'chip-on' : ''}`}
              aria-pressed={on}
              disabled={disabled}
              onClick={() => onChange(on ? '' : String(score))}
            >
              {word}
            </button>
          )
        })}
      </div>
    </div>
  )
}
