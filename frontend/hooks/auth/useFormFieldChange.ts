import {
    useCallback, type ChangeEvent, type Dispatch, type SetStateAction,
} from 'react'

export const useFormFieldChange = <Form>(
    setFormData: Dispatch<SetStateAction<Form>>,
    setError: Dispatch<SetStateAction<string>>,
) => useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const {
        name, value,
    } = event.target
    setFormData(previous => ({
        ...previous,
        // name is a dynamic field name; TS can't verify it maps to a key of the generic Form.
        [name]: value,
    } as Form))
    setError('')
}, [setFormData, setError])
