import type { NextConfig } from 'next'

// Server-side only (NOT NEXT_PUBLIC): where /api/* is proxied.
// Prod compose: http://stream-sniper-api:5002 | dev compose: http://api:5002 | bare metal: http://localhost:5002
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || 'http://localhost:5002'

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  sassOptions: {
    // let bare `@import "bootstrap/..."` resolve from node_modules
    includePaths: ['node_modules'],
  },
  async rewrites() {
    return [
      {
        // strips the /api prefix to match old nginx `proxy_pass .../;`
        source: '/api/:path*',
        destination: `${API_PROXY_TARGET}/:path*`,
      },
    ]
  },
  async redirects() {
    return [
      // The old chatter pages merged into the unified /chatter explorer.
      // Real HTTP redirects (kept non-permanent so browsers don't hard-cache
      // the move while the app is still evolving) preserve old bookmarks/links.
      {
        source: '/chatter-footprint',
        destination: '/chatter?view=footprint',
        permanent: false,
      },
      {
        source: '/chatter-messages',
        destination: '/chatter?view=messages',
        permanent: false,
      },
    ]
  },
}

export default nextConfig
