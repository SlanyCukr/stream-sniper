import type { Dispatch, SetStateAction } from 'react'
import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'
import TabList from '@/components/common/TabList'
import StatusChip from '@/components/common/StatusChip'
import { CHATTER_VIEWS } from '@/lib/models/chatterExplorer'
import type { ChatterOption } from '@/hooks/chatter/useChatterExplorer'

type ChatterView = 'messages' | 'footprint'

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
                <AsyncSearchSelect
                    instanceId="chatter-explorer-nick-select"
                    inputId="chatter-explorer-nick-input"
                    loadOptions={loadOptions}
                    value={selectedChatter}
                    // AsyncSearchSelect is untyped legacy JS wrapping react-select; its
                    // Option generic can't be narrowed from here, but the runtime value
                    // shape matches ChatterOption.
                    onChange={newValue => onChatterChange(newValue as ChatterOption | null)}
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
            // TabList is untyped legacy JS; its tab key is a plain string at that
            // boundary, but CHATTER_VIEWS keys are always a ChatterView.
            onChange={(key: string) => onViewChange(key as ChatterView)}
        />
    </>
)

export default ChatterExplorerControls
