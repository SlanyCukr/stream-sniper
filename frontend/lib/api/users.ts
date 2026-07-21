import { api, buildQuery, getJson } from './client'
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

export interface CreateAdminUserCommand {
  username: string
  email: string
  password: string
  role: AdminUserDto['role']
  isActive: boolean
}

export interface UpdateAdminUserCommand {
  email?: string
  role?: AdminUserDto['role']
  isActive?: boolean
}

interface CreateAdminUserRequest extends Omit<CreateAdminUserCommand, 'isActive'> {
  is_active: boolean
}

interface UpdateAdminUserRequest extends Omit<UpdateAdminUserCommand, 'isActive'> {
  is_active?: boolean
}

export const retrieveAdminSystemStats = () => getJson<AdminStatsDto>('/auth/admin/stats')

export const retrieveUsers = (request: UserListRequest = {}) => getJson<UserListDto>(
  '/auth/users',
  { offset: request.rowOffset, limit: request.pageSize },
)

export const createAdminUser = (command: CreateAdminUserCommand) => {
  const { isActive, ...user } = command
  const request: CreateAdminUserRequest = { ...user, is_active: isActive }
  return api.post<AdminUserDto>('/auth/users', request)
}

export const updateUser = (userId: number, command: UpdateAdminUserCommand) => {
  const { isActive, ...changes } = command
  const request: UpdateAdminUserRequest = {
    ...changes,
    ...(isActive === undefined ? {} : { is_active: isActive }),
  }
  return api.put<AdminUserDto>(`/auth/users/${userId}`, request)
}

export const updateUserRole = (userId: number, role: AdminUserDto['role']) =>
  api.put<AdminUserDto>(`/auth/users/${userId}/role?${buildQuery({ new_role: role })}`)

export const setUserActive = (userId: number, isActive: boolean) =>
  api.put<AdminUserDto>(`/auth/users/${userId}/${isActive ? 'activate' : 'deactivate'}`)

export const deleteUser = (userId: number) =>
  api.delete<void>(`/auth/users/${userId}`)
