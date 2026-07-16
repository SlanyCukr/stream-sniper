export const USER_ROLES = Object.freeze({
  USER: 'user',
  ADMIN: 'admin',
} as const)

export type UserRole = typeof USER_ROLES[keyof typeof USER_ROLES]

export const USER_ROLE_OPTIONS: ReadonlyArray<Readonly<{
  value: UserRole
  label: string
}>> = Object.freeze([
  Object.freeze({ value: USER_ROLES.USER, label: 'User' }),
  Object.freeze({ value: USER_ROLES.ADMIN, label: 'Admin' }),
])

export const isAdminRole = (role: unknown): role is typeof USER_ROLES.ADMIN =>
  role === USER_ROLES.ADMIN
