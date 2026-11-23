import { euro, moneyWarning, totalLine, type Money } from './money'

type MoneyFieldsProps = {
  /** Prefix for the input ids ('' on New visit, 'edit_' on the edit form). */
  idPrefix: string
  value: Money
  onChange: (next: Money) => void
  disabled: boolean
  /** The price list's minimum for this groom, shown as a hint; null hides it. */
  listFrom?: number | null
}

/**
 * Price, tip and (only if it changed) what the customer was told. The total
 * line under the tip is the check: if it says more than the customer handed
 * over, the tip is in the price too. See money.ts for what each box means.
 */
export function MoneyFields({ idPrefix, value, onChange, disabled, listFrom = null }: MoneyFieldsProps) {
  const id = (name: string) => `${idPrefix}${name}`
  const set = <K extends keyof Money>(key: K, v: Money[K]) => onChange({ ...value, [key]: v })
  const total = totalLine(value)
  const warning = moneyWarning(value)

  return (
    <div className="money-fields">
      <div className="field">
        <label htmlFor={id('final_price')}>Price for the groom (€)</label>
        <p className="field-note" id={id('final_price_note')}>
          Without the tip.
          {listFrom !== null && listFrom > 0 && <> Price list: from {euro(listFrom)}.</>}
        </p>
        <input
          id={id('final_price')}
          type="number"
          inputMode="decimal"
          min={0}
          step="0.01"
          value={value.price}
          onChange={(e) => set('price', e.target.value)}
          disabled={disabled}
          aria-describedby={id('final_price_note')}
        />
      </div>

      <div className="field">
        <label htmlFor={id('tip')}>Tip (€)</label>
        <p className="field-note" id={id('tip_note')}>
          Only the tip. Leave empty if there wasn't one.
        </p>
        <input
          id={id('tip')}
          type="number"
          inputMode="decimal"
          min={0}
          step="0.01"
          value={value.tip}
          onChange={(e) => set('tip', e.target.value)}
          disabled={disabled}
          aria-describedby={id('tip_note')}
        />
      </div>

      {total !== null && <p className="money-total">{total}</p>}

      <label className="checkbox-row" htmlFor={id('price_changed')}>
        <input
          id={id('price_changed')}
          type="checkbox"
          checked={value.changed}
          onChange={(e) => set('changed', e.target.checked)}
          disabled={disabled}
        />
        The price changed from what I told them
      </label>

      {value.changed && (
        <div className="field money-told">
          <label htmlFor={id('quoted_price')}>What you told them before (€)</label>
          <p className="field-note" id={id('quoted_price_note')}>
            Before the groom, without any tip.
          </p>
          <input
            id={id('quoted_price')}
            type="number"
            inputMode="decimal"
            min={0}
            step="0.01"
            value={value.told}
            onChange={(e) => set('told', e.target.value)}
            disabled={disabled}
            aria-describedby={`${id('quoted_price_note')}${warning !== null ? ` ${id('money_warning')}` : ''}`}
          />
        </div>
      )}

      {warning !== null && (
        <p className="money-warning" id={id('money_warning')}>
          {warning}
        </p>
      )}
    </div>
  )
}
