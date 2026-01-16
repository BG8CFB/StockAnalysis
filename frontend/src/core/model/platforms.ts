/**
 * AI 模型平台配置
 */

/** 平台类型枚举 */
export enum PlatformType {
  PRESET = 'preset', // 预设平台
  CUSTOM = 'custom'  // 自定义平台
}

/** 预设平台枚举 */
export enum PresetPlatform {
  BAIDU = 'baidu',
  ALIBABA = 'alibaba',
  TENCENT = 'tencent',
  DEEPSEEK = 'deepseek',
  MOONSHOT = 'moonshot',
  ZHIPU = 'zhipu',
  ZHIPU_CODING = 'zhipu_coding'  // 智谱AI编程套餐
}

/** 平台元数据接口 */
export interface PlatformMetadata {
  /** 平台标识 */
  id: PresetPlatform;
  /** 平台显示名称 */
  name: string;
  /** 图标组件名 */
  icon: string;
  /** API 基础 URL */
  baseUrl: string;
  /** 是否支持自动获取模型列表 */
  supportListModels: boolean;
  /** 获取模型列表的端点（如果与标准不同） */
  modelsEndpoint?: string;
  /** 预设的常见模型列表（作为兜底） */
  fallbackModels: string[];
  /** 默认请求头示例 */
  defaultHeaders?: Record<string, string>;
}

/** 预设平台配置 */
export const PRESET_PLATFORMS: Record<PresetPlatform, PlatformMetadata> = {
  [PresetPlatform.BAIDU]: {
    id: PresetPlatform.BAIDU,
    name: '百度千帆',
    icon: 'ChatLineSquare',
    baseUrl: 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat',
    supportListModels: false,
    fallbackModels: [
      'ernie-4.0-8k',
      'ernie-3.5-8k',
      'ernie-speed-8k',
      'ernie-lite-8k'
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  },

  [PresetPlatform.ALIBABA]: {
    id: PresetPlatform.ALIBABA,
    name: '阿里通义千问',
    icon: 'ChatDotSquare',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    supportListModels: true,
    fallbackModels: [
      'qwen-max',
      'qwen-plus',
      'qwen-turbo',
      'qwen-long'
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  },

  [PresetPlatform.TENCENT]: {
    id: PresetPlatform.TENCENT,
    name: '腾讯混元',
    icon: 'ChatRound',
    baseUrl: 'https://api.hunyuan.cloud.tencent.com/v1',
    supportListModels: false,
    fallbackModels: [
      'hunyuan-pro',
      'hunyuan-standard',
      'hunyuan-lite'
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  },

  [PresetPlatform.DEEPSEEK]: {
    id: PresetPlatform.DEEPSEEK,
    name: 'DeepSeek',
    icon: 'Search',
    baseUrl: 'https://api.deepseek.com/v1',
    supportListModels: true,
    fallbackModels: [
      'deepseek-chat',
      'deepseek-coder'
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  },

  [PresetPlatform.MOONSHOT]: {
    id: PresetPlatform.MOONSHOT,
    name: 'Moonshot AI (Kimi)',
    icon: 'Moon',
    baseUrl: 'https://api.moonshot.cn/v1',
    supportListModels: true,
    fallbackModels: [
      'moonshot-v1-8k',
      'moonshot-v1-32k',
      'moonshot-v1-128k'
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  },

  [PresetPlatform.ZHIPU]: {
    id: PresetPlatform.ZHIPU,
    name: '智谱AI (GLM)',
    icon: 'ChatLineSquare',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    supportListModels: false, // 智谱不提供 /models 端点
    fallbackModels: [
      'glm-4-plus',
      'glm-4-plus-coder',
      'glm-4-0520',
      'glm-4-0520-coder',
      'glm-4-air',
      'glm-4-flash'
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  },

  [PresetPlatform.ZHIPU_CODING]: {
    id: PresetPlatform.ZHIPU_CODING,
    name: '智谱AI编程套餐 (GLM Coding Plan)',
    icon: 'EditPen',
    baseUrl: 'https://open.bigmodel.cn/api/coding/paas/v4',  // ⚠️ 注意是 /coding/ 端点
    supportListModels: false,  // 编程套餐不支持 /models 端点
    fallbackModels: [
      'glm-4.7'  // 编程专用模型
    ],
    defaultHeaders: {
      'Content-Type': 'application/json'
    }
  }
};

/** 获取平台配置 */
export function getPresetPlatform(platformId: PresetPlatform): PlatformMetadata | undefined {
  return PRESET_PLATFORMS[platformId];
}

/** 获取所有预设平台列表 */
export function getPresetPlatforms(): PlatformMetadata[] {
  return Object.values(PRESET_PLATFORMS);
}
