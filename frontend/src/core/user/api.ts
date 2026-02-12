/**
 * 用户核心 API 接口
 * 注意：所有用户相关的 API 已统一到 @core/auth/api.ts
 * 此文件仅作为过渡，建议直接从 @core/auth/api 导入
 */

// 重新导出所有 API，保持向后兼容
export {
  authApi,
  userApi,
} from '@core/auth/api'

// 类型也重新导出
export type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserInfo,
  UserPreferences,
  UpdatePreferencesRequest,
} from '@core/auth/api'

// 验证码类型（如果需要可以取消注释）
// export type { CaptchaGenerateResponse, CaptchaRequiredResponse } from '../components/SliderCaptcha.vue'
