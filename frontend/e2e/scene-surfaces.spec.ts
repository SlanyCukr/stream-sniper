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

test('highlights: renders the hype wall and loads a second page on demand', async ({ page }) => {
  let highlightsRequests = 0

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname, searchParams } = new URL(request.url())
    if (pathname !== '/api/scene/highlights') return unexpected(route, pathname)

    highlightsRequests += 1
    const offset = Number(searchParams.get('offset') ?? '0')
    if (offset === 0) {
      return json(route, {
        window: 'all',
        sort: 'hype',
        has_more: true,
        items: [{
          stream_id: 501,
          stream_title: 'PixelKobra plays ranked',
          twitch_id: 'vod-501',
          creator_id: 71,
          creator_nick: 'pixelkobra',
          creator_display_name: 'PixelKobra',
          bucket_minute: '2026-07-14T20:15:00Z',
          offset_seconds: 900,
          ratio: 4.2,
          message_count: 210,
          unique_chatters: 88,
          sub_share: 0.12,
          emote_share: 0.4,
          top_phrases: [{ phrase: 'POGGERS', count: 40, lift: 3.1 }],
          sample_messages: [{ text: 'no way he clutched that', count: 3 }],
          clip_url: null,
          review_status: null,
        }],
      })
    }
    return json(route, {
      window: 'all',
      sort: 'hype',
      has_more: false,
      items: [{
        stream_id: 502,
        stream_title: 'NightOwlCZ late night just chatting',
        twitch_id: 'vod-502',
        creator_id: 72,
        creator_nick: 'nightowlcz',
        creator_display_name: 'NightOwlCZ',
        bucket_minute: '2026-07-14T23:05:00Z',
        offset_seconds: 500,
        ratio: 2.1,
        message_count: 95,
        unique_chatters: 40,
        sub_share: null,
        emote_share: null,
        top_phrases: null,
        sample_messages: null,
        clip_url: null,
        review_status: 'bookmarked',
      }],
    })
  })

  await page.goto('/highlights')
  await expect(page.getByRole('heading', { name: 'Highlights' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'PixelKobra', exact: true })).toBeVisible()
  await expect(page.getByText('PixelKobra plays ranked')).toBeVisible()

  await page.getByRole('button', { name: 'Load more' }).click()

  await expect(page.getByRole('link', { name: 'NightOwlCZ', exact: true })).toBeVisible()
  await expect(page.getByText('NightOwlCZ late night just chatting')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()
  expect(highlightsRequests).toBe(2)
})

test('rankings: renders the power-rankings table and loads a second page on demand', async ({ page }) => {
  let rankingsRequests = 0

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname, searchParams } = new URL(request.url())
    if (pathname !== '/api/scene/chatter-rankings') return unexpected(route, pathname)

    rankingsRequests += 1
    const offset = Number(searchParams.get('offset') ?? '0')
    if (offset === 0) {
      return json(route, {
        window: 'all',
        has_more: true,
        items: [{
          rank: 1,
          chatter_id: 301,
          nick: 'chatterOne',
          total_messages: 5000,
          streams_attended: 42,
          creators_visited: 6,
          home_channel: {
            creator_id: 71,
            creator_nick: 'pixelkobra',
            creator_display_name: 'PixelKobra',
            messages: 3000,
            share: 0.6,
          },
        }],
      })
    }
    return json(route, {
      window: 'all',
      has_more: false,
      items: [{
        rank: 26,
        chatter_id: 302,
        nick: 'chatterTwo',
        total_messages: 900,
        streams_attended: 10,
        creators_visited: 2,
        home_channel: null,
      }],
    })
  })

  await page.goto('/rankings')
  await expect(page.getByRole('heading', { name: 'Power rankings' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()

  await page.getByRole('button', { name: 'Load more' }).click()

  await expect(page.getByRole('link', { name: 'chatterTwo' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()
  expect(rankingsRequests).toBe(2)
})

test('trending: renders both the copypasta and emote boards from the default window', async ({ page }) => {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    if (pathname === '/api/scene/trending/copypastas') {
      return json(route, {
        window: 7,
        items: [{
          message_text_id: 9001,
          text: 'OMEGALUL nice job chat',
          current_usage: 340,
          prior_usage: 120,
          delta_pct: 183,
          trend: 'rising',
          stream_count: 8,
          creator_count: 5,
          first_seen: '2026-07-10T09:00:00Z',
        }],
      })
    }
    if (pathname === '/api/scene/trending/emotes') {
      return json(route, {
        window: 7,
        items: [{
          emote_id: 42,
          name: 'PogChamp',
          source: 'twitch',
          provider_id: 'poggers-42',
          current_usage: 900,
          prior_usage: 950,
          delta_pct: -5,
          trend: 'falling',
          chatter_reach: 210,
          first_seen: '2026-05-01T00:00:00Z',
        }],
      })
    }
    return unexpected(route, pathname)
  })

  await page.goto('/trending')
  await expect(page.getByRole('heading', { name: 'Trending' })).toBeVisible()
  await expect(page.getByText('OMEGALUL nice job chat')).toBeVisible()
  await expect(page.getByText('PogChamp')).toBeVisible()
})

test('wrapped: renders the scene recap for the default 30-day window', async ({ page }) => {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname, searchParams } = new URL(request.url())
    if (pathname !== '/api/scene/wrapped') return unexpected(route, pathname)
    expect(searchParams.get('days')).toBe('30')
    return json(route, {
      days: 30,
      totals: {
        streams: 64,
        hours_streamed: 210.5,
        messages: 128000,
        active_chatters: 940,
        creators_active: 12,
      },
      top_creators: [{
        rank: 1,
        creator_id: 71,
        nick: 'pixelkobra',
        display_name: 'PixelKobra',
        profile_image_url: null,
        total_messages: 40000,
        streams: 20,
        hours_streamed: 60,
        msgs_per_min: 33.3,
        peak_viewers: 1200,
      }],
      top_chatters: [{
        rank: 1,
        chatter_id: 301,
        nick: 'chatterOne',
        total_messages: 5000,
        streams_attended: 42,
        creators_visited: 6,
        home_creator_display_name: 'PixelKobra',
      }],
      top_moments: [{
        stream_id: 501,
        stream_title: 'PixelKobra plays ranked',
        twitch_id: 'vod-501',
        creator_display_name: 'PixelKobra',
        bucket_minute: '2026-07-14T20:15:00Z',
        offset_seconds: 900,
        ratio: 4.2,
        message_count: 210,
      }],
      top_copypastas: [{
        message_text_id: 9001,
        text: 'OMEGALUL nice job chat',
        usage_count: 340,
        creator_count: 5,
        stream_count: 8,
      }],
      top_emotes: [{
        emote_id: 42,
        name: 'PogChamp',
        source: 'twitch',
        usage: 900,
        chatter_reach: 210,
      }],
      notable_events: [{
        event_type: 'went_live',
        occurred_at: '2026-07-14T18:00:00Z',
        title: 'PixelKobra went live',
        summary: 'Started streaming ranked queue.',
        creator_display_name: 'PixelKobra',
      }],
    })
  })

  await page.goto('/wrapped')
  await expect(page.getByRole('heading', { name: 'Scene Wrapped' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'PixelKobra' }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()
  await expect(page.getByText('OMEGALUL nice job chat')).toBeVisible()
})

test('radar: renders a live channel velocity card from the polling feed', async ({ page }) => {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    if (pathname !== '/api/scene/radar') return unexpected(route, pathname)
    return json(route, {
      generated_at: '2026-07-18T20:00:00Z',
      channels: [{
        stream_id: 501,
        creator_id: 71,
        creator_nick: 'pixelkobra',
        creator_display_name: 'PixelKobra',
        profile_image_url: null,
        stream_title: 'PixelKobra plays ranked',
        started_at: '2026-07-18T18:00:00Z',
        messages_last_minute: 140,
        unique_chatters_last_minute: 60,
        baseline_per_minute: 30,
        ratio: 4.6,
        spiking: true,
        minutes: [
          { minute: '2026-07-18T19:58:00Z', messages: 90 },
          { minute: '2026-07-18T19:59:00Z', messages: 140 },
        ],
      }],
    })
  })

  await page.goto('/radar')
  await expect(page.getByRole('heading', { name: 'Moment Radar' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'PixelKobra' })).toBeVisible()
  await expect(page.getByText('SPIKING')).toBeVisible()
})

test('radar: renders the empty state when no channel is live', async ({ page }) => {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    if (pathname !== '/api/scene/radar') return unexpected(route, pathname)
    return json(route, { generated_at: '2026-07-18T20:00:00Z', channels: [] })
  })

  await page.goto('/radar')
  await expect(page.getByRole('heading', { name: 'Moment Radar' })).toBeVisible()
  await expect(page.getByText('No one is live right now')).toBeVisible()
})
