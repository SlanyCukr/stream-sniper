import type { Dispatch, SetStateAction } from 'react'
import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'
import TabList from '@/components/common/TabList'
import StatusChip from '@/components/common/StatusChip'
import { CHATTER_VIEWS } from '@/lib/models/chatterExplorer'
import type { ChatterView } from '@/lib/models/chatterExplorer'
import type { ChatterOption } from '@/hooks/chatter/useChatterExplorer'

interface ChatterExplorerControlsProps {
    selectedChatter: ChatterOption | null
    view: ChatterView
    onChatterChange: Dispatch<SetStateAction<ChatterOption | null>>
    onViewChange: Dispatch<SetStateAction<ChatterView>>
    loadOptions: (query: string) => Promise<ChatterOption[]>
    noOptionsMessage: (info: { inputValue: string }) => string
}

const ChatterExplorerControls = ({
    selectedChatter,
    view,
    onChatterChange,
    onViewChange,
    loadOptions,
    noOptionsMessage,
}: ChatterExplorerControlsProps) => (
    <>
        <div className="toolbar" role="search">
            <span className="toolbar-label" aria-hidden="true">Target</span>
            <div className="toolbar-field">
                <label htmlFor="chatter-explorer-nick-input" className="visually-hidden">
                    Chatter nickname
                </label>
                <AsyncSearchSelect<ChatterOption>
                    instanceId="chatter-explorer-nick-select"
                    inputId="chatter-explorer-nick-input"
                    loadOptions={loadOptions}
                    value={selectedChatter}
                    onChange={onChatterChange}
                    noOptionsMessage={noOptionsMessage}
                    placeholder="Search for a chatter..."
                    isClearable
                    aria-label="Chatter nickname"
                />
            </div>
            {selectedChatter?.isBot === true ? (
                <StatusChip variant="warn" aria-label="This chatter is flagged as a bot">BOT</StatusChip>
            ) : null}
        </div>
        <TabList
            tabs={CHATTER_VIEWS}
            activeKey={view}
            idPrefix="chatter"
            ariaLabel="Chatter view"
            onChange={onViewChange}
        />
    </>
)

export default ChatterExplorerControls
