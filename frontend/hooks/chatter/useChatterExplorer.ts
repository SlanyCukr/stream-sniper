import { useState } from 'react'
import { retrieveChatterSearch } from '@/lib/api/chatter'
import {
    requireArray,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import type { ChatterView } from '@/lib/models/chatterExplorer'

export interface ChatterOption {
    value: number
    label: string
    isBot: boolean | null
}

/** Async chatter-picker option loader shared by every chatter search select. */
export const loadChatterOptions = async (query: string): Promise<ChatterOption[]> => {
    const trimmed = query.trim()
    if (trimmed.length < 2) return []
    const data = await retrieveChatterSearch(trimmed)
    return requireArray(data, 'chatter search results').map((value, index) => {
        const label = `chatter search result[${index}]`
        const result = requireRecord(value, label)
        return {
            value: requireFiniteNumberField(result, 'chatter_id', label),
            label: requireStringField(result, 'nick', label),
            isBot: requireNullableBooleanField(result, 'is_bot', label),
        }
    })
}

/** Matching empty-state copy for the chatter search select's 2-char gate. */
export const noOptionsMessage = ({ inputValue }: { inputValue: string }): string => (
    inputValue && inputValue.trim().length >= 2
        ? `No chatters matching "${inputValue}"`
        : 'Type at least 2 characters to search'
)

export const useChatterExplorer = (initialView: string | undefined) => {
    const [selectedChatter, setSelectedChatter] = useState<ChatterOption | null>(null)
    const [view, setView] = useState<ChatterView>(initialView === 'messages' ? 'messages' : 'footprint')

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
