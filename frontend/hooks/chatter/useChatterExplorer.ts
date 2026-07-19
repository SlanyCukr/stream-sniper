import {
    useCallback, useState,
} from 'react'
import { retrieveChatterSearch } from '@/lib/api/chatter'

export interface ChatterOption {
    value: number
    label: string
    isBot: boolean | null
}

type ChatterView = 'messages' | 'footprint'

export const useChatterExplorer = (initialView: string | undefined) => {
    const [selectedChatter, setSelectedChatter] = useState<ChatterOption | null>(null)
    const [view, setView] = useState<ChatterView>(initialView === 'messages' ? 'messages' : 'footprint')
    const loadChatterOptions = useCallback(async (query: string): Promise<ChatterOption[]> => {
        const trimmed = query.trim()
        if (trimmed.length < 2) return []
        const { data } = await retrieveChatterSearch(trimmed)
        return (data || []).map(result => ({
            value: result.chatter_id,
            label: result.nick,
            isBot: result.is_bot,
        }))
    }, [])
    const noOptionsMessage = useCallback(({ inputValue }: { inputValue: string }) => (
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
