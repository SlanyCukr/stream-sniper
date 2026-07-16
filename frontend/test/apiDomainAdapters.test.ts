import { afterEach, describe, expect, expectTypeOf, it, vi } from 'vitest'

import { api } from '@/lib/api/client'
import {
  retrieveChatterMessages,
  type ChatterMessagePageDto,
} from '@/lib/api/chatter'
import { retrieveStreams, type StreamListDto } from '@/lib/api/streams'
import { retrieveScenePulse, type ScenePulseDto } from '@/lib/api/scene'
import { updateUserRole, type AdminUserDto } from '@/lib/api/users'

describe('domain API adapters', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps domain request translation and response contracts explicit', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: {} })
    const put = vi.spyOn(api, 'put').mockResolvedValue({ data: {} })

    const chatterResponse = await retrieveChatterMessages(7, { rowOffset: 100, pageSize: 50 })
    const streamResponse = await retrieveStreams({
      creatorId: 9,
      sort: 'start',
      dir: 'desc',
      rowOffset: 40,
    })
    const pulseResponse = await retrieveScenePulse({ days: 30, eventType: 'personal_record' })
    const userResponse = await updateUserRole(3, 'admin')

    expect(get).toHaveBeenNthCalledWith(1, '/chatters/7/messages?offset=100&limit=50')
    expect(get).toHaveBeenNthCalledWith(2, '/streams?creator_id=9&sort=start&dir=desc&offset=40')
    expect(get).toHaveBeenNthCalledWith(3, '/scene/pulse?days=30&event_type=personal_record')
    expect(put).toHaveBeenCalledWith('/auth/users/3/role?new_role=admin')

    expectTypeOf(chatterResponse.data).toEqualTypeOf<ChatterMessagePageDto>()
    expectTypeOf(streamResponse.data).toEqualTypeOf<StreamListDto>()
    expectTypeOf(pulseResponse.data).toEqualTypeOf<ScenePulseDto>()
    expectTypeOf(userResponse.data).toEqualTypeOf<AdminUserDto>()
  })
})
