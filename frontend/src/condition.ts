/**
 * Coat condition on arrival, 0 (worst) … 5 (best) — the visit's `condition_score`
 * (#123 locked the polarity). One word per score, used at capture, in visit
 * edits and on the dashboard, so the groomer reads the same word everywhere.
 * Change the words here only (2026-11-14: first set, to be checked with him).
 */
export const CONDITION_WORDS = ['Matted', 'Rough', 'Tangled', 'OK', 'Good', 'Great'] as const

export function conditionWord(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return CONDITION_WORDS[score] ?? String(score)
}
