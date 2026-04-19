import type { LoginForm, RegisterForm, User, TokenResponse } from '@/types/auth.types'
import { httpClient } from '../http/client'
import type { RequestConfig } from '@/types/common.types'

/** 登录 - 后端直接返回 {access_token, refresh_token, token_type} */
export function login(form: LoginForm): Promise<TokenResponse> {
  return httpClient.post('/api/users/login', form, { skipAuth: true } as RequestConfig).then(r => r.data)
}

/** 注册 - 后端直接返回 UserModel */
export function register(form: RegisterForm): Promise<User> {
  return httpClient.post('/api/users/register', form, { skipAuth: true } as RequestConfig).then(r => r.data)
}

/** 登出 - 后端返回 {success: true} */
export function logout(): Promise<{ success: boolean }> {
  return httpClient.post('/api/users/logout').then(r => r.data)
}

/** 获取当前用户 - 后端直接返回 UserModel */
export function getUserInfo(): Promise<User> {
  return httpClient.get('/api/users/me').then(r => r.data)
}

/** 更新用户信息 - 后端直接返回 UserModel */
export function updateUserInfo(data: Partial<User>): Promise<User> {
  return httpClient.put('/api/users/me', data).then(r => r.data)
}

/** 请求密码重置 */
export function requestPasswordReset(data: { email: string }): Promise<{ success: boolean; message: string }> {
  return httpClient.post('/api/users/request-reset', data, { skipAuth: true } as RequestConfig).then(r => r.data)
}

/** 刷新令牌 - 后端直接返回 {access_token, refresh_token, token_type} */
export function refreshToken(token: string): Promise<TokenResponse> {
  return httpClient.post('/api/users/refresh-token', { refresh_token: token }, { skipAuth: true } as RequestConfig).then(r => r.data)
}
