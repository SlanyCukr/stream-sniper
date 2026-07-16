import {
    useMutation, useQueryClient,
} from '@tanstack/react-query'

/**
 * @template TData
 * @template TError
 * @template TVariables
 * @template TContext
 * Hook-level mutation functions resolve to domain data, never Axios response
 * wrappers. Transport metadata remains available on thrown adapter errors.
 * @param {import('@tanstack/react-query').MutationFunction<TData, TVariables>} mutationFn
 * @param {readonly unknown[]} queryKey
 * @param {Omit<import('@tanstack/react-query').UseMutationOptions<TData, TError, TVariables, TContext>, 'mutationFn'>} [options]
 */
export const useInvalidatingMutation = (mutationFn, queryKey, options = {}) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options
    return useMutation({
        ...mutationOptions,
        mutationFn,
        onSuccess: async (...args) => {
            await queryClient.invalidateQueries({ queryKey })
            await onSuccess?.(...args)
        },
    })
}
