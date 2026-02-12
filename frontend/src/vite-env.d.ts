/// <reference types="vite/client" />

// Element Plus 语言包声明
declare module 'element-plus/dist/locale/zh-cn.mjs' {
  import type { DefineLocaleReturn } from 'element-plus'
  const zhCn: DefineLocaleReturn
  export default zhCn
}

// Vite 环境变量类型扩展
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_HEARTBEAT_INTERVAL?: string
  readonly VITE_WS_HEARTBEAT_TIMEOUT?: string
  readonly VITE_WS_BASE_RETRY_DELAY?: string
  readonly VITE_WS_MAX_RETRY_DELAY?: string
  readonly VITE_WS_MAX_RETRY_COUNT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
