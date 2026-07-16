'use client'

import { useChatterExplorer } from '@/hooks/chatter/useChatterExplorer'
import ChatterExplorerControls from '@/components/chatter/ChatterExplorerControls'
import ChatterFootprintPanel from '@/components/chatter/ChatterFootprintPanel'
import ChatterMessagesPanel from '@/components/chatter/ChatterMessagesPanel'

const ChatterExplorer = ({ initialView = 'footprint' }) => {
    const explorer = useChatterExplorer(initialView)

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Chatter explorer</h1>
                    <p className="page-sub">Trace a single chatter across every captured stream</p>
                </div>
            </div>
            <ChatterExplorerControls
                selectedChatter={explorer.selectedChatter}
                view={explorer.view}
                onChatterChange={explorer.setSelectedChatter}
                onViewChange={explorer.setView}
                loadOptions={explorer.loadChatterOptions}
                noOptionsMessage={explorer.noOptionsMessage}
            />
            <div
                id={`chatter-panel-${explorer.view}`}
                role="tabpanel"
                aria-labelledby={`chatter-tab-${explorer.view}`}
            >
                {explorer.view === 'footprint' ? (
                    <ChatterFootprintPanel chatter={explorer.selectedChatter} />
                ) : (
                    <ChatterMessagesPanel
                        key={explorer.chatterId ?? 'none'}
                        chatter={explorer.selectedChatter}
                    />
                )}
            </div>
        </>
    )
}

export default ChatterExplorer
