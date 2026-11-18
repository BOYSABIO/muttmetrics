/**
 * Christmas accents (0.10.0): hats on the dogs, a string of lights, a little
 * snow. One switch, off by default, remembered on the device. Everything
 * festive hangs off `html[data-festive='on']` (festive.css), so with the
 * switch off none of it exists. Rules: docs/architecture/ui-conventions.md
 * ("Seasonal accents").
 */

const STORAGE_KEY = 'muttmetrics.festive'

let enabled = readSetting()

function readSetting(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'on'
  } catch {
    return false
  }
}

function apply(): void {
  if (typeof document === 'undefined') return
  if (enabled) document.documentElement.dataset.festive = 'on'
  else delete document.documentElement.dataset.festive
}

export function festiveEnabled(): boolean {
  return enabled
}

export function setFestiveEnabled(on: boolean): void {
  enabled = on
  try {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off')
  } catch {
    /* private mode: the choice lasts until the tab closes */
  }
  apply()
}

// On load, before the first screen is drawn.
apply()
