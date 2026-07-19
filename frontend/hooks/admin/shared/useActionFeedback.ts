import { useCallback, useState } from 'react'
import { toUiFailure } from '@/utils/errorUtils'

type UiFailure = ReturnType<typeof toUiFailure>

interface RunActionOptions<TResult> {
    action: () => Promise<TResult>
    successMessage?: string | ((result: TResult) => string)
    errorTitle: string
    onSuccess?: (result: TResult) => void | Promise<void>
    onSettled?: () => void
}

type RunActionOutcome<TResult> =
    | { ok: true, value: TResult }
    | { ok: false, failure: UiFailure }

/**
 * Shared lifecycle for admin mutations. The original error object is retained
 * so ErrorAlert can still inspect HTTP status, response payload, and cause.
 */
export const useActionFeedback = () => {
    const [failure, setFailure] = useState<UiFailure | null>(null)
    const [errorTitle, setErrorTitle] = useState('Action failed')
    const [success, setSuccess] = useState<string | null | undefined>(null)

    const dismissError = useCallback(() => setFailure(null), [])
    const dismissSuccess = useCallback(() => setSuccess(null), [])

    const runAction = useCallback(
        async <TResult>({
            action,
            successMessage,
            errorTitle: nextErrorTitle,
            onSuccess,
            onSettled,
        }: RunActionOptions<TResult>): Promise<RunActionOutcome<TResult>> => {
            setFailure(null)
            setSuccess(null)
            try {
                const result = await action()
                setSuccess(typeof successMessage === 'function'
                    ? successMessage(result)
                    : successMessage)
                await onSuccess?.(result)
                return { ok: true, value: result }
            } catch (actionError) {
                console.error(`${nextErrorTitle}:`, actionError)
                const nextFailure = toUiFailure(actionError, nextErrorTitle)
                setErrorTitle(nextErrorTitle)
                setFailure(nextFailure)
                return { ok: false, failure: nextFailure }
            } finally {
                onSettled?.()
            }
        },
        [],
    )

    return {
        failure,
        errorTitle,
        success,
        runAction,
        dismissError,
        dismissSuccess,
    }
}
