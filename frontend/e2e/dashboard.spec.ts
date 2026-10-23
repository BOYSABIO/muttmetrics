import { expect, test } from '@playwright/test'

test('dashboard: fixture week shows hand-computed Grooms', async ({ page }) => {
  await page.goto('/')

  // Reset if a prior session left us off "this week"
  const backToThis = page.getByRole('button', { name: 'Back to this week' })
  if (await backToThis.isVisible()) {
    await backToThis.click()
  }

  const headlines = page.getByRole('region', { name: 'Week headlines' })
  const empty = page.getByRole('region', { name: 'Empty period' })
  const periodBody = headlines.or(empty)
  const rangeLabel = page.locator('.week-nav-range')

  const grooms = headlines
    .locator('.headline-card')
    .filter({ has: page.getByRole('heading', { name: 'Grooms', exact: true }) })
    .locator('.headline-value')

  const takeHome = headlines
    .locator('.headline-card')
    .filter({ has: page.getByRole('heading', { name: 'Take-home', exact: true }) })
    .locator('.headline-value')

  // Walk back to the Syn* week (2026-03-02). Empty weeks have no headlines.
  let found = false
  for (let i = 0; i < 60; i++) {
    await expect(periodBody).toBeVisible({ timeout: 15_000 })

    if (await headlines.isVisible()) {
      const text = (await grooms.textContent())?.trim()
      if (text === '11') {
        found = true
        break
      }
    }

    const prevRange = (await rangeLabel.textContent())?.trim() ?? ''
    const prev = page.getByRole('button', { name: 'Previous week' })
    await expect(prev).toBeEnabled()
    await prev.click()
    await expect(rangeLabel).not.toHaveText(prevRange, { timeout: 15_000 })
  }

  expect(found, 'never reached fixture week with Grooms=11').toBe(true)
  await expect(grooms).toHaveText('11')
  await expect(takeHome).toContainText('633')
})
