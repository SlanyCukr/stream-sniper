import {
    useMutation, useQueryClient,
    type MutationFunction,
    type UseMutationOptions,
} from '@tanstack/react-query'

/**
 * Hook-level mutation functions resolve to domain data, never Axios response
 * wrappers. Transport metadata remains available on thrown adapter errors.
 */
export const useInvalidatingMutation = <TData, TError = Error, TVariables = void, TContext = unknown>(
    mutationFn: MutationFunction<TData, TVariables>,
    queryKey: readonly unknown[],
    options: Omit<UseMutationOptions<TData, TError, TVariables, TContext>, 'mutationFn'> = {},
) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options
    return useMutation({
        ...mutationOptions,
        mutationFn,
        onSuccess: async (...args: Parameters<NonNullable<typeof onSuccess>>) => {
            await queryClient.invalidateQueries({ queryKey })
            await onSuccess?.(...args)
        },
    })
}
