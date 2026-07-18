import { expect, test, type Route } from '@playwright/test'

const json = (route: Route, body: unknown, status = 200) => route.fulfill({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

const unexpected = (route: Route, pathname: string) => json(
  route,
  { detail: `Unexpected smoke request: ${route.request().method()} ${pathname}` },
  500,
)

const wrappedBody = (days: number) => ({
  creator_id: 71,
  days,
  totals: {
    streams: 12,
    hours_streamed: 48.5,
    messages: 40000,
    active_chatters: 320,
  },
  top_chatters: [{
    rank: 1,
    chatter_id: 301,
    nick: 'chatterOne',
    total_messages: 5000,
    streams_attended: 12,
  }],
  top_moments: [{
    stream_id: 501,
    stream_title: 'PixelKobra plays ranked',
    twitch_id: 'vod-501',
    bucket_minute: '2026-07-14T20:15:00Z',
    offset_seconds: 900,
    ratio: 4.2,
    message_count: 210,
  }],
  top_copypastas: [{
    message_text_id: 9001,
    text: 'OMEGALUL nice job chat',
    usage_count: 340,
    stream_count: 8,
  }],
  top_emotes: [{
    emote_id: 42,
    name: 'PogChamp',
    source: 'twitch',
    usage: 900,
    chatter_reach: 210,
  }],
})

test('creator wrapped: renders the recap, and the window pill re-queries', async ({ page }) => {
  const requestedDays: string[] = []

  await page.route('**/api/**', async (route) => {
    const { pathname, searchParams } = new URL(route.request().url())
    if (pathname !== '/api/creators/71/wrapped') return unexpected(route, pathname)
    const days = searchParams.get('days') ?? ''
    requestedDays.push(days)
    if (days === '30' || days === '7') return json(route, wrappedBody(Number(days)))
    return unexpected(route, pathname)
  })

  await page.goto('/creator/71/wrapped')
  await expect(page.getByRole('heading', { name: 'Creator Wrapped' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()
  await expect(page.getByText('OMEGALUL nice job chat')).toBeVisible()
  await expect(page.getByText('PogChamp')).toBeVisible()

  const sevenDays = page.getByRole('button', { name: '7 days' })
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'false')
  await sevenDays.click()
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'true')

  await expect.poll(() => requestedDays).toEqual(['30', '7'])
})

test('creator wrapped: an unparseable creator id 404s instead of faking an empty recap', async ({ page }) => {
  let apiRequests = 0
  await page.route('**/api/**', async (route) => {
    apiRequests += 1
    return unexpected(route, new URL(route.request().url()).pathname)
  })

  await page.goto('/creator/not-a-number/wrapped')

  await expect(page.getByText('404 — Target not found')).toBeVisible()
  await expect(page.getByText('Nothing to wrap yet')).not.toBeVisible()
  expect(apiRequests).toBe(0)
})
