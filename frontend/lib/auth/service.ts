import { api } from '@/lib/api/client'
import type { AdminUserDto } from '@/lib/api/users'

interface TokenDto {
    access_token: string
    token_type: string
}

interface MessageDto {
    message: string
}

export const fetchUserProfile = async (token: string): Promise<AdminUserDto> => (
    await api.get<AdminUserDto>('/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` },
    })
).data

export const authenticate = async (username: string, password: string) => {
    const { data } = await api.post<TokenDto>('/auth/login', { username, password })
    const token = data.access_token
    return {
        token,
        profile: await fetchUserProfile(token),
    }
}

export const registerAndAuthenticate = async (username: string, email: string, password: string) => {
    await api.post('/auth/register', { username, email, password })
    return authenticate(username, password)
}

export const updateProfile = async (userData: { email: string }): Promise<AdminUserDto> => (
    await api.put<AdminUserDto>('/auth/me', userData)
).data

export const requestPasswordChange = async (
    currentPassword: string,
    newPassword: string,
): Promise<MessageDto> => (
    await api.put<MessageDto>(
        '/auth/me/password',
        { current_password: currentPassword, new_password: newPassword },
    )
).data
