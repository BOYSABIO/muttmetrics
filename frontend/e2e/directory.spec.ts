import { expect, test } from '@playwright/test'

test('directory: edit weight → reload → still there', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Clients' }).click()

  await page.locator('#directory_dog_search').fill('SynDog Fluff')
  await page.getByRole('button', { name: 'SynDog Fluff' }).click()

  const weight = page.locator('#dir_weight')
  await expect(weight).toBeVisible({ timeout: 15_000 })
  await weight.fill('12.5')
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('status')).toContainText(/Saved/i)

  await page.reload()
  await page.getByRole('button', { name: 'Clients' }).click()
  await page.locator('#directory_dog_search').fill('SynDog Fluff')
  await page.getByRole('button', { name: 'SynDog Fluff' }).click()

  await expect(page.locator('#dir_weight')).toHaveValue('12.5')
})
