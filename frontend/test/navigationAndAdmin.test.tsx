import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { navigationState, router } from './mocks/navigation'

const mocks = vi.hoisted(() => ({
  auth: {
    isAuthenticated: true,
    isAdmin: true,
    user: { username: 'root', email: 'root@example.test', role: 'admin' },
    logout: vi.fn(),
  },
  useAdminSystemStats: vi.fn(),
  useTrackingStats: vi.fn(),
  mutateAsync: vi.fn(),
}))

vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => mocks.auth }))
vi.mock('@/hooks/admin/users/useUserAdminQueries', () => ({
  useAdminSystemStats: mocks.useAdminSystemStats,
  useCreateAdminUser: () => ({ isPending: false, mutateAsync: mocks.mutateAsync }),
}))
vi.mock('@/hooks/admin/tracking/useTrackingQueries', () => ({ useTrackingStats: mocks.useTrackingStats }))

import Header from '@/components/layout/Header'
import FullLayout from '@/components/layout/FullLayout'
import Sidebar from '@/components/layout/Sidebar'
import MomentCard from '@/components/moments/MomentCard'
import { DEFAULT_ORDERING } from '@/lib/stream/config'
import { isAdminRole, USER_ROLES, USER_ROLE_OPTIONS } from '@/lib/auth/roles'
import AdminDashboard from '@/views/admin/AdminDashboard'
import CreateUser from '@/views/admin/CreateUser'
import TrackingDashboard from '@/views/admin/TrackingDashboard'

describe('navigation shell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    navigationState.pathname = '/admin/users'
    mocks.auth.isAuthenticated = true
    mocks.auth.isAdmin = true
    mocks.auth.user = { username: 'root', email: 'root@example.test', role: 'admin' }
  })

  it('marks nested navigation active and gates command links to admins', () => {
    render(<Sidebar />)
    expect(screen.getByRole('link', { name: 'Users' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('Command')).toBeInTheDocument()

    mocks.auth.isAdmin = false
    const { rerender } = render(<Sidebar />)
    rerender(<Sidebar />)
    expect(screen.getAllByText('Command')).toHaveLength(1)
  })

  it('routes profile and logout actions from the authenticated header', () => {
    render(<Header />)
    fireEvent.click(screen.getByRole('button', { name: 'User menu' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /My Profile/ }))
    expect(router.push).toHaveBeenCalledWith('/profile')

    fireEvent.click(screen.getByRole('button', { name: 'User menu' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Logout/ }))
    expect(mocks.auth.logout).toHaveBeenCalledOnce()
    expect(router.push).toHaveBeenCalledWith('/login')
  })

  it('owns mobile sidebar class, backdrop, and aria state in the layout', () => {
    const { container } = render(<FullLayout><div>content</div></FullLayout>)
    const sidebar = container.querySelector('#sidebarArea')!
    const backdrop = container.querySelector('.sidebar-backdrop')!
    const openButton = screen.getByRole('button', { name: 'Open navigation menu' })

    expect(sidebar).not.toHaveClass('showSidebar')
    expect(openButton).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(openButton)
    expect(sidebar).toHaveClass('showSidebar')
    expect(openButton).toHaveAttribute('aria-expanded', 'true')
    expect(backdrop).toHaveAttribute('data-open', 'true')

    fireEvent.click(backdrop)
    expect(sidebar).not.toHaveClass('showSidebar')
    expect(openButton).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(openButton)
    fireEvent.click(screen.getByRole('button', { name: 'Close navigation menu' }))
    expect(sidebar).not.toHaveClass('showSidebar')
  })

  it('pins role and default-ordering constants used by the shell', () => {
    expect(isAdminRole(USER_ROLES.ADMIN)).toBe(true)
    expect(isAdminRole(USER_ROLES.USER)).toBe(false)
    expect(USER_ROLE_OPTIONS).toEqual([
      { value: USER_ROLES.USER, label: 'User' },
      { value: USER_ROLES.ADMIN, label: 'Admin' },
    ])
    expect(DEFAULT_ORDERING).toEqual({ value: 'start', label: 'Started at' })
  })
})

describe('moment review presentation', () => {
  it('submits clip metadata and preserves nullable analytics semantics', () => {
    const onReview = vi.fn()
    render(<MomentCard
      isAdmin
      pending={false}
      onReview={onReview}
      moment={{
        streamId: 42,
        streamTitle: 'Launch',
        streamStart: '2026-01-01T12:00:00',
        twitchVodId: '1234',
        creatorName: 'alpha',
        t: '2026-01-01T12:15:00',
        count: 100,
        baseline: 20,
        score: 5,
        unique: null,
        subShare: 0.25,
        emoteShare: null,
        topPhrases: [{ phrase: 'lets go', count: 10 }],
        sampleMessages: [{ text: 'huge play', count: 2 }],
        status: 'bookmarked',
        clipUrl: null,
        note: null,
      }}
    />)

    expect(screen.getByText('25%')).toBeInTheDocument()
    expect(screen.queryByText(/chatters/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Attach clip/ }))
    fireEvent.change(screen.getByLabelText('Clip URL'), { target: { value: 'https://clips.twitch.tv/example' } })
    fireEvent.change(screen.getByLabelText('Curator note'), { target: { value: 'opening play' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save clip' }))

    expect(onReview).toHaveBeenCalledWith('clipped', {
      clipUrl: 'https://clips.twitch.tv/example',
      note: 'opening play',
    })
  })
})

describe('admin entry points', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.useAdminSystemStats.mockReturnValue({
      data: { totalUsers: 10, activeUsers: 8, adminUsers: 2, recentRegistrations: 1 },
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })
    mocks.useTrackingStats.mockReturnValue({
      data: {
        systemStatus: {
          monitoringActive: true,
          monitoringDegraded: false,
          processingQueueSize: 2,
          failedJobs: 0,
        },
        trackedStreamers: { total: 3, active: 2, processingEnabled: 2, inactive: 1 },
        processingJobs: { total: 10, pending: 2, inProgress: 1, completed: 7, failed: 0, recent24h: 4 },
      },
      dataUpdatedAt: new Date('2026-01-01T12:00:00').getTime(),
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })
  })

  it('renders live dashboard statistics and correct action destinations', () => {
    render(<AdminDashboard />)
    expect(screen.getByText('Welcome back, root')).toBeInTheDocument()
    expect(screen.getByText('Total users').nextSibling).toHaveTextContent('10')
    expect(screen.getByRole('link', { name: /Create New User/ })).toHaveAttribute('href', '/admin/users/create')
  })

  it('renders tracking health from query data and reports the query update time', () => {
    render(<TrackingDashboard />)
    expect(screen.getByText(/Last updated:/)).toBeInTheDocument()
    expect(screen.getByText('2 pending')).toBeInTheDocument()
    expect(screen.getByText('70%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View Processing Jobs/ })).toHaveAttribute('href', '/admin/tracking/jobs')
  })

  it('validates and submits the complete create-user command', async () => {
    mocks.mutateAsync.mockResolvedValue({ username: 'operator' })
    render(<CreateUser />)
    const submit = screen.getByRole('button', { name: /Create user/ })
    expect(screen.getByLabelText('Role')).toHaveTextContent('UserAdmin')

    fireEvent.submit(submit.closest('form')!)
    expect(await screen.findByText('All fields are required')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('Enter username'), { target: { value: 'operator' } })
    fireEvent.change(screen.getByPlaceholderText('Enter email address'), { target: { value: 'operator@example.test' } })
    fireEvent.change(screen.getByPlaceholderText('Enter password'), { target: { value: 'password1' } })
    fireEvent.change(screen.getByPlaceholderText('Confirm password'), { target: { value: 'password1' } })
    fireEvent.click(submit)

    await waitFor(() => expect(mocks.mutateAsync).toHaveBeenCalledWith({
      username: 'operator',
      email: 'operator@example.test',
      password: 'password1',
      role: USER_ROLES.USER,
      is_active: true,
    }))
    expect(await screen.findByText('User "operator" created successfully!')).toBeInTheDocument()
  })

  it('preserves structured create-user failures for the shared error UI', async () => {
    mocks.mutateAsync.mockRejectedValue({
      response: { status: 409, data: { detail: 'username already exists' } },
      message: 'request failed',
    })
    render(<CreateUser />)

    fireEvent.change(screen.getByPlaceholderText('Enter username'), { target: { value: 'operator' } })
    fireEvent.change(screen.getByPlaceholderText('Enter email address'), { target: { value: 'operator@example.test' } })
    fireEvent.change(screen.getByPlaceholderText('Enter password'), { target: { value: 'password1' } })
    fireEvent.change(screen.getByPlaceholderText('Confirm password'), { target: { value: 'password1' } })
    fireEvent.click(screen.getByRole('button', { name: /Create user/ }))

    expect(await screen.findByText('username already exists')).toBeInTheDocument()
    expect(screen.getByText('Failed to create user')).toBeInTheDocument()
  })
})
