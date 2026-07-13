'use client'
import { useMemo } from 'react'
import Link from 'next/link'
import Select from 'react-select'
import { useCreatorNeighbors } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

const NEIGHBOR_LIMIT = 10

/**
 * "Audience also watches": pick a creator, see the creators whose audiences most
 * overlap with theirs (ranked by shared chatters/regulars for the selected metric).
 *
 * @param {object} props
 * @param {Array} props.creators - overlap creator set (react-select options source)
 * @param {'chatters'|'regulars'} props.metric
 * @param {{value:number,label:string}|null} props.selected
 * @param {function} props.onSelect - (option|null) => void
 */
const NeighborsExplorer = ({
    creators, metric, selected, onSelect,
}) => {
    const options = useMemo(() => creators.map(c => ({
        label: c.displayName || c.nick || `#${c.creatorId}`,
        value: c.creatorId,
    })), [
        creators,
    ])

    const creatorId = selected?.value || null

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useCreatorNeighbors(creatorId, {
        metric,
        limit: NEIGHBOR_LIMIT,
    })

    const neighbors = useMemo(() => {
        const list = data?.neighbors || []
        return list.map(nbr => ({
            ...nbr,
            shared: metric === 'chatters' ? nbr.sharedChatters : nbr.sharedRegulars,
        }))
    }, [
        data,
        metric,
    ])

    const maxShared = Math.max(1, ...neighbors.map(nbr => nbr.shared || 0))

    return (
        <div className="neighbors-explorer">
            <div
                className="toolbar"
                role="search"
                aria-label="Audience-also-watches creator selection"
            >
                <span
                    className="toolbar-label"
                    aria-hidden="true"
                >
                    Creator
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="neighbors-creator-select"
                        className="visually-hidden"
                    >
                        Select a creator
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="neighbors-creator-select"
                        inputId="neighbors-creator-select"
                        options={options}
                        value={selected}
                        onChange={onSelect}
                        placeholder="Select creator..."
                        isClearable
                        aria-label="Select a creator"
                    />
                </div>
            </div>

            {!creatorId && (
                <div className="empty-state">
                    <div
                        className="empty-scope"
                        aria-hidden="true"
                    />
                    <p className="empty-title">No creator selected</p>
                    <p className="empty-hint">
                        Pick a creator to rank the channels their audience also watches.
                    </p>
                </div>
            )}

            {creatorId && isLoading && (
                <LoadingSpinner
                    size="lg"
                    text="Loading neighbors..."
                />
            )}

            {creatorId && error && (
                <ErrorAlert
                    error={error}
                    title="Failed to load neighbors"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}

            {creatorId && !isLoading && !error && neighbors.length === 0 && (
                <div className="empty-state">
                    <div
                        className="empty-scope"
                        aria-hidden="true"
                    />
                    <p className="empty-title">No shared audience</p>
                    <p className="empty-hint">
                        No overlapping {metric} recorded with other tracked creators yet.
                    </p>
                </div>
            )}

            {creatorId && !isLoading && !error && neighbors.length > 0 && (
                <ol className="rank-list neighbors-rank">
                    {neighbors.map((nbr, index) => (
                        <li key={nbr.creatorId}>
                            <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                            <Link className="nick" href={`/creator/${nbr.creatorId}`}>
                                {nbr.displayName || nbr.nick || `#${nbr.creatorId}`}
                            </Link>
                            <span className="neighbors-bar-wrap">
                                <span
                                    className="data-bar"
                                    aria-hidden="true"
                                >
                                    <span
                                        className="data-bar-fill"
                                        style={{ width: `${Math.max(4, Math.round(((nbr.shared || 0) / maxShared) * 100))}%` }}
                                    />
                                </span>
                            </span>
                            <span className="count">{(nbr.shared || 0).toLocaleString()}</span>
                        </li>
                    ))}
                </ol>
            )}
        </div>
    )
}

export default NeighborsExplorer
