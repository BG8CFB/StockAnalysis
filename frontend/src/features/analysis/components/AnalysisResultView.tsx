import { Card, Tag, Space, Divider, Typography, Row, Col, Statistic } from 'antd'
import { RiseOutlined, FallOutlined, FieldTimeOutlined, FileTextOutlined } from '@ant-design/icons'
import MarkdownRenderer from '@/components/ui/MarkdownRenderer'
import type { AnalysisResult } from '@/types/analysis.types'

const { Title, Text } = Typography

interface AnalysisResultViewProps {
  result: AnalysisResult
}

export default function AnalysisResultView({ result }: AnalysisResultViewProps) {
  const decision = result.decision || {}
  const reports = result.reports || {}
  const confidence = result.confidence_score ?? 0

  const recommendationColor =
    confidence >= 0.7 ? 'var(--accent-success)' : confidence >= 0.4 ? 'var(--accent-warning)' : 'var(--accent-error)'

  return (
    <div style={{ color: 'var(--text-primary)' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card
            style={{ background: 'var(--bg-card)', border: 'none' }}
            styles={{ body: { padding: 16 } }}
          >
            <Statistic
              title={<Text style={{ color: 'var(--text-secondary)' }}>置信度</Text>}
              value={(confidence * 100).toFixed(1)}
              suffix="%"
              styles={{ content: { color: recommendationColor, fontWeight: 700 } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            style={{ background: 'var(--bg-card)', border: 'none' }}
            styles={{ body: { padding: 16 } }}
          >
            <Statistic
              title={<Text style={{ color: 'var(--text-secondary)' }}>风险等级</Text>}
              value={result.risk_level || '中等'}
              styles={{ content: { color: 'var(--text-primary)', fontWeight: 700 } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            style={{ background: 'var(--bg-card)', border: 'none' }}
            styles={{ body: { padding: 16 } }}
          >
            <Statistic
              title={<Text style={{ color: 'var(--text-secondary)' }}>执行时间</Text>}
              value={result.execution_time}
              suffix="s"
              prefix={<FieldTimeOutlined />}
              styles={{ content: { color: 'var(--text-primary)', fontWeight: 700 } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            style={{ background: 'var(--bg-card)', border: 'none' }}
            styles={{ body: { padding: 16 } }}
          >
            <Statistic
              title={<Text style={{ color: 'var(--text-secondary)' }}>Token 消耗</Text>}
              value={result.tokens_used}
              styles={{ content: { color: 'var(--text-primary)', fontWeight: 700 } }}
            />
          </Card>
        </Col>
      </Row>

      {decision.action && (
        <Card
          style={{
            marginTop: 16,
            background: 'var(--bg-card)',
            border: 'none',
            boxShadow: '0 2px 16px rgba(201,169,110,0.08)',
          }}
        >
          <Space vertical size="small" style={{ width: '100%' }}>
            <Title level={5} style={{ color: 'var(--text-primary)', margin: 0 }}>
              交易决策
            </Title>
            <Space wrap>
              <Tag color={decision.action.includes('买入') ? 'green' : decision.action.includes('卖出') ? 'red' : 'default'}>
                {decision.action}
              </Tag>
              {decision.target_price !== undefined && (
                <Tag icon={<RiseOutlined />}>目标价: {decision.target_price}</Tag>
              )}
              {decision.confidence !== undefined && (
                <Tag>置信度: {(decision.confidence * 100).toFixed(1)}%</Tag>
              )}
              {decision.stop_loss !== undefined && (
                <Tag icon={<FallOutlined />}>止损: {decision.stop_loss}</Tag>
              )}
            </Space>
            {decision.reasoning && (
              <Text style={{ color: 'var(--text-secondary)' }}>{decision.reasoning}</Text>
            )}
          </Space>
        </Card>
      )}

      {result.summary && (
        <Card style={{ marginTop: 16, background: 'var(--bg-card)', border: 'none' }}>
          <Title level={5} style={{ color: 'var(--text-primary)', marginBottom: 12 }}>
            分析摘要
          </Title>
          <MarkdownRenderer content={result.summary} />
        </Card>
      )}

      {result.recommendation && (
        <Card style={{ marginTop: 16, background: 'var(--bg-card)', border: 'none' }}>
          <Title level={5} style={{ color: 'var(--text-primary)', marginBottom: 12 }}>
            投资建议
          </Title>
          <MarkdownRenderer content={result.recommendation} />
        </Card>
      )}

      {result.key_points && result.key_points.length > 0 && (
        <Card style={{ marginTop: 16, background: 'var(--bg-card)', border: 'none' }}>
          <Title level={5} style={{ color: 'var(--text-primary)', marginBottom: 12 }}>
            核心要点
          </Title>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            {result.key_points.map((point, idx) => (
              <li key={idx} style={{ marginBottom: 8, color: 'var(--text-primary)' }}>
                {point}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {Object.keys(reports).length > 0 && (
        <>
          <Divider style={{ borderColor: 'rgba(255,255,255,0.06)' }} />
          <Title level={5} style={{ color: 'var(--text-primary)' }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            详细报告
          </Title>
          <Space vertical size="middle" style={{ width: '100%' }}>
            {Object.entries(reports).map(([key, content]) => (
              <Card
                key={key}
                title={
                  <Text strong style={{ color: 'var(--accent-secondary)' }}>
                    {formatReportKey(key)}
                  </Text>
                }
                style={{ background: 'var(--bg-card)', border: 'none' }}
                styles={{ header: { borderBottom: '1px solid rgba(255,255,255,0.06)' } }}
              >
                <MarkdownRenderer content={content} />
              </Card>
            ))}
          </Space>
        </>
      )}
    </div>
  )
}

function formatReportKey(key: string): string {
  // 与后端 YAML 配置的 slug 保持一致
  const map: Record<string, string> = {
    // Phase 1
    'financial-news-analyst': '财经新闻分析师',
    'social-media-analyst': '社交媒体和投资情绪分析师',
    'china-market-analyst': '中国市场分析师',
    'market-analyst': '市场技术分析师',
    'fundamentals-analyst': '基本面分析师',
    'short-term-capital-analyst': '短线资金分析师',
    // Phase 2
    'bull-researcher': '看涨分析师',
    'bear-researcher': '看跌分析师',
    'research-manager': '投资组合经理',
    'trader': '专业交易员',
    // Phase 3
    'aggressive-debator': '激进策略分析师',
    'neutral-debator': '中性策略分析师',
    'conservative-debator': '保守策略分析师',
    'risk-manager': '风险管理委员会主席',
    // Phase 4
    'summarizer': '总结智能体',
  }
  return map[key] || key.replace(/-/g, ' ')
}
