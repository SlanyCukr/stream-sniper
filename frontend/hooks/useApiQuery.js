// TanStack Query API hooks index file
export {
    useStreams,
    useStreamData,
    streamsKeys,
} from './useStreamsQuery'

export {
    useMessages,
    messagesKeys,
} from './useMessagesQuery'

export {
    useStreamMessages,
    streamMessagesKeys,
} from './useStreamMessagesQuery'

export {
    useStreamTimeline,
    streamTimelineKeys,
} from './useStreamTimelineQuery'

export {
    useCreatorTrends,
    creatorTrendsKeys,
} from './useCreatorTrendsQuery'

export {
    useCreatorRegulars,
    creatorRegularsKeys,
} from './useCreatorRegularsQuery'

export {
    useStreamReport,
    streamReportKeys,
} from './useStreamReportQuery'

export {
    streamInsightsKeys,
    useCreatorEmotes,
    useStreamEmotes,
    useStreamMentions,
    useStreamPhrases,
} from './useStreamInsightsQuery'

export {
    communityKeys,
    useCommunityOverlap,
    useCreatorNeighbors,
} from './useCommunityQuery'

export {
    momentsQueueKeys,
    useMomentReview,
    useMomentsQueue,
} from './useMomentsQueries'

export {
    sceneKeys,
    useSceneCopypastas,
    useSceneLeaderboard,
    useSceneLive,
} from './useSceneQueries'

export {
    useChatters,
    useCreators,
    useChatterId,
    useChatterStreamActivity,
    chattersKeys,
} from './useChattersQuery'

export {
    trackingKeys,
    useCreateTrackedStreamer,
    useDeleteTrackedStreamer,
    useProcessingJobs,
    useTrackedStreamerOptions,
    useTrackedStreamers,
    useTrackingStats,
    useUpdateTrackedStreamer,
} from './useTrackingQueries'

export {
    userAdminKeys,
    useAdminSystemStats,
    useAdminUsers,
    useCreateAdminUser,
    useDeleteAdminUser,
    useSetAdminUserActive,
    useUpdateAdminUser,
    useUpdateAdminUserRole,
} from './useUserAdminQueries'

export {
    systemKeys,
    useCacheStats,
    useDetailedHealth,
    useFlushCache,
    useSystemMetrics,
} from './useSystemQueries'
