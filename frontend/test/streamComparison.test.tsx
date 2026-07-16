import { http, HttpResponse } from 'msw'
import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import StreamCompare from '@/views/stream/StreamCompare'
import { renderWithQueryClient } from './render'
import { server } from './mocks/server'

describe('stream comparison integration', () => {
  it('maps list options and comparison analytics through the real query chain', async () => {
    const comparisonRequests: string[] = []
    server.use(
      http.get('/api/streams', () => HttpResponse.json({
        streams: [
          {
            stream_id: 101, creator_name: 'Alpha', start: '2026-07-14T10:00:00Z',
            end: '2026-07-14T11:00:00Z', thumbnail_url: null, message_count: 1200,
          },
          {
            stream_id: 202, creator_name: 'Beta', start: '2026-07-13T10:00:00Z',
            end: '2026-07-13T11:00:00Z', thumbnail_url: null, message_count: 900,
          },
        ],
        total: 2,
        offset: 0,
        limit: 20,
      })),
      http.get('/api/streams/compare', ({ request }) => {
        comparisonRequests.push(request.url)
        return HttpResponse.json({
          streams: [
            {
              stream_id: 101,
              creator_id: 1,
              creator_nick: 'alpha',
              creator_display_name: 'Alpha',
              title: 'Alpha launch',
              start: '2026-07-14T10:00:00Z',
              duration_seconds: 3600,
              total_messages: 1200,
              messages_per_minute: 20.5,
              unique_chatters: 400,
              new_chatters: 100,
              returning_chatters: 300,
              sub_share: 0.25,
              emote_share: 0.4,
              peak_messages: 50,
              peak_bucket_minute: '2026-07-14T10:30:00Z',
              peak_viewers: 800,
              curve: [
                { percent: 0, message_count: 10, unique_chatters: 8 },
                { percent: 100, message_count: 20, unique_chatters: 15 },
              ],
            },
            {
              stream_id: 202,
              creator_id: 2,
              creator_nick: 'beta',
              creator_display_name: 'Beta',
              title: 'Beta recap',
              start: '2026-07-13T10:00:00Z',
              duration_seconds: 3600,
              total_messages: 900,
              messages_per_minute: 15,
              unique_chatters: 300,
              new_chatters: 80,
              returning_chatters: 220,
              sub_share: 0.2,
              emote_share: 0.3,
              peak_messages: 40,
              peak_bucket_minute: '2026-07-13T10:30:00Z',
              peak_viewers: 600,
              curve: [
                { percent: 0, message_count: 8, unique_chatters: 6 },
                { percent: 100, message_count: 16, unique_chatters: 12 },
              ],
            },
          ],
          retention: [{
            from_stream_id: 101,
            to_stream_id: 202,
            from_audience: 400,
            to_audience: 300,
            retained: 200,
            retention_rate: 0.5,
          }],
        })
      }),
    )

    const { user } = renderWithQueryClient(<StreamCompare />)
    const picker = await screen.findByLabelText('Choose streams')

    await user.click(picker)
    await user.click(await screen.findByText('Alpha · 2026-07-14T10:00:00Z · #101'))
    await user.click(picker)
    await user.click(await screen.findByText('Beta · 2026-07-13T10:00:00Z · #202'))

    expect(await screen.findByRole('img', { name: 'Normalized chat activity curves' }))
      .toBeInTheDocument()
    expect(screen.getByRole('link', { name: /AlphaAlpha launch/ })).toHaveAttribute('href', '/stream/101')
    expect(screen.getByRole('link', { name: /BetaBeta recap/ })).toHaveAttribute('href', '/stream/202')
    expect(screen.getByRole('row', { name: /Total messages 1,200 900/ })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /Messages\/min 20\.5 15\.0/ })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /Subscriber share 25% 20%/ })).toBeInTheDocument()
    expect(screen.getByText('50%', { selector: '.stat-value' })).toBeInTheDocument()
    expect(screen.getByText('200 of 400 chatters returned')).toBeInTheDocument()
    await waitFor(() => expect(comparisonRequests).toHaveLength(1))
    expect(new URL(comparisonRequests[0]).searchParams.getAll('stream_ids')).toEqual(['101', '202'])
  })
})
