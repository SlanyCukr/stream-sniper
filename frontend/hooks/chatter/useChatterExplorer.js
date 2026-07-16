import {
    useCallback, useState,
} from 'react'
import { retrieveChatterSearch } from '@/lib/api/chatter'

/** @typedef {{value:number, label:string, isBot:boolean|null}} ChatterOption */

/** @param {string|undefined} initialView */
export const useChatterExplorer = initialView => {
    const [selectedChatter, setSelectedChatter] = useState(/** @type {ChatterOption|null} */ (null))
    const [view, setView] = useState(initialView === 'messages' ? 'messages' : 'footprint')
    const loadChatterOptions = useCallback(async (/** @type {string} */ query) => {
        const trimmed = query.trim()
        if (trimmed.length < 2) return []
        const { data } = await retrieveChatterSearch(trimmed)
        return (data || []).map(result => ({
            value: result.chatter_id,
            label: result.nick,
            isBot: result.is_bot,
        }))
    }, [])
    const noOptionsMessage = useCallback((/** @type {{inputValue:string}} */ { inputValue }) => (
        inputValue && inputValue.trim().length >= 2
            ? `No chatters matching "${inputValue}"`
            : 'Type at least 2 characters to search'
    ), [])

    return {
        selectedChatter,
        chatterId: selectedChatter?.value || null,
        view,
        setSelectedChatter,
        setView,
        loadChatterOptions,
        noOptionsMessage,
    }
}
