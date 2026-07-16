import { useCallback } from 'react'

export const useFormFieldChange = (setFormData, setError) => useCallback(event => {
    const {
        name, value,
    } = event.target
    setFormData(previous => ({
        ...previous,
        [name]: value,
    }))
    setError('')
}, [setFormData, setError])
