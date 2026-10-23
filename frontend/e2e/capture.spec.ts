import { expect, test } from '@playwright/test'

test('capture: search dog → service → Saved', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('button', { name: 'New visit' }).click()

  await page.locator('#dog_search').fill('SynDog Fluff')
  await page.getByRole('button', { name: /SynDog Fluff/i }).click()

  // Step 1 — skip optional photo
  await page.getByRole('button', { name: 'Continue' }).click()

  // Step 2 — type minutes (skip timer)
  await page.locator('#actual_minutes').fill('45')
  await page.getByRole('button', { name: 'Continue' }).click()

  // Step 3 — pick first real service + price
  const service = page.locator('#service_id')
  await expect(service.locator('option')).toHaveCount(6, { timeout: 15_000 }) // blank + 5 seeded
  await service.selectOption({ index: 1 })
  await page.locator('#final_price').fill('55')
  await page.getByRole('button', { name: 'Save visit' }).click()

  await expect(page.getByRole('status')).toContainText(/Saved SynDog Fluff/i, {
    timeout: 15_000,
  })
})
