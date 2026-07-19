'use client'
import {
    useState, type ChangeEvent, type FormEvent, type ReactNode,
} from 'react'
import type { MomentReviewStatus } from '@/lib/api/moments'

export interface MomentReviewMetadata {
    clipUrl?: string | null
    note?: string | null
}

export type OnMomentReview = (
    nextStatus: MomentReviewStatus | null,
    metadata?: MomentReviewMetadata,
) => Promise<unknown>

interface ReviewButtonProps {
    activeClass?: string
    disabled: boolean
    onClick: () => void
    icon: string
    children: ReactNode
    title?: string
}

const ReviewButton = ({
    activeClass = '', disabled, onClick, icon, children, title,
}: ReviewButtonProps) => (
    <button
        type="button"
        className={`moment-review-btn${activeClass}`}
        disabled={disabled}
        onClick={onClick}
        title={title}>
        <i className={`bi ${icon}`} aria-hidden="true" />
        {children}
    </button>
)

interface MomentReviewControlsProps {
    isAdmin: boolean
    pending: boolean
    status: MomentReviewStatus | 'pending'
    clipUrl: string | null
    note: string | null
    vodHref: string | null
    onReview: OnMomentReview
}

const MomentReviewControls = ({
    isAdmin,
    pending,
    status,
    clipUrl,
    note,
    vodHref,
    onReview,
}: MomentReviewControlsProps) => {
    const [showClipForm, setShowClipForm] = useState(false)
    const [draftClipUrl, setDraftClipUrl] = useState(clipUrl || '')
    const [draftNote, setDraftNote] = useState(note || '')

    const runReview = (nextStatus: MomentReviewStatus | null, metadata?: MomentReviewMetadata) => {
        Promise.resolve(onReview(nextStatus, metadata)).catch(reviewError => {
            void reviewError
        })
    }

    const submitClip = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        try {
            await onReview('clipped', { clipUrl: draftClipUrl, note: draftNote })
            setShowClipForm(false)
        } catch (reviewError) {
            void reviewError
            // The card renders the retained mutation error; keep the editor open for retry.
        }
    }

    return (
        <>
            {isAdmin && showClipForm ? (
                <form className="moment-clip-form" onSubmit={submitClip}>
                    <label>
                        Clip URL
                        <input
                            className="form-control form-control-sm"
                            type="url"
                            required
                            value={draftClipUrl}
                            onChange={(event: ChangeEvent<HTMLInputElement>) => setDraftClipUrl(event.target.value)}
                            placeholder="https://clips.twitch.tv/..."
                        />
                    </label>
                    <label>
                        Curator note
                        <textarea
                            className="form-control form-control-sm"
                            maxLength={500}
                            value={draftNote}
                            onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setDraftNote(event.target.value)}
                        />
                    </label>
                    <div>
                        <button className="btn btn-primary btn-sm" type="submit" disabled={pending}>Save clip</button>
                        <button className="btn btn-link btn-sm" type="button" onClick={() => setShowClipForm(false)}>Cancel</button>
                    </div>
                </form>
            ) : null}

            <footer className="moment-actions">
                {vodHref ? (
                    <a className="moment-vod-link" href={vodHref} target="_blank" rel="noopener noreferrer">
                        <i className="bi bi-box-arrow-up-right" aria-hidden="true" />
                        Open VOD
                    </a>
                ) : (
                    <span className="moment-vod-missing">No VOD</span>
                )}

                {isAdmin ? (
                    <div className="moment-review" role="group" aria-label="Review actions">
                        <ReviewButton
                            activeClass={status === 'bookmarked' ? ' is-active-ok' : ''}
                            disabled={pending || status === 'bookmarked'}
                            onClick={() => runReview('bookmarked')}
                            icon="bi-bookmark-star"
                            title="Bookmark this moment">
                            Bookmark
                        </ReviewButton>
                        {status === 'bookmarked' || status === 'clipped' ? (
                            <ReviewButton
                                activeClass={status === 'clipped' ? ' is-active-ok' : ''}
                                disabled={pending}
                                onClick={() => setShowClipForm(value => !value)}
                                icon="bi-camera-video">
                                {clipUrl ? 'Edit clip' : 'Attach clip'}
                            </ReviewButton>
                        ) : null}
                        {status === 'clipped' ? (
                            <ReviewButton
                                disabled={pending}
                                onClick={() => runReview('published', { clipUrl, note })}
                                icon="bi-send">
                                Publish
                            </ReviewButton>
                        ) : null}
                        <ReviewButton
                            activeClass={status === 'rejected' ? ' is-active-warn' : ''}
                            disabled={pending || status === 'rejected'}
                            onClick={() => runReview('rejected')}
                            icon="bi-x-circle"
                            title="Reject this moment">
                            Reject
                        </ReviewButton>
                        {status !== 'pending' ? (
                            <ReviewButton
                                disabled={pending}
                                onClick={() => runReview(null)}
                                icon="bi-arrow-counterclockwise"
                                title="Clear review">
                                Clear
                            </ReviewButton>
                        ) : null}
                    </div>
                ) : null}
            </footer>
        </>
    )
}

export default MomentReviewControls
