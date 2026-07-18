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

const highlightItem = (id: number, title: string, creator: string) => ({
  stream_id: id,
  stream_title: title,
  twitch_id: `vod-${id}`,
  creator_id: id,
  creator_nick: creator.toLowerCase(),
  creator_display_name: creator,
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
})

test('highlights: paginates, then window and sort pills re-query and reset the wall', async ({ page }) => {
  const calls: Array<{ window: string, sort: string, offset: number }> = []
  // The window-switch response is gated so the test can observe the in-flight
  // state: the wall must show the loading spinner, not the empty state and not
  // the previous window's cards.
  let releaseWindowSwitch = () => {}
  const windowSwitchGate = new Promise<void>((resolve) => { releaseWindowSwitch = resolve })

  await page.route('**/api/**', async (route) => {
    const { pathname, searchParams } = new URL(route.request().url())
    if (pathname !== '/api/scene/highlights') return unexpected(route, pathname)

    const windowKey = searchParams.get('window') ?? 'all'
    const sort = searchParams.get('sort') ?? 'hype'
    const offset = Number(searchParams.get('offset') ?? '0')
    calls.push({ window: windowKey, sort, offset })

    if (windowKey === 'all' && sort === 'hype' && offset === 0) {
      return json(route, {
        window: windowKey,
        sort,
        has_more: true,
        items: [highlightItem(501, 'PixelKobra plays ranked', 'PixelKobra')],
      })
    }
    if (windowKey === 'all' && sort === 'hype') {
      return json(route, {
        window: windowKey,
        sort,
        has_more: false,
        items: [highlightItem(502, 'NightOwlCZ late night just chatting', 'NightOwlCZ')],
      })
    }
    if (windowKey === '7' && sort === 'hype' && offset === 0) {
      await windowSwitchGate
      return json(route, {
        window: windowKey,
        sort,
        has_more: false,
        items: [highlightItem(503, 'Weekly window hype moment', 'WeeklyHero')],
      })
    }
    if (windowKey === '7' && sort === 'recent' && offset === 0) {
      return json(route, {
        window: windowKey,
        sort,
        has_more: false,
        items: [highlightItem(504, 'Freshest moment this week', 'FreshFace')],
      })
    }
    return unexpected(route, pathname)
  })

  await page.goto('/highlights')
  await expect(page.getByRole('heading', { name: 'Highlights' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'PixelKobra', exact: true })).toBeVisible()
  await expect(page.getByText('PixelKobra plays ranked')).toBeVisible()

  await page.getByRole('button', { name: 'Load more' }).click()
  await expect(page.getByText('NightOwlCZ late night just chatting')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()

  // Re-clicking the ACTIVE pills is a no-op: loaded pages survive, no request fires.
  await page.getByRole('button', { name: 'All time' }).click()
  await page.getByRole('button', { name: 'Top hype' }).click()
  await expect(page.getByText('PixelKobra plays ranked')).toBeVisible()
  await expect(page.getByText('NightOwlCZ late night just chatting')).toBeVisible()
  expect(calls).toHaveLength(2)

  // Window pill: re-queries with window=7 at offset 0 and resets the accumulated wall.
  const sevenDays = page.getByRole('button', { name: '7 days' })
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'false')
  await sevenDays.click()
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'true')

  // While the new window is in flight: spinner, not the empty state, and none
  // of the previous window's cards or its Load more control.
  await expect(page.getByText('Surfacing the best moments…').first()).toBeVisible()
  await expect(page.getByText('No highlights yet')).not.toBeVisible()
  await expect(page.getByText('PixelKobra plays ranked')).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()
  releaseWindowSwitch()

  await expect(page.getByText('Weekly window hype moment')).toBeVisible()
  await expect(page.getByText('PixelKobra plays ranked')).not.toBeVisible()
  await expect(page.getByText('NightOwlCZ late night just chatting')).not.toBeVisible()

  // Sort pill: re-queries with sort=recent inside the selected window.
  const mostRecent = page.getByRole('button', { name: 'Most recent' })
  await expect(mostRecent).toHaveAttribute('aria-pressed', 'false')
  await mostRecent.click()
  await expect(mostRecent).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText('Freshest moment this week')).toBeVisible()

  expect(calls).toEqual([
    { window: 'all', sort: 'hype', offset: 0 },
    { window: 'all', sort: 'hype', offset: 24 },
    { window: '7', sort: 'hype', offset: 0 },
    { window: '7', sort: 'recent', offset: 0 },
  ])
})

const rankingRow = (
  rank: number,
  chatterId: number,
  nick: string,
  archetypes: Array<{ key: string, label: string }> = [],
) => ({
  rank,
  chatter_id: chatterId,
  nick,
  total_messages: 5000 - rank,
  streams_attended: 42,
  creators_visited: 6,
  home_channel: {
    creator_id: 71,
    creator_nick: 'pixelkobra',
    creator_display_name: 'PixelKobra',
    messages: 3000,
    share: 0.6,
  },
  archetypes: archetypes.map(({ key, label }) => ({
    key,
    label,
    description: `${label} badge`,
  })),
})

test('rankings: paginates, then the window pill re-queries and resets the table', async ({ page }) => {
  const calls: Array<{ window: string, offset: number }> = []
  // The window-switch response is gated: keepPreviousData means a slow switch
  // must NOT keep the old window's rows (or their Load more, which would fire
  // the new window at the stale offset) on screen while the fetch is in flight.
  let releaseWindowSwitch = () => {}
  const windowSwitchGate = new Promise<void>((resolve) => { releaseWindowSwitch = resolve })

  await page.route('**/api/**', async (route) => {
    const { pathname, searchParams } = new URL(route.request().url())
    if (pathname !== '/api/scene/chatter-rankings') return unexpected(route, pathname)

    const windowKey = searchParams.get('window') ?? 'all'
    const offset = Number(searchParams.get('offset') ?? '0')
    calls.push({ window: windowKey, offset })

    if (windowKey === 'all' && offset === 0) {
      return json(route, {
        window: windowKey,
        has_more: true,
        items: [rankingRow(1, 301, 'chatterOne', [{ key: 'loyalist', label: 'Loyalist' }])],
      })
    }
    if (windowKey === 'all') {
      return json(route, {
        window: windowKey,
        has_more: false,
        items: [{ ...rankingRow(26, 302, 'chatterTwo'), home_channel: null }],
      })
    }
    if (windowKey === '30' && offset === 0) {
      await windowSwitchGate
      return json(route, {
        window: windowKey,
        has_more: false,
        items: [rankingRow(1, 303, 'monthlyChampion')],
      })
    }
    return unexpected(route, pathname)
  })

  await page.goto('/rankings')
  await expect(page.getByRole('heading', { name: 'Power rankings' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()

  await page.getByRole('button', { name: 'Load more' }).click()
  await expect(page.getByRole('link', { name: 'chatterTwo' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()

  // Archetype filter chip: any-of, client-side only — toggling re-filters the
  // already-loaded rows with no extra network request (chatterOne is a
  // Loyalist, chatterTwo carries no badges).
  const loyalistChip = page.getByRole('button', { name: 'Loyalist' })
  await expect(loyalistChip).toHaveAttribute('aria-pressed', 'false')
  await loyalistChip.click()
  await expect(loyalistChip).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterTwo' })).not.toBeVisible()
  expect(calls).toHaveLength(2)

  // Clearing the chip restores both loaded rows, still with no new request.
  await loyalistChip.click()
  await expect(loyalistChip).toHaveAttribute('aria-pressed', 'false')
  await expect(page.getByRole('link', { name: 'chatterTwo' })).toBeVisible()
  expect(calls).toHaveLength(2)

  // Re-clicking the ACTIVE pill is a no-op: loaded pages survive, no request fires.
  await page.getByRole('button', { name: 'All time' }).click()
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterTwo' })).toBeVisible()
  expect(calls).toHaveLength(2)

  // Window pill: re-queries with window=30 at offset 0 and drops the accumulated pages.
  const thirtyDays = page.getByRole('button', { name: '30 days' })
  await expect(thirtyDays).toHaveAttribute('aria-pressed', 'false')
  await thirtyDays.click()
  await expect(thirtyDays).toHaveAttribute('aria-pressed', 'true')

  // While the new window is in flight: spinner only — no stale rows, and no
  // Load more that could fire window=30 at the old offset.
  await expect(page.getByText('Ranking the scene...').first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()
  releaseWindowSwitch()

  await expect(page.getByRole('link', { name: 'monthlyChampion' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).not.toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterTwo' })).not.toBeVisible()

  expect(calls).toEqual([
    { window: 'all', offset: 0 },
    { window: 'all', offset: 25 },
    { window: '30', offset: 0 },
  ])
})

test('trending: renders both boards, and the window pill refetches them', async ({ page }) => {
  const copypastaByWindow: Record<string, { text: string }> = {
    7: { text: 'OMEGALUL nice job chat' },
    14: { text: 'KEKW the two week classic' },
  }
  const emoteByWindow: Record<string, { name: string }> = {
    7: { name: 'PogChamp' },
    14: { name: 'LULW' },
  }

  await page.route('**/api/**', async (route) => {
    const { pathname, searchParams } = new URL(route.request().url())
    const windowKey = searchParams.get('window') ?? '7'
    if (pathname === '/api/scene/trending/copypastas') {
      const entry = copypastaByWindow[windowKey]
      if (!entry) return unexpected(route, pathname)
      return json(route, {
        window: Number(windowKey),
        items: [{
          message_text_id: 9001,
          text: entry.text,
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
      const entry = emoteByWindow[windowKey]
      if (!entry) return unexpected(route, pathname)
      return json(route, {
        window: Number(windowKey),
        items: [{
          emote_id: 42,
          name: entry.name,
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

  // Window pill: both boards refetch with window=14.
  const fourteenDays = page.getByRole('button', { name: '14 days' })
  await expect(fourteenDays).toHaveAttribute('aria-pressed', 'false')
  await fourteenDays.click()
  await expect(fourteenDays).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText('KEKW the two week classic')).toBeVisible()
  await expect(page.getByText('LULW')).toBeVisible()
})

const wrappedBody = (days: number, topCreator: string, topChatter: string) => ({
  days,
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
    nick: topCreator.toLowerCase(),
    display_name: topCreator,
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
    nick: topChatter,
    total_messages: 5000,
    streams_attended: 42,
    creators_visited: 6,
    home_creator_display_name: topCreator,
  }],
  top_moments: [{
    stream_id: 501,
    stream_title: `${topCreator} plays ranked`,
    twitch_id: 'vod-501',
    creator_display_name: topCreator,
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
    title: `${topCreator} went live`,
    summary: 'Started streaming ranked queue.',
    creator_display_name: topCreator,
  }],
})

test('wrapped: renders the default 30-day recap, and the window pill re-queries', async ({ page }) => {
  const requestedDays: string[] = []

  await page.route('**/api/**', async (route) => {
    const { pathname, searchParams } = new URL(route.request().url())
    if (pathname !== '/api/scene/wrapped') return unexpected(route, pathname)
    const days = searchParams.get('days') ?? ''
    requestedDays.push(days)
    if (days === '30') return json(route, wrappedBody(30, 'PixelKobra', 'chatterOne'))
    if (days === '7') return json(route, wrappedBody(7, 'SprintKing', 'weeklyOne'))
    return unexpected(route, pathname)
  })

  await page.goto('/wrapped')
  await expect(page.getByRole('heading', { name: 'Scene Wrapped' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'PixelKobra' }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'chatterOne' })).toBeVisible()
  await expect(page.getByText('OMEGALUL nice job chat')).toBeVisible()

  // Window pill: re-queries the recap with days=7.
  const sevenDays = page.getByRole('button', { name: '7 days' })
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'false')
  await sevenDays.click()
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('link', { name: 'SprintKing' }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'weeklyOne' })).toBeVisible()

  expect(requestedDays).toEqual(['30', '7'])
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
