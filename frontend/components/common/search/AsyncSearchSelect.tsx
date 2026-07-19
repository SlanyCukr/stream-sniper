'use client'
import type { GroupBase } from 'react-select'
import AsyncSelect from 'react-select/async'
import AsyncCreatableSelect from 'react-select/async-creatable'
import type { AsyncProps } from 'react-select/async'
import {
    useAsyncSearchLoader, type SearchOption,
} from '@/hooks/useAsyncSearchLoader'

type BaseSelectProps = Omit<
    AsyncProps<SearchOption, boolean, GroupBase<SearchOption>>,
    'loadOptions' | 'defaultOptions'
>

interface AsyncSearchSelectProps extends BaseSelectProps {
    loadOptions: (query: string) => Promise<SearchOption[]>
    debounceMs?: number
    creatable?: boolean
    onLoadError?: (error: unknown) => void
    loadErrorMessage?: string
    defaultOptions?: boolean | SearchOption[]
}

const DEFAULT_DEBOUNCE_MS = 300

/**
 * Debounced async react-select wrapper for server-backed autocomplete.
 *
 * react-select's AsyncSelect calls loadOptions on every keystroke; we wrap it in
 * a small setTimeout debounce so a suggestion request only fires once the user
 * pauses typing. Set `creatable` to allow selecting a value the search didn't
 * surface (used by the add-streamer field, since Twitch search only returns
 * channels active in the last 6 months).
 */
const AsyncSearchSelect = ({
    loadOptions,
    debounceMs = DEFAULT_DEBOUNCE_MS,
    creatable = false,
    onLoadError = undefined,
    loadErrorMessage = 'Search unavailable. Retry or change the query.',
    defaultOptions = false,
    ...selectProps
}: AsyncSearchSelectProps) => {
    const loader = useAsyncSearchLoader({
        loadOptions,
        onLoadError,
        debounceMs,
    })

    const SelectComponent = creatable ? AsyncCreatableSelect : AsyncSelect

    return (
        <div>
            <SelectComponent
                key={loader.retryVersion}
                classNamePrefix="rs"
                loadOptions={loader.debouncedLoadOptions}
                defaultOptions={loader.retryOptions ?? defaultOptions}
                {...selectProps}
            />
            {Boolean(loader.loadError) && (
                <div
                    className="small text-danger mt-1 d-flex align-items-center gap-2"
                    role="alert">
                    <span>{String(loadErrorMessage)}</span>
                    <button
                        type="button"
                        className="btn btn-link btn-sm p-0"
                        onClick={loader.retryLastSearch}
                        disabled={loader.retrying}
                        aria-label="Retry search">
                        {loader.retrying ? 'Retrying...' : 'Retry'}
                    </button>
                </div>
            )}
        </div>
    )
}

export default AsyncSearchSelect
