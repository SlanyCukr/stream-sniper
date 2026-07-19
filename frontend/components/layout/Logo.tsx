'use client'

import Link from 'next/link'

/** Crosshair brand mark + wordmark. */
const Logo = () => (
    <Link
        href="/"
        className="brand-mark"
        aria-label="Stream Sniper - Home">
        <svg
            width="30"
            height="30"
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden="true"
        >
            <circle
                cx="16"
                cy="16"
                r="11"
                stroke="#9FEF00"
                strokeWidth="1.6" />
            <circle
                cx="16"
                cy="16"
                r="2.4"
                fill="#9FEF00" />
            <path
                d="M16 1v7M16 24v7M1 16h7M24 16h7"
                stroke="#9FEF00"
                strokeWidth="1.6"
                strokeLinecap="round"
            />
        </svg>
        <span className="brand-word">
            Stream<br />
            <em>Sniper</em>
        </span>
    </Link>
)

export default Logo
