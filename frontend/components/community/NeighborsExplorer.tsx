'use client'

import Select from 'react-select'
import { useNeighborsExplorerModel } from '@/hooks/community/useNeighborsExplorerModel'
import type { CreatorOption } from '@/hooks/community/useNeighborsExplorerModel'
import type { CommunityCreator, OverlapMetric } from '@/hooks/community/useCommunityQuery'
import NeighborResults from './NeighborResults'

interface NeighborsExplorerProps {
    creators: CommunityCreator[]
    metric: OverlapMetric
    selected: CreatorOption | null
    onSelect: (option: CreatorOption | null) => void
}

const NeighborsExplorer = ({
    creators, metric, selected, onSelect,
}: NeighborsExplorerProps) => {
    const model = useNeighborsExplorerModel({
        creators, metric, selected,
    })

    return (
        <div className="neighbors-explorer">
            <div className="toolbar" role="search" aria-label="Audience-also-watches creator selection">
                <span className="toolbar-label" aria-hidden="true">Creator</span>
                <div className="toolbar-field">
                    <label htmlFor="neighbors-creator-select" className="visually-hidden">
                        Select a creator
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="neighbors-creator-select"
                        inputId="neighbors-creator-select"
                        options={model.options}
                        value={selected}
                        onChange={onSelect}
                        placeholder="Select creator..."
                        isClearable
                        aria-label="Select a creator"
                    />
                </div>
            </div>
            <NeighborResults
                creatorId={model.creatorId}
                query={model.query}
                neighbors={model.neighbors}
                metric={metric}
                maxShared={model.maxShared}
            />
        </div>
    )
}

export default NeighborsExplorer
