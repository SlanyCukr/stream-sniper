'use client'

import { useCopypastaLibrary } from '@/hooks/scene/useCopypastaLibrary'
import CopypastaFilters from '@/components/scene/CopypastaFilters'
import CopypastaResults from '@/components/scene/CopypastaResults'
import CreatorLoadError from '@/components/creator/CreatorLoadError'

const Copypasta = () => {
    const library = useCopypastaLibrary()

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Copypasta</h1>
                    <p className="page-sub">The scene&apos;s most-repeated chat lines</p>
                </div>
            </div>
            <CreatorLoadError query={library.creatorsQuery} />
            <CopypastaFilters
                creators={library.creators}
                selectedCreator={library.selectedCreator}
                selectedSort={library.selectedSort}
                onCreatorChange={library.handleCreatorChange}
                onSortChange={library.handleSortChange}
            />
            <CopypastaResults
                query={library.copypastasQuery}
                pageIndex={library.pageIndex}
                onPageChange={library.setPageIndex}
            />
        </>
    )
}

export default Copypasta
