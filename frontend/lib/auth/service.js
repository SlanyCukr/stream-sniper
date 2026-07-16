import { api } from '@/lib/api/client'

export const fetchUserProfile = async token => (
    await api.get('/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` },
    })
).data

export const authenticate = async (username, password) => {
    const { data } = await api.post('/auth/login', { username, password })
    const token = data.access_token
    return {
        token,
        profile: await fetchUserProfile(token),
    }
}

export const registerAndAuthenticate = async (username, email, password) => {
    await api.post('/auth/register', { username, email, password })
    return authenticate(username, password)
}

export const updateProfile = async userData => (
    await api.put('/auth/me', userData)
).data

export const requestPasswordChange = async (currentPassword, newPassword) => (
    await api.put(
        '/auth/me/password',
        { current_password: currentPassword, new_password: newPassword },
    )
).data
