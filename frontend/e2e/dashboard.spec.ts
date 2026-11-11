import { expect, test } from '@playwright/test'

test('dashboard: fixture week shows hand-computed Grooms', async ({ page }) => {
  await page.goto('/')

  // Land on week mode even if a prior session left All/Month selected.
  await page.getByRole('button', { name: 'Week', exact: true }).click()

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
    .locator('.tw-stat')
    .filter({ has: page.getByRole('heading', { name: 'Grooms', exact: true }) })
    .locator('.tw-stat-value')

  // The hero card: its heading is "Take-home", the big number is the value.
  const takeHome = headlines.locator('.tw-hero-value')

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

test('dashboard: All time mode shows lifetime headlines', async ({ page }) => {
  await page.goto('/')
  // exact: the week view's "… All time →" link is a button too
  await page.getByRole('button', { name: 'All time', exact: true }).click()

  const headlines = page.getByRole('region', { name: 'All-time headlines' })
  const empty = page.getByRole('region', { name: 'Empty period' })
  await expect(headlines.or(empty)).toBeVisible({ timeout: 15_000 })

  if (await headlines.isVisible()) {
    await expect(page.getByRole('heading', { name: 'All time' })).toBeVisible()
    await expect(headlines.locator('.tw-hero-value')).not.toHaveText('')
    // Lifetime numbers live only in this hero: no link back to itself.
    await expect(page.locator('.tw-alltime-link')).toHaveCount(0)
  }
})

test('dashboard: the week view links to All time instead of repeating it', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Week', exact: true }).click()

  const link = page.locator('.tw-alltime-link')
  await expect(link).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('region', { name: 'Since day one' })).toHaveCount(0)

  await link.click()
  await expect(page.getByRole('heading', { name: 'All time' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'All-time headlines' })).toBeVisible()
})
