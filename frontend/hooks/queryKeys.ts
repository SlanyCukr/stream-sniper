/** Query-key factory shared by timeline readers and moment-review writers. */
export const streamTimelineKeys = {
    all: [
        'stream-timeline',
    ],
    details: () => [
        ...streamTimelineKeys.all,
        'detail',
    ],
    detail: (streamId: number) => [
        ...streamTimelineKeys.details(),
        Number(streamId),
    ],
}
