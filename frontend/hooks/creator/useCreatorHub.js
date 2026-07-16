import {
    useMemo, useState,
} from 'react'
import {
    mapCreatorOption, useCreators,
} from './useCreatorsQuery'

export const useCreatorHub = initialView => {
    const [selectedCreator, setSelectedCreator] = useState(null)
    const [view, setView] = useState(initialView === 'trends' ? 'trends' : 'regulars')
    const creatorsQuery = useCreators()
    const options = useMemo(
        () => creatorsQuery.data?.map(mapCreatorOption) || [],
        [creatorsQuery.data],
    )

    return {
        selectedCreator,
        creatorId: selectedCreator?.value || null,
        view,
        creatorsQuery,
        options,
        setSelectedCreator,
        setView,
    }
}
