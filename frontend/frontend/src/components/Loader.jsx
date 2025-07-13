import React from 'react'
import classnames from 'classnames'
import PropTypes from 'prop-types'

/**
 * @description Base loader definition
 *      USAGE
 *          <Loader
 *              *** PROPS ***
 *          />
 *
 *      PROPS - all props are optional
 *          height    - height of loader
 *          width     - width of loader
 *          className - additional CSS classes
 *
 */

const Loader = ({ className }) => (
    <div className={classnames({
        'loader': true,
        [className]: !!className,
    })}>
        <div className="loader__inner">
            <div className="loader__content">
            </div>
        </div>
    </div>
)

Loader.propTypes = {
    className: PropTypes.string,
}

export default React.memo(Loader)
