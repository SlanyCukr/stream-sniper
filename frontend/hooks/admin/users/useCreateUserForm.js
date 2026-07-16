import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { USER_ROLES } from '@/lib/auth/roles'
import { useCreateAdminUser } from './useUserAdminQueries'
import { useActionFeedback } from '../shared/useActionFeedback'

const INITIAL_FORM = {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: USER_ROLES.USER,
    is_active: true,
}

const validate = form => {
    if (!form.username || !form.email || !form.password || !form.confirmPassword) {
        return 'All fields are required'
    }
    if (form.username.length < 3) return 'Username must be at least 3 characters long'
    if (form.password.length < 8) return 'Password must be at least 8 characters long'
    if (form.password !== form.confirmPassword) return 'Passwords do not match'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
        return 'Please enter a valid email address'
    }
    if (!/^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/.test(form.password)) {
        return 'Password must contain at least one letter and one number'
    }
    return null
}

export const useCreateUserForm = () => {
    const router = useRouter()
    const createUser = useCreateAdminUser()
    const feedback = useActionFeedback()
    const [formData, setFormData] = useState(INITIAL_FORM)
    const [validationError, setValidationError] = useState(null)

    const handleInputChange = event => {
        const {
            name, value, type, checked,
        } = event.target
        setFormData(previous => ({
            ...previous,
            [name]: type === 'checkbox' ? checked : value,
        }))
    }

    const handleSubmit = async event => {
        event.preventDefault()
        const validationError = validate(formData)
        if (validationError) {
            setValidationError(validationError)
            return
        }
        setValidationError(null)
        await feedback.runAction({
            action: () => createUser.mutateAsync({
                username: formData.username,
                email: formData.email,
                password: formData.password,
                role: formData.role,
                is_active: formData.is_active,
            }),
            successMessage: user => `User "${user.username}" created successfully!`,
            errorTitle: 'Failed to create user',
            onSuccess: () => {
                setFormData(INITIAL_FORM)
                setTimeout(() => router.push('/admin/users'), 2000)
            },
        })
    }

    return {
        formData,
        validationError,
        feedback,
        loading: createUser.isPending,
        handleInputChange,
        handleSubmit,
        dismissValidationError: () => setValidationError(null),
        cancel: () => router.push('/admin/users'),
    }
}
