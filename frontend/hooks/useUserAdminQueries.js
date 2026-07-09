import {
    useMutation, useQuery, useQueryClient,
} from '@tanstack/react-query'
import {
    createAdminUser,
    deleteUser,
    retrieveAdminSystemStats,
    retrieveUsers,
    setUserActive,
    updateUser,
    updateUserRole,
} from '@/lib/api'

const EMPTY_USERS_RESPONSE = {
    users: [
    ],
    total: 0,
    offset: 0,
    limit: 20,
}

const normalizeUserParams = ({
    offset = 0,
    limit = 20,
} = {}) => ({
    offset,
    limit,
})

/** Query-key factory for account administration data. */
export const userAdminKeys = {
    all: [
        'admin',
        'users',
    ],
    stats: () => [
        ...userAdminKeys.all,
        'stats',
    ],
    lists: () => [
        ...userAdminKeys.all,
        'list',
    ],
    list: params => [
        ...userAdminKeys.lists(),
        normalizeUserParams(params),
    ],
}

/** Fetch user counts for the administration dashboard. */
export const useAdminSystemStats = (options = {}) => useQuery({
    queryKey: userAdminKeys.stats(),
    queryFn: async () => {
        const { data } = await retrieveAdminSystemStats()
        return data
    },
    ...options,
})

/** Fetch one page of user accounts. */
export const useAdminUsers = (params = {}, options = {}) => {
    const normalizedParams = normalizeUserParams(params)
    return useQuery({
        queryKey: userAdminKeys.list(normalizedParams),
        queryFn: async () => {
            const { data } = await retrieveUsers(normalizedParams)
            return data || EMPTY_USERS_RESPONSE
        },
        ...options,
    })
}

const useUserAdminMutation = (mutationFn, options = {}) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options

    return useMutation({
        ...mutationOptions,
        mutationFn,
        onSuccess: async (...args) => {
            await queryClient.invalidateQueries({ queryKey: userAdminKeys.all })
            await onSuccess?.(...args)
        },
    })
}

/** Create a user and refresh account lists and counts. */
export const useCreateAdminUser = (options = {}) => useUserAdminMutation(
    user => createAdminUser(user),
    options,
)

/** Update a user's account details and refresh account lists and counts. */
export const useUpdateAdminUser = (options = {}) => useUserAdminMutation(
    ({ userId, changes }) => updateUser(userId, changes),
    options,
)

/** Update a user's role and refresh account lists and counts. */
export const useUpdateAdminUserRole = (options = {}) => useUserAdminMutation(
    ({ userId, role }) => updateUserRole(userId, role),
    options,
)

/** Toggle a user's active state and refresh account lists and counts. */
export const useSetAdminUserActive = (options = {}) => useUserAdminMutation(
    ({ userId, isActive }) => setUserActive(userId, isActive),
    options,
)

/** Delete a user and refresh account lists and counts. */
export const useDeleteAdminUser = (options = {}) => useUserAdminMutation(
    userId => deleteUser(userId),
    options,
)
