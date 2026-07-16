import { useCallback, useState } from 'react'
import { toUiFailure } from '@/utils/errorUtils'

/**
 * Shared lifecycle for admin mutations. The original error object is retained
 * so ErrorAlert can still inspect HTTP status, response payload, and cause.
 */
export const useActionFeedback = () => {
    const [failure, setFailure] = useState(
        /** @type {ReturnType<typeof toUiFailure>|null} */ (null),
    )
    const [errorTitle, setErrorTitle] = useState('Action failed')
    const [success, setSuccess] = useState(null)

    const dismissError = useCallback(() => setFailure(null), [])
    const dismissSuccess = useCallback(() => setSuccess(null), [])

    const runAction = useCallback(
        /**
         * @param {{
         *   action: () => Promise<unknown>,
         *   successMessage?: string|((result:unknown) => string),
         *   errorTitle: string,
         *   onSuccess?: (result:unknown) => void|Promise<void>,
         *   onSettled?: () => void,
         * }} options
         */
        async ({
            action,
            successMessage,
            errorTitle: nextErrorTitle,
            onSuccess,
            onSettled,
        }) => {
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
