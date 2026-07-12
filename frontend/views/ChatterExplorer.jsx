'use client'
import {
    useState, useCallback,
} from 'react'
import { retrieveChatterSearch } from '@/lib/api'
import AsyncSearchSelect from '@/components/AsyncSearchSelect'
import ChatterFootprintPanel from '@/components/chatter/ChatterFootprintPanel'
import ChatterMessagesPanel from '@/components/chatter/ChatterMessagesPanel'

const TABS = [
    {
        key: 'footprint',
        label: 'Footprint',
    },
    {
        key: 'messages',
        label: 'Messages',
    },
]

/**
 * Chatter explorer: one chatter search feeding two views of the same target —
 * "Footprint" (which streams they appear in, aggregated) and "Messages" (their
 * individual chat lines, paginated). Previously two separate pages/routes.
 *
 * @param {object} props
 * @param {'footprint'|'messages'} [props.initialView] tab to open on first render
 *   (set from the `?view=` query so the old routes deep-link to the right tab)
 */
const ChatterExplorer = ({ initialView = 'footprint' }) => {
    const [
        selectedChatter,
        setSelectedChatter,
    ] = useState(null)
    const [
        view,
        setView,
    ] = useState(initialView === 'messages' ? 'messages' : 'footprint')

    const chatterId = selectedChatter?.value || null

    /**
     * Prefix-search chatter nicks for the autocomplete dropdown.
     * The backend returns [[id, nick, is_bot], ...]; map to react-select options,
     * preserving is_bot (null = unclassified, unknown — never coerced to false)
     * so a selected bot can be badged.
     * @param {string} query
     * @returns {Promise<Array<{value: number, label: string, isBot: boolean|null}>>}
     */
    const loadChatterOptions = useCallback(async query => {
        const trimmed = query.trim()
        if (trimmed.length < 2) {
            return []
        }
        try {
            const { data } = await retrieveChatterSearch(trimmed)
            return (data || []).map(([
                id,
                nick,
                isBot,
            ]) => ({
                value: id,
                label: nick,
                isBot: isBot ?? null,
            }))
        } catch {
            return []
        }
    }, [
    ])

    const noOptionsMessage = useCallback(({ inputValue }) => (
        inputValue && inputValue.trim().length >= 2
            ? `No chatters matching "${inputValue}"`
            : 'Type at least 2 characters to search'
    ), [
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Chatter explorer</h1>
                    <p className="page-sub">Trace a single chatter across every captured stream</p>
                </div>
            </div>

            <div
                className="toolbar"
                role="search"
            >
                <span
                    className="toolbar-label"
                    aria-hidden="true">
                    Target
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="chatter-explorer-nick-input"
                        className="visually-hidden"
                    >
                        Chatter nickname
                    </label>
                    <AsyncSearchSelect
                        instanceId="chatter-explorer-nick-select"
                        inputId="chatter-explorer-nick-input"
                        loadOptions={loadChatterOptions}
                        value={selectedChatter}
                        onChange={setSelectedChatter}
                        noOptionsMessage={noOptionsMessage}
                        placeholder="Search for a chatter..."
                        isClearable
                        aria-label="Chatter nickname"
                    />
                </div>
                {selectedChatter?.isBot === true && (
                    <span
                        className="status-chip is-warn"
                        aria-label="This chatter is flagged as a bot">
                        BOT
                    </span>
                )}
            </div>

            <div
                className="chatter-tabs"
                role="tablist"
                aria-label="Chatter view"
            >
                {TABS.map(tab => (
                    <button
                        key={tab.key}
                        type="button"
                        role="tab"
                        id={`chatter-tab-${tab.key}`}
                        aria-selected={view === tab.key}
                        aria-controls={`chatter-panel-${tab.key}`}
                        className={view === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                        onClick={() => setView(tab.key)}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            <div
                id={`chatter-panel-${view}`}
                role="tabpanel"
                aria-labelledby={`chatter-tab-${view}`}
            >
                {view === 'footprint'
                    ? <ChatterFootprintPanel chatter={selectedChatter} />
                    : (
                        <ChatterMessagesPanel
                            key={chatterId ?? 'none'}
                            chatter={selectedChatter}
                        />
                    )}
            </div>
        </>
    )
}

export default ChatterExplorer
