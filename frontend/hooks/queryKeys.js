/** Query-key factory shared by timeline readers and moment-review writers. */
export const streamTimelineKeys = {
    all: [
        'stream-timeline',
    ],
    details: () => [
        ...streamTimelineKeys.all,
        'detail',
    ],
    detail: (/** @type {number} */ streamId) => [
        ...streamTimelineKeys.details(),
        Number(streamId),
    ],
}
