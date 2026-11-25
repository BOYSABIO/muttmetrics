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
  await expect(service.locator('option')).toHaveCount(8, { timeout: 15_000 }) // blank + 7 seeded
  await service.selectOption({ index: 1 })
  await page.locator('#final_price').fill('55')

  // Price didn't change: the quote is saved as the price.
  const posted = page.waitForRequest((r) => r.method() === 'POST' && /\/visits$/.test(r.url()))
  await page.getByRole('button', { name: 'Save visit' }).click()
  const body = (await posted).postDataJSON()
  expect(body.final_price).toBe(55)
  expect(body.quoted_price).toBe(55)
  expect(body.tip).toBeUndefined()

  await expect(page.getByRole('status')).toContainText(/Saved SynDog Fluff/i, {
    timeout: 15_000,
  })
})

test('capture: money boxes catch a tip typed into the price', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'New visit' }).click()
  await page.locator('#dog_search').fill('SynDog Fluff')
  await page.getByRole('button', { name: /SynDog Fluff/i }).click()
  await page.getByRole('button', { name: 'Continue' }).click()
  await page.locator('#actual_minutes').fill('40')
  await page.getByRole('button', { name: 'Continue' }).click()

  const service = page.locator('#service_id')
  await expect(service.locator('option')).toHaveCount(8, { timeout: 15_000 })
  await service.selectOption({ index: 1 })

  // The mix-up: what the customer paid in total typed as the price.
  await page.getByLabel('Price for the groom (€)').fill('68')
  await page.getByLabel('Tip (€)').fill('8')
  await expect(page.locator('.money-total')).toHaveText(
    'Customer paid €76 in total · €68 groom + €8 tip',
  )

  // What they were told is hidden until the price changed.
  await expect(page.locator('#quoted_price')).toHaveCount(0)
  await page.getByLabel('The price changed from what I told them').check()
  await page.getByLabel('What you told them before (€)').fill('60')
  await expect(page.locator('.money-warning')).toContainText('it would count twice')

  // Fixed: the price without the tip, and a real change from what was said.
  await page.getByLabel('Price for the groom (€)').fill('60')
  await page.getByLabel('What you told them before (€)').fill('50')
  await expect(page.locator('.money-warning')).toHaveCount(0)
  await expect(page.locator('.money-total')).toHaveText(
    'Customer paid €68 in total · €60 groom + €8 tip',
  )

  const posted = page.waitForRequest((r) => r.method() === 'POST' && /\/visits$/.test(r.url()))
  await page.getByRole('button', { name: 'Save visit' }).click()
  const body = (await posted).postDataJSON()
  expect(body.final_price).toBe(60)
  expect(body.tip).toBe(8)
  expect(body.quoted_price).toBe(50)

  await expect(page.getByRole('status')).toContainText(/Saved SynDog Fluff/i, {
    timeout: 15_000,
  })
})
