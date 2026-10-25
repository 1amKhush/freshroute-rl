import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('replay controls preserve actual decision values and stop at the end', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Inside this decision' })).toBeVisible()
  const first = await page.evaluate(async () => JSON.parse((await (await fetch('/demo/decisions.jsonl')).text()).split('\n')[0]))
  await expect(page.locator('.selected-q strong')).toHaveText(first.q_values[first.action].toFixed(3))
  await expect(page.locator('.reward-total strong')).toHaveText(first.reward.toFixed(3))
  await page.getByRole('button', { name: 'Next decision' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('.step-label')).toHaveText('#002')
  await page.getByRole('button', { name: 'Previous decision' }).click()
  await expect(page.locator('.step-label')).toHaveText('#001')
  await page.getByRole('slider', { name: 'Replay position' }).focus()
  await page.keyboard.press('End')
  await expect(page.locator('.step-label')).toHaveText('#160')
  await expect(page.getByRole('button', { name: 'Next decision' })).toBeDisabled()
  await expect(page.getByRole('button', { name: '▶ Play' })).toBeDisabled()
  await page.getByRole('button', { name: 'Reset', exact: true }).click()
  await expect(page.locator('.step-label')).toHaveText('#001')
  await page.getByRole('combobox', { name: 'Event filter' }).selectOption('stale')
  await expect(page.locator('.step-label')).toHaveText('#017')
  await page.getByRole('combobox', { name: 'Event filter' }).selectOption('all')
  await expect(page.locator('.step-label')).toHaveText('#001')
  await page.getByRole('button', { name: 'Training & evaluation' }).click()
  await expect(page.getByRole('table')).toBeVisible()
  expect(errors).toEqual([])
})

test('invalid trace is rejected and mobile layout remains usable', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  await page.setViewportSize({ width: 390, height: 844 }); await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await expect(page.locator('.step-label')).toHaveText('#001')
  const first = await page.evaluate(async () => JSON.parse((await (await fetch('/demo/decisions.jsonl')).text()).split('\n')[0]))
  const invalid = [
    { schema_version: 99 },
    { ...first, q_values: [0, 1] },
    { ...first, outcome: { ...first.outcome, reward_terms: { ...first.outcome.reward_terms, latency: 'invalid' } } },
    { ...first, outcome: { ...first.outcome, reward_terms: { ...first.outcome.reward_terms, failure: -1 } } },
    { ...first, outcome: { ...first.outcome, reward_terms: { ...first.outcome.reward_terms, extra: 'invalid' } } },
    { ...first, outcome: { ...first.outcome, reward_terms: { ...first.outcome.reward_terms, extra: -1 } } },
    { ...first, outcome: { ...first.outcome, transport_ok: 'yes' } },
  ]
  for (const row of invalid) {
    await page.getByLabel('Open decision trace').setInputFiles({ name: 'invalid.jsonl', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(row)) })
    await expect(page.getByRole('alert')).toContainText('Could not open trace')
    await expect(page.locator('.step-label')).toHaveText('#001')
    await expect(page.locator('.selected-q strong')).toHaveText(first.q_values[first.action].toFixed(3))
  }
  await page.getByLabel('Open decision trace').setInputFiles({ name: 'valid.jsonl', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(first)) })
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Next decision' })).toBeDisabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  expect(errors).toEqual([])
})

test('leaving during session creation deletes the abandoned server session', async ({ page, request }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Live laboratory' }).click()
  let release!: () => void
  let capture!: (id: string) => void
  const heldResponse = new Promise<void>(resolve => { release = resolve })
  const created = new Promise<string>(resolve => { capture = resolve })
  let sessionId: string | undefined
  let stepRequests = 0
  await page.route('**/api/sessions/*/step', route => { stepRequests++; return route.continue() })
  await page.route('**/api/sessions', async route => {
    const response = await route.fetch()
    sessionId = (await response.json()).id
    capture(sessionId!)
    await heldResponse
    await route.fulfill({ response })
  })
  try {
    await page.getByRole('button', { name: 'Start session' }).click()
    await created
    await page.getByRole('button', { name: 'Training & evaluation' }).click()
    release()
    await expect.poll(async () => (await request.get(`/api/sessions/${sessionId}/trace`)).status()).toBe(404)
    expect(stepRequests).toBe(0)
    await page.getByRole('button', { name: 'Live laboratory' }).click()
    await expect(page.getByRole('button', { name: 'Start session' })).toBeEnabled()
  } finally {
    release()
    if (sessionId) await request.delete(`/api/sessions/${sessionId}`)
  }
})

test('live DQN routing, fault injection, and same-snapshot branches use the real API', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Live laboratory' }).click()
  await page.getByLabel('Live model').selectOption('dqn')
  await page.getByRole('button', { name: 'Start session' }).click()
  await expect(page.locator('.step-label')).toHaveText('#001')
  await page.getByRole('button', { name: 'Step live request' }).click()
  await expect(page.locator('.step-label')).toHaveText('#002')
  await page.getByRole('button', { name: 'Apply fault' }).click()
  await expect(page.getByRole('status')).toContainText('applied to Mumbai')
  await page.getByRole('button', { name: 'Step live request' }).click()
  await expect(page.locator('.step-label')).toHaveText('#003')
  await expect(page.locator('.replica').filter({ has: page.getByRole('heading', { name: 'Mumbai', exact: true }) })).toContainText('Offline')
  await page.getByRole('button', { name: 'Compare all choices from this snapshot' }).click()
  await expect(page.getByRole('heading', { name: 'What if we chose another replica?' })).toBeVisible()
  await expect(page.locator('.branch-grid article')).toHaveCount(3)
  await expect(page.locator('.step-label')).toHaveText('#003')
  const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(accessibility.violations).toEqual([])
  await page.getByRole('button', { name: 'End session', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Start session' })).toBeVisible()
})

test('replay has no WCAG A or AA accessibility violations', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.step-label')).toHaveText('#001')
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(results.violations).toEqual([])
})
