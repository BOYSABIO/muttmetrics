import { expect, test } from '@playwright/test'

async function openFluff(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: 'Clients' }).click()
  await page.locator('#directory_dog_search').fill('SynDog Fluff')
  await page.getByRole('button', { name: 'SynDog Fluff' }).click()
  await expect(page.getByRole('heading', { name: 'SynDog Fluff' })).toBeVisible({ timeout: 15_000 })
}

test('directory: edit weight and coat → reload → still there', async ({ page }) => {
  await page.goto('/')
  await openFluff(page)

  // Coat is a Basics chip; pick one that isn't selected yet, so a re-run
  // against the same database still changes something.
  const wire = page.getByRole('button', { name: 'Wire', exact: true })
  const coat = (await wire.getAttribute('aria-pressed')) === 'true' ? 'Curly' : 'Wire'
  await page.getByRole('button', { name: coat, exact: true }).click()

  // Weight lives under the folded "More details".
  await page.locator('details.profile-more > summary').click()
  const weight = page.locator('#dir_weight')
  await expect(weight).toBeVisible()
  const kg = (await weight.inputValue()) === '12.5' ? '13.5' : '12.5'
  await weight.fill(kg)

  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('status')).toContainText(/Saved/i)
  await expect(page.locator('.profile-summary')).toContainText(coat === 'Wire' ? 'Wire' : 'Curly')

  await page.reload()
  await openFluff(page)
  await expect(page.getByRole('button', { name: coat, exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.locator('#dir_weight')).toHaveValue(kg)
})
