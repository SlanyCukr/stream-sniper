// Wire fragments the backend reuses across domains — typed once so the three
// adapters consuming them (chatter passport, head-to-head, scene rankings)
// cannot drift on the shape.

/** Backend's shared home-channel aggregate (null = no qualifying channel). */
export interface HomeChannelDto {
  creator_id: number
  creator_nick: string
  creator_display_name: string
  messages: number
  share: number
}

/** Rule-based identity badge derived server-side; stable key + label + reason. */
export interface ArchetypeBadgeDto {
  key: string
  label: string
  description: string
}
