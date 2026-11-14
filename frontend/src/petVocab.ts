/**
 * Words for the pet profile's fixed lists. The codes are the API's (and the
 * database CHECKs', src/muttmetrics/pet_vocab.py); only the labels live here,
 * so they can change after the groomer has tried them without touching data.
 * Why each field exists: docs/architecture/pet-data.md.
 */

import type { Species } from './api'

export type Option<V extends string> = { value: V; label: string; hint?: string }

export const COAT_TYPES: Record<Species, Option<string>[]> = {
  dog: [
    { value: 'smooth', label: 'Smooth', hint: 'Short and close: Boxer, Frenchie' },
    { value: 'double', label: 'Double', hint: 'Undercoat, sheds: Husky, Golden, Lab' },
    { value: 'curly', label: 'Curly', hint: 'Keeps growing, mats: Poodle, doodles' },
    { value: 'wire', label: 'Wire', hint: 'Harsh, hand stripping: terriers, Schnauzer' },
    { value: 'silky', label: 'Long & silky', hint: 'Yorkie, Maltese, Shih Tzu' },
    { value: 'combination', label: 'Combination', hint: 'Short body, feathering: Cocker, Setter' },
  ],
  cat: [
    { value: 'short', label: 'Short-haired' },
    { value: 'long', label: 'Long-haired' },
  ],
}

export function coatTypeLabel(species: Species, code: string | null): string | null {
  if (code === null) return null
  return COAT_TYPES[species].find((o) => o.value === code)?.label ?? code
}

/** 1 thin .. 3 thick (stored as a number). */
export const COAT_THICKNESS: Option<string>[] = [
  { value: '1', label: 'Thin' },
  { value: '2', label: 'Normal' },
  { value: '3', label: 'Thick' },
]

/** Chips say S / M / L / XL, the salon's price bands; sentences use the words. */
export const SIZES: Option<string>[] = [
  { value: 's', label: 'S', hint: 'Small' },
  { value: 'm', label: 'M', hint: 'Medium' },
  { value: 'l', label: 'L', hint: 'Large' },
  { value: 'xl', label: 'XL', hint: 'Extra large' },
]

export function sizeLabel(code: string | null): string | null {
  if (code === null) return null
  return SIZES.find((o) => o.value === code)?.hint ?? code
}

/** 1 easy .. 5 very difficult (stored as a number). Ask the groomer. */
export const HANDLING: Option<string>[] = [
  { value: '1', label: 'Easy' },
  { value: '2', label: 'Calm' },
  { value: '3', label: 'Some fuss' },
  { value: '4', label: 'Difficult' },
  { value: '5', label: 'Very difficult' },
]

export function handlingLabel(score: number | null): string | null {
  if (score === null) return null
  return HANDLING.find((o) => o.value === String(score))?.label ?? String(score)
}

/** Blank = nobody checked; there's no "unknown" value. */
export const SEXES: Option<string>[] = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
]
