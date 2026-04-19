/** 分析深度选项 */
export const AnalysisDepths = [
  { value: 'quick', label: '快速分析', desc: '1-2分钟，基础观点' },
  { value: 'basic', label: '基础分析', desc: '3-5分钟，常规框架' },
  { value: 'standard', label: '标准分析', desc: '5-8分钟，多维度评估' },
  { value: 'deep', label: '深度分析', desc: '10-15分钟，全面研判' },
  { value: 'comprehensive', label: '全面分析', desc: '15-30分钟，全景报告' },
] as const

/** 分析阶段配置 */
export const AnalysisPhases = {
  PHASE1: {
    key: 'phase1',
    label: '信息收集与基础分析',
    description: '并行执行多个分析师，从不同维度收集信息',
  },
  PHASE2: {
    key: 'phase2',
    label: '多空辩论',
    description: '看涨/看跌研究员辩论，投资组合经理决策，交易员制定计划',
    agents: ['看涨研究员', '看跌研究员', '投资组合经理', '交易员'],
  },
  PHASE3: {
    key: 'phase3',
    label: '风险评估',
    description: '激进/中性/保守策略并行分析，风险管理委员会主席审查',
    agents: ['激进派', '中性派', '保守派', '风险管理主席'],
  },
  PHASE4: {
    key: 'phase4',
    label: '总结报告',
    description: '汇总所有阶段输出，生成最终投资报告与价格预测',
    agents: ['总结智能体'],
    alwaysEnabled: true,
  },
} as const

/** Phase 1 默认选中的分析师（slug 列表） */
export const DEFAULT_SELECTED_ANALYSTS = [
  'financial-news-analyst',
  'market-analyst',
  'fundamentals-analyst',
]
