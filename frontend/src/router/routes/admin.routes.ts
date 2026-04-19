import type { RouteObject } from 'react-router-dom'

export const adminRoutes: RouteObject[] = [
  {
    path: '/admin/users',
    lazy: async () => {
      const { default: UserManagementPage } = await import('@/pages/admin/UserManagementPage')
      return { Component: UserManagementPage }
    },
  },
]
