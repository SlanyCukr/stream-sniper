import { screen } from '@testing-library/react'
import { usePathname, useRouter } from 'next/navigation'
import { describe, expect, it } from 'vitest'

import { renderWithQueryClient } from './render'
import { navigationState, router } from './mocks/navigation'

function NavigationConsumer() {
  const nextRouter = useRouter()

  return (
    <button type="button" onClick={() => nextRouter.push('/streams')}>
      Current path: {usePathname()}
    </button>
  )
}

describe('frontend test harness', () => {
  it('renders through the shared query client wrapper', () => {
    const { queryClient } = renderWithQueryClient(<p>Harness ready</p>)

    expect(screen.getByText('Harness ready')).toBeInTheDocument()
    expect(queryClient.getDefaultOptions().queries?.retry).toBe(false)
  })

  it('provides controllable Next navigation state', async () => {
    navigationState.pathname = '/admin'
    const { user } = renderWithQueryClient(<NavigationConsumer />)

    expect(screen.getByRole('button')).toHaveTextContent('Current path: /admin')
    await user.click(screen.getByRole('button'))
    expect(router.push).toHaveBeenCalledWith('/streams')
  })
})
