import React, {
    useMemo,
} from 'react'
import {
    OverlayTrigger,
    Tooltip,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

const ChatterSmallInfo = ({
    id,
    nick,
    count,  // 
    noun,
}) => {
    // Memoize the chatter ID to prevent string concatenation on every render
    const chatterId = useMemo(() => `chatter-${id}`, [
        id,
    ])

    // Memoize the tooltip content
    const tooltipContent = useMemo(() => `${noun}: ${count}`, [
        noun,
        count,
    ])

    return (
        <OverlayTrigger
            placement="left"
            overlay={
                <Tooltip
                    id={chatterId}
                    role="tooltip"
                >
                    {tooltipContent}
                </Tooltip>
            }
        >
            <li
                tabIndex="0"
                role="listitem"
                aria-describedby={chatterId}
                aria-label={`${nick}, ${tooltipContent}`}
                style={{ cursor: 'pointer' }}
            >
                {nick}
            </li>
        </OverlayTrigger>
    )
}

ChatterSmallInfo.propTypes = {
    id: PropTypes.number.isRequired,
    nick: PropTypes.string.isRequired,
    count: PropTypes.number.isRequired,
    noun: PropTypes.string.isRequired,
}

export default React.memo(ChatterSmallInfo)
