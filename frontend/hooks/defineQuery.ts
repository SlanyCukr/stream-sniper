import { useQuery, type UseQueryOptions } from '@tanstack/react-query'

/**
 * Options callers may pass to a defined query hook: everything React Query
 * accepts except the wiring (`queryKey`/`queryFn`), which the definition owns.
 */
export type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

interface QueryDefinition<Args, T> {
    key: (args: Args) => readonly unknown[]
    fetch: (args: Args) => Promise<unknown>
    map: (value: unknown) => T
}

/**
 * Single owner of the query-hook shape: key building, fetch→map piping, and
 * error propagation (a mapper throw surfaces as the query's error) are wired
 * here once. Domain hooks declare `{ key, fetch, map }` and keep their public
 * signatures as thin wrappers, so the ~26 hand-rolled `useQuery` skeletons
 * collapse to declarations and the wiring semantics are testable in one place.
 *
 * Mirrors `useInvalidatingMutation`, which plays this role for mutations.
 */
export const defineQuery = <Args, T>({ key, fetch, map }: QueryDefinition<Args, T>) => (
    args: Args,
    options: QueryOptions<T> = {},
) => useQuery({
    ...options,
    queryKey: key(args),
    queryFn: async () => map(await fetch(args)),
})

interface GatedQueryDefinition<Args, Valid, T> {
    label: string
    key: (args: Args) => readonly unknown[]
    /** Null means "not fetchable yet" (missing/invalid id); non-null is the
     *  validated, narrowed argument shape the fetcher receives — no casts.
     *  Must be pure: it runs on every render (gating) and again at fetch time. */
    validate: (args: Args) => Valid | null
    fetch: (args: Valid) => Promise<unknown>
    map: (value: unknown) => T
}

/**
 * `defineQuery` for hooks whose arguments may not be fetchable yet (nullable
 * ids from routing/selection state). The gating policy lives here once:
 *
 * - the query is disabled until `validate` accepts the arguments (and stays
 *   composable with a caller-supplied `enabled`),
 * - the query key is still built from the raw arguments, so disabled and
 *   enabled states never collide in the cache, and
 * - the fetch path re-validates at call time and throws a `TypeError` —
 *   belt-and-braces if a caller ever forces a fetch while ungated.
 */
export const defineGatedQuery = <Args, Valid, T>({
    label, key, validate, fetch, map,
}: GatedQueryDefinition<Args, Valid, T>) => (
    args: Args,
    { enabled = true, ...options }: QueryOptions<T> = {},
) => useQuery({
    ...options,
    queryKey: key(args),
    queryFn: async () => {
        const valid = validate(args)
        if (valid === null) {
            throw new TypeError(`${label} requires valid arguments before fetching`)
        }
        return map(await fetch(valid))
    },
    enabled: validate(args) !== null && enabled,
})
