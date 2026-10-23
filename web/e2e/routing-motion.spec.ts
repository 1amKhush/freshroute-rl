import { test, expect, type Page } from '@playwright/test'
import type { Decision } from '../src/types'

async function openReplay(page: Page) {
  await page.goto('/')
  await expect(page.locator('.step-label')).toHaveText('#001')
  const response = await page.request.get('/demo/decisions.jsonl')
  return (await response.text()).trim().split('\n').map(line => JSON.parse(line) as Decision)
}

async function seek(page: Page, step: number) {
  await page.getByRole('slider', { name: 'Replay position' }).fill(String(step))
  await expect(page.locator('.step-label')).toHaveText(`#${String(step + 1).padStart(3, '0')}`)
}

// Assert visible packet geometry against the selected SVG route, not a guessed
// destination or generated demonstration trajectory.
async function packetGeometry(page: Page, selector: string) {
  return page.locator('.topology-panel').evaluate((panel, selector) => {
    const packet = panel.querySelector<SVGGElement>(selector)!
    const path = panel.querySelector<SVGPathElement>('.route.selected')!
    const position = new DOMMatrix(getComputedStyle(packet).transform)
    const length = path.getTotalLength()
    const points = Array.from({ length: 301 }, (_, i) => path.getPointAtLength(length * i / 300))
    const distance = Math.min(...points.map(point => Math.hypot(point.x - position.e, point.y - position.f)))
    const end = path.getPointAtLength(length)
    return { x: position.e, y: position.f, distance, destination: end.x, opacity: Number(getComputedStyle(packet).opacity) }
  }, selector)
}

test('a real read travels to the selected replica, pauses, and returns along its route', async ({ page }) => {
  const rows = await openReplay(page)
  const row = rows[0]
  const panel = page.locator('.topology-panel')
  await page.getByRole('button', { name: 'Animate this read', exact: true }).click()
  await expect(panel).toHaveAttribute('data-phase', '2')
  await page.getByRole('button', { name: 'Pause read animation' }).click()
  await expect(panel).toHaveAttribute('data-motion', 'paused')
  const outgoing = await packetGeometry(page, '.request-packet')
  expect(outgoing.destination).toBe(100 + row.action * 200)
  expect(outgoing.distance).toBeLessThan(2)
  expect(outgoing.opacity).toBe(1)
  const before = await panel.evaluate(el => el.getAnimations({ subtree: true }).map(animation => animation.currentTime))
  await page.waitForTimeout(150)
  expect(await panel.evaluate(el => el.getAnimations({ subtree: true }).map(animation => animation.currentTime))).toEqual(before)
  await page.getByRole('button', { name: 'Resume read animation' }).click()
  await expect(panel).toHaveAttribute('data-phase', '4')
  await page.getByRole('button', { name: 'Pause read animation' }).click()
  const incoming = await packetGeometry(page, '.response-packet')
  expect(incoming.distance).toBeLessThan(2)
  expect(incoming.opacity).toBe(1)
  await page.getByRole('button', { name: 'Resume read animation' }).click()
  await expect(panel).toHaveAttribute('data-motion', 'finished')
  await expect(page.getByLabel('Read walkthrough')).toContainText('Fresh data returned')
  await expect(page.getByLabel('Read walkthrough')).toContainText(`reward ${row.reward.toFixed(3)}`)
  await expect(page.locator('.step-label')).toHaveText('#001')
})

test('stale, timed out, and offline reads explain the actual recorded outcome', async ({ page }) => {
  const rows = await openReplay(page)
  for (const kind of ['stale', 'timeout', 'offline'] as const) {
    const row = rows.find(row => kind === 'stale' ? row.outcome.freshness_violation : kind === 'timeout' ? row.outcome.timeout : row.outcome.unavailable)!
    expect(row).toBeTruthy()
    await seek(page, row.step)
    await expect(page.getByLabel('Read walkthrough')).toContainText(kind === 'stale' ? 'Stale data returned' : kind === 'timeout' ? 'Deadline exceeded' : 'Replica unavailable')
    await expect(page.locator('.reward-total strong')).toHaveText(row.reward.toFixed(3))
    await page.getByRole('button', { name: 'Animate this read', exact: true }).click()
    await expect(page.locator('.topology-panel')).toHaveAttribute('data-phase', '4')
    await page.getByRole('button', { name: 'Pause read animation' }).click()
    const returned = await packetGeometry(page, '.response-packet')
    expect(returned.opacity).toBe(kind === 'stale' ? 1 : 0)
    await expect(page.getByLabel('Read walkthrough')).toContainText(kind === 'stale' ? `${row.outcome.staleness_ms!.toFixed(0)} ms returned data lag` : 'No successful data response')
  }
})

test('motion pause stops replay advancement and seeking cancels the preceding request', async ({ page }) => {
  await openReplay(page)
  await page.getByRole('combobox', { name: 'Playback speed' }).selectOption('800')
  await page.getByRole('button', { name: '▶ Play', exact: true }).click()
  await expect(page.locator('.step-label')).toHaveText('#002')
  await page.getByRole('button', { name: 'Pause read animation' }).click()
  const step = await page.locator('.step-label').textContent()
  await expect(page.getByRole('button', { name: '▶ Play', exact: true })).toBeVisible()
  await page.waitForTimeout(1000)
  await expect(page.locator('.step-label')).toHaveText(step!)
  for (const destination of [70, 159, 0, 21]) await seek(page, destination)
  await expect(page.locator('.topology-panel')).toHaveAttribute('data-request', '22')
  await expect(page.locator('.topology-panel')).toHaveAttribute('data-motion', 'finished')
  await expect.poll(() => page.locator('.topology-panel').evaluate(el => el.getAnimations({ subtree: true }).filter(animation => animation.playState === 'running').length)).toBe(0)
  await page.getByRole('button', { name: 'Animate this read', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Show next state' }).check()
  await expect(page.locator('.topology-panel')).toHaveAttribute('data-motion', 'off')
  await expect(page.getByLabel('Read walkthrough')).toContainText('highlighted route belongs to the preceding read')
  await expect(page.getByRole('button', { name: 'Animate this read', exact: true })).toBeDisabled()
})

test('motion can be disabled locally and when the system preference changes', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await openReplay(page)
  await page.getByRole('button', { name: 'Animate this read', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Enable routing motion' }).uncheck()
  await expect(page.locator('.topology-panel')).toHaveAttribute('data-motion', 'off')
  await expect(page.getByLabel('Read walkthrough')).toContainText('Motion off')
  await page.getByRole('checkbox', { name: 'Enable routing motion' }).check()
  await page.getByRole('button', { name: 'Animate this read', exact: true }).click()
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(page.getByRole('checkbox', { name: 'Enable routing motion' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Animate this read', exact: true })).toBeDisabled()
  await expect(page.locator('.topology-panel')).toHaveAttribute('data-motion', 'off')
  await expect(page.getByLabel('Read walkthrough')).toContainText('Reduced motion')
  expect(await page.locator('.topology-panel').evaluate(el => el.getAnimations({ subtree: true }).length)).toBe(0)
  await seek(page, 16)
  await expect(page.getByLabel('Read walkthrough')).toContainText('Stale data returned')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
})
