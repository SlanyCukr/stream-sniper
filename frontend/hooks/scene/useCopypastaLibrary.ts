import {
    useCallback, useMemo, useState,
} from 'react'
import { keepPreviousData } from '@tanstack/react-query'
import {
    mapCreatorOption, useCreators, type CreatorOption,
} from '@/hooks/creator/useCreatorsQuery'
import { useSceneCopypastas } from './useSceneCopypastaQueries'
import { COPYPASTA_SORT_OPTIONS } from '@/lib/models/copypastaLibrary'

type SortOption = typeof COPYPASTA_SORT_OPTIONS[number]

const PAGE_SIZE = 25

export const useCopypastaLibrary = () => {
    const [selectedCreator, setSelectedCreator] = useState<CreatorOption | null>(null)
    const [selectedSort, setSelectedSort] = useState<SortOption>(COPYPASTA_SORT_OPTIONS[0])
    const [pageIndex, setPageIndex] = useState(0)
    const creatorsQuery = useCreators()
    const creators = useMemo(
        () => creatorsQuery.data?.map(mapCreatorOption) || [],
        [creatorsQuery.data],
    )
    const copypastasQuery = useSceneCopypastas({
        creatorId: selectedCreator?.value || undefined,
        sort: selectedSort?.value || 'usage',
        pageIndex,
        pageSize: PAGE_SIZE,
    }, { placeholderData: keepPreviousData })

    const handleCreatorChange = useCallback((option: CreatorOption | null) => {
        setSelectedCreator(option)
        setPageIndex(0)
    }, [])

    const handleSortChange = useCallback((option: SortOption | null) => {
        setSelectedSort(option || COPYPASTA_SORT_OPTIONS[0])
        setPageIndex(0)
    }, [])

    return {
        creators,
        creatorsQuery,
        copypastasQuery,
        selectedCreator,
        selectedSort,
        pageIndex,
        handleCreatorChange,
        handleSortChange,
        setPageIndex,
    }
}
