import { InputNumber, Switch, Space, Typography, Divider, Tag, Input } from 'antd'
import { CheckCircleFilled } from '@ant-design/icons'
import { AnalysisPhases } from '@/constants/analysts'
import AnalystTeamSelector from './AnalystTeamSelector'

const { Text } = Typography

export interface AnalysisConfigFormValues {
  selected_analysts?: string[]
  custom_prompt?: string
  phase2_enabled?: boolean
  phase2_debate_rounds?: number
  phase3_enabled?: boolean
  phase3_debate_rounds?: number
}

interface AnalysisConfigFormProps {
  values: AnalysisConfigFormValues
  onChange: (values: AnalysisConfigFormValues) => void
  disabled?: boolean
}

export default function AnalysisConfigForm({ values, onChange, disabled }: AnalysisConfigFormProps) {
  const update = (patch: Partial<AnalysisConfigFormValues>) => {
    onChange({ ...values, ...patch })
  }

  return (
    <Space vertical size="middle" style={{ width: '100%' }}>
      {/* 第一阶段：分析师团队 */}
      <div>
        <div style={{ marginBottom: 8 }}>
          <Text strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>
            第一阶段 · {AnalysisPhases.PHASE1.label}
          </Text>
          <Text style={{ color: 'var(--text-secondary)', fontSize: 12, marginLeft: 8 }}>
            选择参与分析的研究员
          </Text>
        </div>
        <AnalystTeamSelector
          value={values.selected_analysts || []}
          onChange={(v) => update({ selected_analysts: v })}
          disabled={disabled}
        />
      </div>

      <Divider style={{ margin: '4px 0' }} />

      {/* 第二阶段：多空辩论 */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>
            第二阶段 · {AnalysisPhases.PHASE2.label}
          </Text>
          <Switch
            checked={values.phase2_enabled !== false}
            onChange={(v) => update({ phase2_enabled: v })}
            disabled={disabled}
            size="small"
          />
        </div>
        {values.phase2_enabled !== false ? (
          <div>
            <div style={{ marginBottom: 8 }}>
              {AnalysisPhases.PHASE2.agents.map((name) => (
                <Tag key={name} color="blue" style={{ marginBottom: 4 }}>{name}</Tag>
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text style={{ color: 'var(--text-secondary)', fontSize: 13 }}>辩论轮数</Text>
              <InputNumber
                min={1}
                max={4}
                value={values.phase2_debate_rounds ?? 2}
                onChange={(v) => update({ phase2_debate_rounds: v ?? 2 })}
                disabled={disabled}
                size="small"
                style={{ width: 64 }}
              />
              <Text style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>（1-4 次）</Text>
            </div>
          </div>
        ) : (
          <Text type="secondary" style={{ fontSize: 13 }}>已跳过多空辩论阶段</Text>
        )}
      </div>

      <Divider style={{ margin: '4px 0' }} />

      {/* 第三阶段：风险评估 */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>
            第三阶段 · {AnalysisPhases.PHASE3.label}
          </Text>
          <Switch
            checked={values.phase3_enabled !== false}
            onChange={(v) => update({ phase3_enabled: v })}
            disabled={disabled}
            size="small"
          />
        </div>
        {values.phase3_enabled !== false ? (
          <div>
            <div style={{ marginBottom: 8 }}>
              {AnalysisPhases.PHASE3.agents.map((name) => (
                <Tag key={name} color="orange" style={{ marginBottom: 4 }}>{name}</Tag>
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text style={{ color: 'var(--text-secondary)', fontSize: 13 }}>辩论轮数</Text>
              <InputNumber
                min={1}
                max={4}
                value={values.phase3_debate_rounds ?? 2}
                onChange={(v) => update({ phase3_debate_rounds: v ?? 2 })}
                disabled={disabled}
                size="small"
                style={{ width: 64 }}
              />
              <Text style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>（1-4 次）</Text>
            </div>
          </div>
        ) : (
          <Text type="secondary" style={{ fontSize: 13 }}>已跳过风险评估阶段</Text>
        )}
      </div>

      <Divider style={{ margin: '4px 0' }} />

      {/* 第四阶段：总结报告（始终启用） */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>
            第四阶段 · {AnalysisPhases.PHASE4.label}
          </Text>
          <Tag icon={<CheckCircleFilled />} color="success" style={{ fontSize: 12 }}>始终启用</Tag>
        </div>
        <Text style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
          {AnalysisPhases.PHASE4.description}
        </Text>
      </div>

      <Divider style={{ margin: '4px 0' }} />

      {/* 自定义提示词 */}
      <div>
        <Text strong style={{ color: 'var(--text-primary)', fontSize: 14, display: 'block', marginBottom: 8 }}>
          自定义提示词
        </Text>
        <Input.TextArea
          value={values.custom_prompt}
          onChange={(e) => update({ custom_prompt: e.target.value })}
          placeholder="可选，补充特殊分析要求"
          disabled={disabled}
          autoSize={{ minRows: 2, maxRows: 4 }}
        />
      </div>
    </Space>
  )
}
