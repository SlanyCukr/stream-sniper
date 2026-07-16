import {
    useCallback, useMemo, useState,
} from 'react'
import { keepPreviousData } from '@tanstack/react-query'
import {
    mapCreatorOption, useCreators,
} from '@/hooks/creator/useCreatorsQuery'
import { useSceneCopypastas } from './useSceneCopypastaQueries'
import { COPYPASTA_SORT_OPTIONS } from '@/lib/models/copypastaLibrary'

const PAGE_SIZE = 25

export const useCopypastaLibrary = () => {
    const [selectedCreator, setSelectedCreator] = useState(null)
    const [selectedSort, setSelectedSort] = useState(COPYPASTA_SORT_OPTIONS[0])
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

    const handleCreatorChange = useCallback(option => {
        setSelectedCreator(option)
        setPageIndex(0)
    }, [])

    const handleSortChange = useCallback(option => {
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
