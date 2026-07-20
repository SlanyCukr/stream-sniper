import { expect, test, type Page } from '@playwright/test'
import { json, login, unexpected } from './helpers'

const tokenFor = (role: 'admin' | 'user') => [
  Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url'),
  Buffer.from(JSON.stringify({
    sub: 'smoke-user',
    role,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url'),
  'smoke-signature',
].join('.')

const adminProfile = {
  id: 1,
  username: 'smoke-admin',
  email: 'admin@example.test',
  role: 'admin',
  is_active: true,
}

const trackedStreamer = {
  id: 7,
  creator_id: 70,
  twitch_username: 'operator',
  display_name: 'Operator',
  is_active: true,
  last_stream_check: null,
  last_processed_vod_id: null,
  total_streams_collected: 3,
  last_collected_stream_start: '2026-07-13T18:00:00',
  processing_enabled: true,
  created_at: '2026-07-14T10:00:00Z',
  updated_at: '2026-07-14T10:00:00Z',
  created_by: 1,
  notes: null,
  creator_display_name: 'Operator',
  profile_image_url: null,
  created_by_username: 'smoke-admin',
}

const trackedStreamersPage = {
  streamers: [trackedStreamer],
  total: 1,
  offset: 0,
  limit: 20,
}

async function installStoredAdmin(page: Page) {
  const token = tokenFor('admin')
  await page.addInitScript((storedToken) => {
    window.localStorage.setItem('token', storedToken)
  }, token)
  return token
}

test('redirects a protected route through the real login/session flow', async ({ page }) => {
  const token = tokenFor('admin')
  let loginPayload: unknown
  let profileAuthorization: string | undefined

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    if (pathname === '/api/auth/login' && request.method() === 'POST') {
      loginPayload = request.postDataJSON()
      return json(route, { access_token: token })
    }
    if (pathname === '/api/auth/me' && request.method() === 'GET') {
      profileAuthorization = request.headers().authorization
      return json(route, adminProfile)
    }
    if (pathname === '/api/admin/tracking/streamers' && request.method() === 'GET') {
      return json(route, trackedStreamersPage)
    }
    return unexpected(route, pathname)
  })

  await page.goto('/admin/tracking/streamers')
  await expect(page).toHaveURL(/\/login\?from=%2Fadmin%2Ftracking%2Fstreamers$/)
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()

  await login(page, 'smoke-admin', 'correct horse battery staple')

  await expect(page).toHaveURL(/\/admin\/tracking\/streamers$/)
  await expect(page.getByRole('heading', { name: 'Streamer tracking' })).toBeVisible()
  await expect(page.getByText('operator', { exact: true })).toBeVisible()
  expect(loginPayload).toEqual({
    username: 'smoke-admin',
    password: 'correct horse battery staple',
  })
  expect(profileAuthorization).toBe(`Bearer ${token}`)
  await expect.poll(() => page.evaluate(() => localStorage.getItem('token'))).toBe(token)
})

test('loads a stream through production hooks and jumps from timeline to replay', async ({ page }) => {
  let replayPageRequests = 0

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const { pathname, searchParams } = url

    if (pathname === '/api/streams/42' && request.method() === 'GET') {
      return json(route, {
        info: {
          title: 'Smoke Test Stream',
          start: '2026-07-14T10:00:00Z',
          end: '2026-07-14T11:00:00Z',
          thumbnail_url: null,
          message_count: 2,
          creator_nick: 'operator',
          creator_display_name: 'Operator',
          profile_image_url: null,
          creator_id: 70,
        },
        most_active_chatters: [{ chatter_id: 11, nick: 'first-viewer', count: 2 }],
        most_tagged_chatters: [],
        other_creators: [],
        chatters: [{ chatter_id: 11, nick: 'first-viewer' }],
      })
    }
    if (pathname === '/api/streams/42/timeline' && request.method() === 'GET') {
      return json(route, {
        stream_id: 42,
        stream_start: '2026-07-14T10:00:00Z',
        twitch_id: 'vod-42',
        bucket_seconds: 60,
        buckets: [
          {
            bucket_minute: '2026-07-14T10:00:00Z',
            message_count: 1,
            unique_chatters: 1,
            sub_messages: 0,
            emote_messages: 0,
          },
          {
            bucket_minute: '2026-07-14T10:01:00Z',
            message_count: 5,
            unique_chatters: 2,
            sub_messages: 1,
            emote_messages: 1,
          },
        ],
        moments: [{
          bucket_minute: '2026-07-14T10:01:00Z',
          offset_seconds: 60,
          message_count: 5,
          ratio: 5,
          persisted: false,
          status: null,
          sub_share: 0.2,
          emote_share: 0.2,
          top_phrases: [],
          sample_messages: [],
        }],
        metrics: {
          unique_chatters: 2,
          messages_per_minute: 3,
          peak_bucket_minute: '2026-07-14T10:01:00Z',
          new_chatters: 1,
          returning_chatters: 1,
          total_messages: 6,
          duration_seconds: 120,
          peak_messages: 5,
          sub_messages: 1,
          emote_messages: 1,
        },
        viewer_samples: [],
        peak_viewers: null,
        context_changes: [],
      })
    }
    if (pathname === '/api/streams/42/messages' && request.method() === 'GET') {
      replayPageRequests += 1
      if (searchParams.has('after_ts')) {
        return json(route, {
          messages: [{
            id: 2,
            time: '2026-07-14T10:01:00Z',
            chatter_id: 12,
            nick: 'target-viewer',
            text: 'timeline target message',
            is_subscriber: true,
            badges: ['subscriber'],
          }],
          next_cursor: null,
          has_more: false,
        })
      }
      return json(route, {
        messages: [{
          id: 1,
          time: '2026-07-14T10:00:00Z',
          chatter_id: 11,
          nick: 'first-viewer',
          text: 'earlier replay message',
          is_subscriber: false,
          badges: [],
        }],
        next_cursor: {
          after_ts: '2026-07-14T10:00:00Z',
          after_id: 1,
        },
        has_more: true,
      })
    }
    if (pathname === '/api/streams/42/report') {
      return json(route, {
        stream_id: 42,
        creator_id: 70,
        baseline_count: 0,
        lookback: 10,
        metrics: {},
        top_emote: null,
        top_phrase: null,
        top_moments: [],
      })
    }
    if (pathname === '/api/streams/42/mentions') return json(route, { mentioned: [], pairs: [] })
    if (pathname === '/api/streams/42/emotes') return json(route, { emotes: [] })
    if (pathname === '/api/streams/42/phrases') return json(route, { phrases: [] })

    return unexpected(route, pathname)
  })

  await page.goto('/stream/42')
  await expect(page.getByRole('heading', { name: 'Operator' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Smoke Test Stream' })).toBeVisible()
  await expect(page.getByText('earlier replay message')).toBeVisible()

  await page.getByRole('button', { name: /Spike at 10:01.*Jump replay here/ }).click()

  await expect(page.locator('.chat-line--flash')).toContainText('timeline target message')
  expect(replayPageRequests).toBe(2)
})

test('runs an authenticated admin mutation and clears the session on 401', async ({ page }) => {
  const token = await installStoredAdmin(page)
  let updateRequests = 0
  const updateBodies: unknown[] = []

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    if (pathname === '/api/auth/me' && request.method() === 'GET') {
      expect(request.headers().authorization).toBe(`Bearer ${token}`)
      return json(route, adminProfile)
    }
    if (pathname === '/api/admin/tracking/streamers' && request.method() === 'GET') {
      return json(route, trackedStreamersPage)
    }
    if (pathname === '/api/admin/tracking/streamers/7' && request.method() === 'PUT') {
      updateRequests += 1
      updateBodies.push(request.postDataJSON())
      if (updateRequests === 1) {
        return json(route, { ...trackedStreamer, is_active: false })
      }
      return json(route, { detail: 'Session expired' }, 401)
    }
    return unexpected(route, pathname)
  })

  await page.goto('/admin/tracking/streamers')
  await expect(page.getByRole('heading', { name: 'Streamer tracking' })).toBeVisible()
  const row = page.getByRole('row').filter({ hasText: 'operator' })

  await row.getByRole('button', { name: 'Deactivate' }).click()
  await expect(page.getByText('Streamer updated successfully')).toBeVisible()
  await expect(row.getByRole('button', { name: 'Disable' })).toBeEnabled()

  await row.getByRole('button', { name: 'Disable' }).click()
  await expect(page).toHaveURL(/\/login\?from=%2Fadmin%2Ftracking%2Fstreamers$/)
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  expect(updateBodies).toEqual([
    { is_active: false },
    { processing_enabled: false },
  ])
  await expect.poll(() => page.evaluate(() => localStorage.getItem('token'))).toBeNull()
})

test('invalid dynamic-route ids respond with a real HTTP 404', async ({ page }) => {
  // Regression guard for the removed root app/loading.tsx: a streaming boundary
  // above these routes made Next commit HTTP 200 before notFound() ran, so
  // crawlers saw the 404 UI with a 200 status. request.get bypasses the app
  // shell and asserts the raw response status.
  for (const path of ['/stream/abc', '/chatter/abc', '/creator/abc/wrapped']) {
    const response = await page.request.get(path)
    expect(response.status(), `${path} should 404`).toBe(404)
  }
})
