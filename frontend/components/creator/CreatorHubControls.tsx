import Select from 'react-select'
import TabList from '@/components/common/TabList'
import { CREATOR_HUB_VIEWS } from '@/lib/models/creatorHub'
import type { CreatorOption } from '@/hooks/creator/useCreatorsQuery'

interface CreatorHubControlsProps {
    options: CreatorOption[]
    selectedCreator: CreatorOption | null
    view: string
    onCreatorChange: (option: CreatorOption | null) => void
    onViewChange: (view: string) => void
}

const CreatorHubControls = ({
    options, selectedCreator, view, onCreatorChange, onViewChange,
}: CreatorHubControlsProps) => (
    <>
        <div className="toolbar" role="search" aria-label="Creator selection">
            <span className="toolbar-label" aria-hidden="true">Creator</span>
            <div className="toolbar-field">
                <label htmlFor="creator-hub-select" className="visually-hidden">Select a creator</label>
                <Select
                    classNamePrefix="rs"
                    instanceId="creator-hub-select"
                    inputId="creator-hub-select"
                    options={options}
                    value={selectedCreator}
                    onChange={onCreatorChange}
                    placeholder="Select creator..."
                    isClearable
                    aria-label="Select a creator"
                />
            </div>
        </div>
        <TabList
            tabs={CREATOR_HUB_VIEWS}
            activeKey={view}
            idPrefix="creator"
            ariaLabel="Creator view"
            onChange={onViewChange}
        />
    </>
)

export default CreatorHubControls
