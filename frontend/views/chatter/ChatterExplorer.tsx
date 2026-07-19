'use client'

import Link from 'next/link'
import { useChatterExplorer } from '@/hooks/chatter/useChatterExplorer'
import ChatterExplorerControls from '@/components/chatter/ChatterExplorerControls'
import ChatterFootprintPanel from '@/components/chatter/ChatterFootprintPanel'
import ChatterMessagesPanel from '@/components/chatter/ChatterMessagesPanel'

interface ChatterExplorerProps {
    initialView?: string
}

const ChatterExplorer = ({ initialView = 'footprint' }: ChatterExplorerProps) => {
    const explorer = useChatterExplorer(initialView)

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Chatter explorer</h1>
                    <p className="page-sub">Trace a single chatter across every captured stream</p>
                </div>
                {explorer.chatterId ? (
                    <div className="page-actions">
                        <Link className="btn btn-outline-primary btn-sm" href={`/chatter/${explorer.chatterId}`}>
                            View passport
                        </Link>
                    </div>
                ) : null}
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
