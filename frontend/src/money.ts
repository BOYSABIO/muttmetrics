/**
 * The money on a visit, and what each box means (0.10.1). Used by the
 * new-visit form and the visit edit form, so both read the same way.
 *
 * - price → `visit.final_price`: what the groom cost. Never includes the tip.
 * - tip → `visit.tip`: the tip on its own. Empty means there wasn't one.
 * - told → `visit.quoted_price`: what the groomer told the customer before
 *   the groom. Only asked for when the price changed on the day; otherwise
 *   the quote is saved as the price.
 *
 * Take-home is price + tip, so a tip typed into the price box counts twice.
 * The form shows the total the customer paid as a check, and warns when one
 * box is exactly the other plus the tip.
 */

export type Money = {
  price: string
  tip: string
  /** The price changed from what the customer was told. */
  changed: boolean
  told: string
}

/** null when empty, NaN when not a number ≥ 0. Accepts "45,50". */
export function parseMoney(s: string): number | null {
  const t = s.trim().replace(',', '.')
  if (t === '') return null
  const n = Number(t)
  return Number.isFinite(n) && n >= 0 ? n : Number.NaN
}

function isAmount(n: number | null): n is number {
  return n !== null && !Number.isNaN(n)
}

/** Money is compared to the cent, so 45 + 5 equals 50 even with float noise. */
function same(a: number, b: number): boolean {
  return Math.abs(a - b) < 0.005
}

/** "€60" or "€55.50": cents only when there are some. */
export function euro(n: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: Number.isInteger(n) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(n)
}

/** What goes in `quoted_price`: what they were told, else the price itself. */
export function quoteToSave(m: Money): number | null {
  return m.changed ? parseMoney(m.told) : parseMoney(m.price)
}

/** For an existing visit: did the price change from the quote? */
export function changedFrom(quoted: number | null, final: number | null): boolean {
  return quoted !== null && (final === null || !same(quoted, final))
}

/** The check under the tip: what the customer handed over in total. */
export function totalLine(m: Money): string | null {
  const price = parseMoney(m.price)
  const tip = parseMoney(m.tip)
  if (!isAmount(price) || Number.isNaN(tip)) return null
  if (tip === null || tip === 0) return `Customer paid ${euro(price)} in total · no tip`
  return `Customer paid ${euro(price + tip)} in total · ${euro(price)} groom + ${euro(tip)} tip`
}

/**
 * A gentle note when the boxes look mixed up; null when they look fine. Only
 * ever "if": a real €5 rise with a €5 tip looks the same as the mix-up.
 */
export function moneyWarning(m: Money): string | null {
  if (!m.changed) return null
  const price = parseMoney(m.price)
  const told = parseMoney(m.told)
  const tip = parseMoney(m.tip)
  if (!isAmount(price) || !isAmount(told)) return null
  if (same(told, price)) {
    return "That's the same as the price. If it didn't change, untick the box."
  }
  if (!isAmount(tip) || tip === 0) return null
  if (same(told, price + tip)) {
    return "That's exactly the price plus the tip. If it's what they paid in total, put what you told them before the groom instead."
  }
  if (same(price, told + tip)) {
    return "The price is exactly what you told them plus the tip. If the tip is in the price too, take it out: it would count twice."
  }
  return null
}
