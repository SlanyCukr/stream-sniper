import { api } from '@/lib/api/client'
import type { AdminUserDto } from '@/lib/api/users'
import {
    requireBooleanField,
    requireFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { USER_ROLES, type UserRole } from '@/lib/auth/roles'

interface TokenDto {
    access_token: string
    token_type: string
}

interface MessageDto {
    message: string
}

export interface AuthUser {
    id: number
    username: string
    email: string
    role: UserRole
    isActive: boolean
    createdAt: string
}

export const mapAuthUser = (value: unknown): AuthUser => {
    const user = requireRecord(value, 'authenticated user')
    const role = requireStringField(user, 'role', 'authenticated user')
    if (role !== USER_ROLES.USER && role !== USER_ROLES.ADMIN) {
        throw new TypeError('authenticated user.role must be a recognized user role')
    }
    return {
        id: requireFiniteNumberField(user, 'id', 'authenticated user'),
        username: requireStringField(user, 'username', 'authenticated user'),
        email: requireStringField(user, 'email', 'authenticated user'),
        role,
        isActive: requireBooleanField(user, 'is_active', 'authenticated user'),
        createdAt: requireStringField(user, 'created_at', 'authenticated user'),
    }
}

export const fetchUserProfile = async (token: string): Promise<AuthUser> => mapAuthUser((
    await api.get<AdminUserDto>('/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` },
    })
).data)

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

export const updateProfile = async (userData: { email: string }): Promise<AuthUser> => mapAuthUser((
    await api.put<AdminUserDto>('/auth/me', userData)
).data)

export const requestPasswordChange = async (
    currentPassword: string,
    newPassword: string,
): Promise<MessageDto> => (
    await api.put<MessageDto>(
        '/auth/me/password',
        { current_password: currentPassword, new_password: newPassword },
    )
).data
