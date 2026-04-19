import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Typography,
  Tag,
  Button,
  Space,
  Row, Col,
  Descriptions,
  Tabs,
  Spin,
  message,
  Progress,
  Empty,
} from 'antd'
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  ShareAltOutlined,
  ClockCircleOutlined,
  FireOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { getReportDetail, getReportDownloadUrl, type ReportDetail } from '@/services/api/reports'
import MarkdownRenderer from '@/components/ui/MarkdownRenderer'

const { Title, Text, Paragraph } = Typography

const RISK_TAG_MAP: Record<string, { color: string; label: string }> = {
  low: { color: 'success', label: '低风险' },
  medium: { color: 'warning', label: '中风险' },
  high: { color: 'error', label: '高风险' },
  低: { color: 'success', label: '低风险' },
  中等: { color: 'warning', label: '中风险' },
  高: { color: 'error', label: '高风险' },
}

/** 智能体 slug → 中文名称映射（与后端 YAML 配置的 slug 一致） */
const AGENT_NAME_MAP: Record<string, string> = {
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

/** 模块名称映射：优先使用 AGENT_NAME_MAP，兜底做格式美化 */
const MODULE_LABEL_MAP: Record<string, string> = AGENT_NAME_MAP

export default function ReportDetailPage() {
  const { id: reportId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [report, setReport] = useState<ReportDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeModule, setActiveModule] = useState('')

  useEffect(() => {
    if (!reportId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(false)
      return
    }
    getReportDetail(reportId)
      .then((res) => {
        const data = res.data
        if (data) {
          setReport(data)
          // 默认选中第一个模块
          const modules = Object.keys(data.reports || {})
          if (modules.length > 0) setActiveModule(modules[0])
        }
      })
      .catch(() => message.error('获取报告详情失败'))
      .finally(() => setLoading(false))
  }, [reportId])

  if (!reportId) {
    return (
      <Card style={{ background: 'var(--bg-card)', border: 'none' }}>
        <Empty description="缺少报告 ID 参数" />
      </Card>
    )
  }

  const modules = Object.keys(report?.reports || {})
  const riskInfo = RISK_TAG_MAP[report?.risk_level || ''] || { color: 'default', label: report?.risk_level || '未知' }

  return (
    <div style={{ padding: '0 4px' }}>
      <Spin spinning={loading}>
        {/* 返回 + 操作栏 */}
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/reports')}>
            返回列表
          </Button>
          <Space>
            <Button icon={<ShareAltOutlined />}>分享</Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => window.open(getReportDownloadUrl(reportId, 'markdown'), '_blank')}
            >
              下载报告
            </Button>
          </Space>
        </div>

        {!report ? (
          <Card style={{ background: 'var(--bg-card)', border: 'none' }}>
            <Empty description="报告不存在或已被删除" />
          </Card>
        ) : (
          <>
            {/* 报告头部信息 */}
            <Card style={{ background: 'var(--bg-card)', border: 'none', marginBottom: 16 }}>
              <Row gutter={[24, 16]} align="top">
                <Col xs={24} lg={16}>
                  <Title level={3} style={{ marginBottom: 8, color: 'var(--text-primary)' }}>
                    {report.stock_name}({report.stock_symbol}) 分析报告
                  </Title>
                  <Space size="middle" wrap>
                    <Tag>{(report as unknown as Record<string, unknown>).market_type as string ?? 'A股'}</Tag>
                    <Tag color={report.status === 'completed' ? 'success' : 'processing'}>
                      {report.status === 'completed' ? '已完成' : report.status}
                    </Tag>
                    <Tag color={riskInfo.color} icon={<SafetyCertificateOutlined />}>
                      {riskInfo.label}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {report.created_at?.slice(0, 19).replace('T', ' ')}
                    </Text>
                  </Space>

                  {report.summary && (
                    <Paragraph
                      style={{
                        marginTop: 12,
                        padding: '12px 16px',
                        background: 'var(--bg-base)',
                        borderRadius: 8,
                        borderLeft: '3px solid var(--accent-primary)',
                        fontSize: 14,
                        lineHeight: 1.8,
                        color: 'var(--text-secondary)',
                      }}
                    >
                      {report.summary}
                    </Paragraph>
                  )}
                </Col>

                <Col xs={24} lg={8}>
                  <Card
                    size="small"
                    title={<Text strong style={{ fontSize: 13 }}>核心指标</Text>}
                    style={{ background: 'var(--bg-base)', border: '1px solid var(--border-color)' }}
                    styles={{ header: { background: 'transparent', borderBottom: '1px solid var(--border-color)' } }}
                  >
                    <Descriptions column={1} size="small" styles={{ label: { color: 'var(--text-secondary)', fontSize: 12 } }}>
                      <Descriptions.Item label="置信度">
                        <Progress
                          percent={Math.round((report.confidence_score ?? 0) * 100)}
                          size="small"
                          strokeColor={report.confidence_score && report.confidence_score >= 0.7 ? '#52C41A' : '#D48806'}
                          format={(percent) => `${percent}%`}
                        />
                      </Descriptions.Item>
                      <Descriptions.Item label="投资建议">
                        <Text strong style={{ color: 'var(--accent-primary)', fontSize: 14 }}>
                          {report.recommendation || '-'}
                        </Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="Token 消耗">
                        <FireOutlined style={{ color: 'var(--accent-blue)', marginRight: 4 }} />
                        <Text>{(report.tokens_used ?? 0).toLocaleString()}</Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="执行耗时">
                        <ThunderboltOutlined style={{ color: 'var(--accent-primary)', marginRight: 4 }} />
                        <Text>{report.execution_time ? `${report.execution_time.toFixed(1)}s` : '-'}</Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="分析师">
                        <Space size={[4, 4]} wrap>
                          {(report.analysts || []).map((a) => (
                            <Tag key={a} style={{ fontSize: 11 }}>
                              {AGENT_NAME_MAP[a] || a}
                            </Tag>
                          ))}
                        </Space>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>
              </Row>
            </Card>

            {/* 关键要点 */}
            {report.key_points && report.key_points.length > 0 && (
              <Card
                title="关键要点"
                style={{ background: 'var(--bg-card)', border: 'none', marginBottom: 16 }}
                styles={{ header: { borderBottom: '1px solid var(--border-color)' } }}
              >
                <ul style={{ paddingLeft: 20, margin: 0, color: 'var(--text-secondary)' }}>
                  {report.key_points.map((point, i) => (
                    <li key={i} style={{ marginBottom: 6, lineHeight: 1.6 }}>{point}</li>
                  ))}
                </ul>
              </Card>
            )}

            {/* 报告模块内容 */}
            {modules.length > 0 && (
              <Card
                style={{ background: 'var(--bg-card)', border: 'none' }}
                styles={{ body: { padding: 0 } }}
              >
                <Tabs
                  activeKey={activeModule}
                  onChange={setActiveModule}
                  items={modules.map((key) => ({
                    key,
                    label: MODULE_LABEL_MAP[key] || key.replace(/-/g, ' '),
                    children: (
                      <div style={{ padding: '16px 20px' }}>
                        <MarkdownRenderer content={report!.reports[key]} />
                      </div>
                    ),
                  }))}
                  style={{ padding: '0 16px' }}
                />
              </Card>
            )}

            {modules.length === 0 && (
              <Card style={{ background: 'var(--bg-card)', border: 'none' }}>
                <Empty description="暂无报告模块内容" />
              </Card>
            )}
          </>
        )}
      </Spin>
    </div>
  )
}
