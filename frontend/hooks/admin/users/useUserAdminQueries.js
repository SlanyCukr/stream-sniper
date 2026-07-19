import { useQuery } from '@tanstack/react-query'
import { useInvalidatingMutation } from '@/hooks/useInvalidatingMutation'
import {
    createAdminUser,
    deleteUser,
    retrieveAdminSystemStats,
    retrieveUsers,
    setUserActive,
    updateUser,
    updateUserRole,
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

/** @typedef {{pageIndex?:number, pageSize?:number}} UserParams */

/** @param {UserParams} [params] */
const normalizeUserParams = ({
    pageIndex = 0,
    pageSize = 20,
} = {}) => ({
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
    list: (/** @type {UserParams} */ params) => [
        ...userAdminKeys.all,
        'list',
        normalizeUserParams(params),
    ],
}

/** @param {unknown} value */
export const mapAdminSystemStats = value => {
    const data = requireRecord(value, 'admin system stats')
    return {
        totalUsers: requireFiniteNumberField(data, 'total_users', 'admin system stats'),
        activeUsers: requireFiniteNumberField(data, 'active_users', 'admin system stats'),
        adminUsers: requireFiniteNumberField(data, 'admin_users', 'admin system stats'),
        recentRegistrations: requireFiniteNumberField(data, 'recent_registrations', 'admin system stats'),
    }
}

/** @param {unknown} value */
export const mapAdminUser = value => {
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

/** @param {unknown} value @param {{pageIndex:number, pageSize:number}} pagination */
const mapAdminUsersPage = (value, pagination) => {
    const data = requireRecord(value, 'admin users')
    return createPage(
        requireArrayField(data, 'users', 'admin users').map(mapAdminUser),
        requireFiniteNumberField(data, 'total', 'admin users'),
        pagination.pageIndex,
        pagination.pageSize,
    )
}

export const useAdminSystemStats = (options = {}) => useQuery({
    ...options,
    queryKey: userAdminKeys.stats(),
    queryFn: async () => {
        const { data } = await retrieveAdminSystemStats()
        return mapAdminSystemStats(data)
    },
})

export const useAdminUsers = (params = {}, options = {}) => {
    const normalizedParams = normalizeUserParams(params)
    return useQuery({
        ...options,
        queryKey: userAdminKeys.list(normalizedParams),
        queryFn: async () => {
            const { data: value } = await retrieveUsers({
                rowOffset: getRowOffset(normalizedParams.pageIndex, normalizedParams.pageSize),
                pageSize: normalizedParams.pageSize,
            })
            return mapAdminUsersPage(value, normalizedParams)
        },
    })
}

export const useCreateAdminUser = (options = {}) => useInvalidatingMutation(
    async (/** @type {import('@/lib/api/users').CreateAdminUserRequest} */ user) => (
        mapAdminUser((await createAdminUser(user)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useUpdateAdminUser = (options = {}) => useInvalidatingMutation(
    async (/** @type {{userId:number, changes:import('@/lib/api/users').UpdateAdminUserRequest}} */ command) => (
        mapAdminUser((await updateUser(command.userId, command.changes)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useUpdateAdminUserRole = (options = {}) => useInvalidatingMutation(
    async (/** @type {{userId:number, role:import('@/lib/api/users').AdminUserDto['role']}} */ command) => (
        mapAdminUser((await updateUserRole(command.userId, command.role)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useSetAdminUserActive = (options = {}) => useInvalidatingMutation(
    async (/** @type {{userId:number, isActive:boolean}} */ command) => (
        mapAdminUser((await setUserActive(command.userId, command.isActive)).data)
    ),
    userAdminKeys.all,
    options,
)

export const useDeleteAdminUser = (options = {}) => useInvalidatingMutation(
    async (/** @type {number} */ userId) => (await deleteUser(userId)).data,
    userAdminKeys.all,
    options,
)
