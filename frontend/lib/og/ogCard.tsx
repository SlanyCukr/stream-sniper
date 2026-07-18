import type { OgCardData } from './fetchOgData'

/**
 * Night-ops palette, inlined as hex because Satori (next/og) resolves neither
 * SCSS variables nor CSS custom properties. Kept in sync with
 * `styles/_theme.scss` — phosphor green on deep navy-black.
 */
const COLORS = {
  bgFrom: '#0b0e13',
  bgTo: '#12161e',
  phosphor: '#9fef00',
  phosphorFill: 'rgba(159, 239, 0, 0.10)',
  phosphorEdge: 'rgba(159, 239, 0, 0.35)',
  hairline: '#232c3a',
  text: '#e8edf4',
  muted: '#8b97a8',
} as const

/**
 * The 1200×630 social-unfurl card, in the night-ops console aesthetic.
 *
 * Returns a Satori-compatible element tree: flex layouts only, inline styles
 * only, and the system sans font (remote fonts are CSP-blocked). Every element
 * with more than one child declares `display: 'flex'`, per Satori's rules.
 * Pure and side-effect free so the OG routes share one layout definition.
 */
export function OgCard({ data }: { data: OgCardData }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        width: '100%',
        height: '100%',
        padding: '72px 80px',
        backgroundColor: COLORS.bgFrom,
        backgroundImage: `linear-gradient(135deg, ${COLORS.bgFrom} 0%, ${COLORS.bgTo} 100%)`,
        color: COLORS.text,
        fontFamily: 'sans-serif',
      }}
    >
      {/* Eyebrow: phosphor mark + wordmark on the left, section kind on the right */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div
            style={{
              display: 'flex',
              width: 22,
              height: 22,
              borderRadius: 22,
              marginRight: 20,
              backgroundColor: COLORS.phosphor,
            }}
          />
          <div
            style={{
              display: 'flex',
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: 8,
              color: COLORS.phosphor,
            }}
          >
            STREAM SNIPER
          </div>
        </div>
        <div
          style={{
            display: 'flex',
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: 4,
            color: COLORS.muted,
            border: `1px solid ${COLORS.hairline}`,
            borderRadius: 8,
            padding: '10px 20px',
          }}
        >
          {data.kind}
        </div>
      </div>

      {/* Headline: large title, optional one-line subtitle */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            display: 'flex',
            fontSize: 84,
            fontWeight: 800,
            lineHeight: 1.05,
            color: COLORS.text,
          }}
        >
          {data.title}
        </div>
        {data.subtitle ? (
          <div style={{ display: 'flex', fontSize: 34, color: COLORS.muted, marginTop: 24 }}>
            {data.subtitle}
          </div>
        ) : null}
      </div>

      {/* Footer: identity tag chips above numeric stat pills (domain when empty) */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {data.tags.length > 0 ? (
          <div style={{ display: 'flex', marginBottom: 30 }}>
            {data.tags.map(tag => (
              <div
                key={tag}
                style={{
                  display: 'flex',
                  fontSize: 24,
                  color: COLORS.phosphor,
                  backgroundColor: COLORS.phosphorFill,
                  border: `1px solid ${COLORS.phosphorEdge}`,
                  borderRadius: 999,
                  padding: '8px 22px',
                  marginRight: 16,
                }}
              >
                {tag}
              </div>
            ))}
          </div>
        ) : null}

        {data.stats.length > 0 ? (
          <div style={{ display: 'flex' }}>
            {data.stats.map(stat => (
              <div key={stat.label} style={{ display: 'flex', flexDirection: 'column', marginRight: 72 }}>
                <div style={{ display: 'flex', fontSize: 54, fontWeight: 800, color: COLORS.text }}>
                  {stat.value}
                </div>
                <div
                  style={{
                    display: 'flex',
                    fontSize: 24,
                    letterSpacing: 3,
                    color: COLORS.muted,
                    marginTop: 8,
                  }}
                >
                  {stat.label.toUpperCase()}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', fontSize: 26, letterSpacing: 2, color: COLORS.muted }}>
            stream-sniper.slanycukr.com
          </div>
        )}
      </div>
    </div>
  )
}
