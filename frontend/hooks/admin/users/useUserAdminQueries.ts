import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { useInvalidatingMutation } from '@/hooks/useInvalidatingMutation'
import {
    createAdminUser,
    deleteUser,
    retrieveAdminSystemStats,
    retrieveUsers,
    setUserActive,
    updateUser,
    updateUserRole,
    type AdminUserDto,
    type CreateAdminUserRequest,
    type UpdateAdminUserRequest,
} from '@/lib/api/users'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { USER_ROLES } from '@/lib/auth/roles'

interface UserParams {
    pageIndex?: number
    pageSize?: number
}

// queryKey/queryFn stay accepted-but-untyped: both hooks below always overwrite
// them with their own key/fetcher (matching runtime behavior), so a caller
// passing either does not influence what actually runs.
type QueryOptions<T> = Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, 'queryKey' | 'queryFn'> & {
    queryKey?: unknown
    queryFn?: unknown
}

const normalizeUserParams = ({
    pageIndex = 0,
    pageSize = 20,
}: UserParams = {}) => ({
    ...normalizePagination(pageIndex, pageSize),
})

export const userAdminKeys = {
    all: [
        'admin',
        'users',
    ],
    stats: () => [
        ...userAdminKeys.all,
        'stats',
    ],
    list: (params?: UserParams) => [
        ...userAdminKeys.all,
        'list',
        normalizeUserParams(params),
    ],
}

export interface AdminSystemStats {
    totalUsers: number
    activeUsers: number
    adminUsers: number
    recentRegistrations: number
}

export const mapAdminSystemStats = (value: unknown): AdminSystemStats => {
    const data = requireRecord(value, 'admin system stats')
    return {
        totalUsers: requireFiniteNumberField(data, 'total_users', 'admin system stats'),
        activeUsers: requireFiniteNumberField(data, 'active_users', 'admin system stats'),
        adminUsers: requireFiniteNumberField(data, 'admin_users', 'admin system stats'),
        recentRegistrations: requireFiniteNumberField(data, 'recent_registrations', 'admin system stats'),
    }
}

export interface AdminUser {
    id: number
    username: string
    email: string
    role: AdminUserDto['role']
    isActive: boolean
    createdAt: string
}

export const mapAdminUser = (value: unknown): AdminUser => {
    const user = requireRecord(value, 'admin user')
    const role = requireStringField(user, 'role', 'admin user')
    if (role !== USER_ROLES.USER && role !== USER_ROLES.ADMIN) {
        throw new TypeError('admin user.role must be a recognized user role')
    }
    return {
        id: requireFiniteNumberField(user, 'id', 'admin user'),
        username: requireStringField(user, 'username', 'admin user'),
        email: requireStringField(user, 'email', 'admin user'),
        role,
        isActive: requireBooleanField(user, 'is_active', 'admin user'),
        createdAt: requireStringField(user, 'created_at', 'admin user'),
    }
}

const mapAdminUsersPage = (value: unknown, pagination: { pageIndex: number, pageSize: number }) => {
    const data = requireRecord(value, 'admin users')
    return createPage(
        requireArrayField(data, 'users', 'admin users').map(mapAdminUser),
        requireFiniteNumberField(data, 'total', 'admin users'),
        pagination.pageIndex,
        pagination.pageSize,
    )
}

export const useAdminSystemStats = (options: QueryOptions<AdminSystemStats> = {}) => useQuery({
    ...options,
    queryKey: userAdminKeys.stats(),
    queryFn: async () => {
        const data = await retrieveAdminSystemStats()
        return mapAdminSystemStats(data)
    },
})

export const useAdminUsers = (
    params: UserParams = {},
    options: QueryOptions<ReturnType<typeof mapAdminUsersPage>> = {},
) => {
    const normalizedParams = normalizeUserParams(params)
    return useQuery({
        ...options,
        queryKey: userAdminKeys.list(normalizedParams),
        queryFn: async () => {
            const value = await retrieveUsers({
                rowOffset: getRowOffset(normalizedParams.pageIndex, normalizedParams.pageSize),
                pageSize: normalizedParams.pageSize,
            })
            return mapAdminUsersPage(value, normalizedParams)
        },
    })
}

export const useCreateAdminUser = (options = {}) => useInvalidatingMutation(
    async (user: CreateAdminUserRequest): Promise<AdminUser> => (
        mapAdminUser((await createAdminUser(user)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useUpdateAdminUser = (options = {}) => useInvalidatingMutation(
    async (command: { userId: number, changes: UpdateAdminUserRequest }): Promise<AdminUser> => (
        mapAdminUser((await updateUser(command.userId, command.changes)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useUpdateAdminUserRole = (options = {}) => useInvalidatingMutation(
    async (command: { userId: number, role: AdminUserDto['role'] }): Promise<AdminUser> => (
        mapAdminUser((await updateUserRole(command.userId, command.role)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useSetAdminUserActive = (options = {}) => useInvalidatingMutation(
    async (command: { userId: number, isActive: boolean }): Promise<AdminUser> => (
        mapAdminUser((await setUserActive(command.userId, command.isActive)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useDeleteAdminUser = (options = {}) => useInvalidatingMutation(
    async (userId: number): Promise<void> => (await deleteUser(userId)).data,
    userAdminKeys.all,
    options,
)
