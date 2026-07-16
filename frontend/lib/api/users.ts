import { api, buildQuery } from './client'
import type { UserRole } from '@/lib/auth/roles'

export interface UserListRequest {
  rowOffset?: number
  pageSize?: number
}

export interface AdminUserDto {
  id: number
  username: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface UserListDto {
  users: AdminUserDto[]
  total: number
  offset: number
  limit: number
}

export interface AdminStatsDto {
  total_users: number
  active_users: number
  admin_users: number
  recent_registrations: number
}

export interface CreateAdminUserRequest {
  username: string
  email: string
  password: string
  role: AdminUserDto['role']
  is_active: boolean
}

export interface UpdateAdminUserRequest {
  email?: string
  role?: AdminUserDto['role']
  is_active?: boolean
}

export const retrieveAdminSystemStats = () => api.get<AdminStatsDto>('/auth/admin/stats')

export const retrieveUsers = (request: UserListRequest = {}) => api.get<UserListDto>(
  `/auth/users?${buildQuery({ offset: request.rowOffset, limit: request.pageSize })}`,
)

export const createAdminUser = (user: CreateAdminUserRequest) =>
  api.post<AdminUserDto>('/auth/users', user)

export const updateUser = (userId: number, changes: UpdateAdminUserRequest) =>
  api.put<AdminUserDto>(`/auth/users/${userId}`, changes)

export const updateUserRole = (userId: number, role: AdminUserDto['role']) =>
  api.put<AdminUserDto>(`/auth/users/${userId}/role?${buildQuery({ new_role: role })}`)

export const setUserActive = (userId: number, isActive: boolean) =>
  api.put<AdminUserDto>(`/auth/users/${userId}/${isActive ? 'activate' : 'deactivate'}`)

export const deleteUser = (userId: number) =>
  api.delete<void>(`/auth/users/${userId}`)
