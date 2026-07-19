import Select from 'react-select'
import { COPYPASTA_SORT_OPTIONS } from '@/lib/models/copypastaLibrary'
import type { CreatorOption } from '@/hooks/creator/useCreatorsQuery'

type CopypastaSortOption = typeof COPYPASTA_SORT_OPTIONS[number]

interface CopypastaFiltersProps {
    creators: CreatorOption[]
    selectedCreator: CreatorOption | null
    selectedSort: CopypastaSortOption
    onCreatorChange: (option: CreatorOption | null) => void
    onSortChange: (option: CopypastaSortOption | null) => void
}

const CopypastaFilters = ({
    creators,
    selectedCreator,
    selectedSort,
    onCreatorChange,
    onSortChange,
}: CopypastaFiltersProps) => (
    <div className="toolbar copypasta-toolbar" role="search" aria-label="Copypasta filters">
        <div className="toolbar-field copypasta-creator-field">
            <label htmlFor="copypasta-creator-select" className="visually-hidden">
                Filter by creator
            </label>
            <Select
                classNamePrefix="rs"
                instanceId="copypasta-creator-select"
                inputId="copypasta-creator-select"
                options={creators}
                value={selectedCreator}
                onChange={onCreatorChange}
                placeholder="All creators..."
                isClearable
                aria-label="Filter by creator"
            />
        </div>
        <div className="toolbar-field copypasta-sort-field">
            <label htmlFor="copypasta-sort-select" className="visually-hidden">
                Sort order
            </label>
            <Select
                classNamePrefix="rs"
                instanceId="copypasta-sort-select"
                inputId="copypasta-sort-select"
                options={COPYPASTA_SORT_OPTIONS}
                value={selectedSort}
                onChange={onSortChange}
                isSearchable={false}
                aria-label="Sort order"
            />
        </div>
    </div>
)

export default CopypastaFilters
