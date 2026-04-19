/** 后端直接返回的令牌响应 */
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  username: string
  display_name?: string
  role: string
  status: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
  last_login_at?: string
  avatar?: string
  preferences?: UserPreferences
  permissions?: string[]
  roles?: string[]
}

export interface UserPreferences {
  default_market?: string
  default_depth?: string
  default_analysts?: string[]
  auto_refresh?: boolean
  refresh_interval?: number
  ui_theme?: string
  language?: string
  notifications_enabled?: boolean
}

export interface LoginForm {
  account: string
  password: string
  remember?: boolean
}

export interface RegisterForm {
  username: string
  email: string
  password: string
  confirm_password: string
}
