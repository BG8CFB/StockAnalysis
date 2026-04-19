/** 路由路径常量 */
export const ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',

  ANALYSIS: {
    SINGLE: '/analysis/single',
    BATCH: '/analysis/batch',
  },

  TASKS: '/tasks',

  REPORTS: {
    LIST: '/reports',
    DETAIL: (id = ':id') => `/reports/view/${id}`,
  },

  STOCKS: {
    DETAIL: (code = ':code') => `/stocks/${code}`,
  },

  SCREENING: '/screening',
  FAVORITES: '/favorites',

  LEARNING: {
    INDEX: '/learning',
    CATEGORY: (id = ':id') => `/learning/${id}`,
    ARTICLE: (id = ':id') => `/learning/article/${id}`,
  },

  SETTINGS: {
    PROFILE: '/settings/profile',
    CONFIG: '/settings/config',
    MCP: '/settings/mcp',
    MCP_TOOLS: '/settings/mcp-tools',
    AGENTS: '/settings/agents',
    CACHE: '/settings/cache',
    USAGE: '/settings/usage',
  },

  SYSTEM: {
    DATABASE: '/system/database',
    SYNC: '/system/sync',
    SCHEDULER: '/system/scheduler',
    OPERATION_LOGS: '/system/operation-logs',
    SYSTEM_LOGS: '/system/system-logs',
    DATA_SOURCE_STATUS: '/system/data-source-status',
  },

  ADMIN: {
    USERS: '/admin/users',
    TRADING_AGENTS: '/admin/trading-agents',
  },

  ABOUT: '/about',
  NOT_FOUND: '*',
} as const
