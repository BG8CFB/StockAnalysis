/**
 * 数据源状态监控页面
 * 功能：市场概览、数据源健康度、重试操作
 */

import { useState, useEffect, useRef } from 'react'
import {
  Card, Button, Space, Typography, Tag, Table, Spin, Empty,
  Modal, Descriptions, Timeline, Row, Col, Statistic,
} from 'antd'
import { globalMessage } from '@/services/http/message-ref'
import {
  DatabaseOutlined, ReloadOutlined, SyncOutlined,
  CheckCircleOutlined, WarningOutlined, CloseCircleOutlined,
  QuestionCircleOutlined, ThunderboltOutlined, HistoryOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getDataSourceOverview,
  getMarketDetail,
  getDataSourceHistory,
  retryDataSource,
  refreshAllDataSources,
} from '@/services/api/data-source-status'
import type { DataSourceStatus, DataSourceInfo, DataSourceHistoryItem } from '@/types/admin.types'

const { Title, Text } = Typography

/** 状态颜色映射 */
const STATUS_CONFIG: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  healthy: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    label: '健康',
  },
  degraded: {
    color: 'warning',
    icon: <WarningOutlined />,
    label: '降级',
  },
  unhealthy: {
    color: 'error',
    icon: <CloseCircleOutlined />,
    label: '异常',
  },
  unknown: {
    color: 'default',
    icon: <QuestionCircleOutlined />,
    label: '未知',
  },
}

function StatusTag({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown
  return (
    <Tag color={config.color} icon={config.icon}>
      {config.label}
    </Tag>
  )
}

export default function DataSourceStatusPage() {
  const [overview, setOverview] = useState<DataSourceStatus[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [currentMarket, setCurrentMarket] = useState<DataSourceStatus | null>(null)
  const [historyData, setHistoryData] = useState<DataSourceHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [retryLoading, setRetryLoading] = useState<Record<string, boolean>>({})

  const initializedRef = useRef(false)

  /** 加载概览数据 */
  const loadOverview = async () => {
    setLoading(true)
    try {
      const res = await getDataSourceOverview()
      const data = res.data as DataSourceStatus[] | undefined
      setOverview(data ?? [])
    } catch {
      globalMessage?.error('加载数据源状态失败')
      setOverview([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    loadOverview()
  }, [])

  /** 刷新所有数据源 */
  const handleRefreshAll = async () => {
    setRefreshing(true)
    try {
      await refreshAllDataSources()
      globalMessage?.success('已触发全局刷新')
      await loadOverview()
    } catch {
      globalMessage?.error('刷新失败')
    } finally {
      setRefreshing(false)
    }
  }

  /** 查看市场详情 */
  const handleViewMarket = async (market: DataSourceStatus) => {
    setCurrentMarket(market)
    setDetailOpen(true)
    try {
      const res = await getMarketDetail(market.market)
      const data = res.data as DataSourceStatus | undefined
      if (data) setCurrentMarket(data)
    } catch {
      globalMessage?.error('加载市场详情失败')
    }
  }

  /** 查看历史 */
  const handleViewHistory = async (market: string, dataType: string) => {
    setHistoryOpen(true)
    setHistoryLoading(true)
    try {
      const res = await getDataSourceHistory(market, dataType, 50)
      const data = res.data as DataSourceHistoryItem[] | undefined
      setHistoryData(data ?? [])
    } catch {
      globalMessage?.error('加载历史记录失败')
      setHistoryData([])
    } finally {
      setHistoryLoading(false)
    }
  }

  /** 重试数据源 */
  const handleRetry = async (market: string, dataType: string, sourceId: string) => {
    const key = `${market}-${dataType}-${sourceId}`
    setRetryLoading(prev => ({ ...prev, [key]: true }))
    try {
      await retryDataSource(market, dataType, sourceId)
      globalMessage?.success('重试请求已发送')
      if (currentMarket) {
        const res = await getMarketDetail(currentMarket.market)
        const data = res.data as DataSourceStatus | undefined
        if (data) setCurrentMarket(data)
      }
    } catch {
      globalMessage?.error('重试失败')
    } finally {
      setRetryLoading(prev => ({ ...prev, [key]: false }))
    }
  }

  /** 统计各状态数量 */
  const stats = overview.reduce(
    (acc, m) => {
      acc.total += m.sources.length
      m.sources.forEach((s) => {
        if (s.status === 'healthy') acc.healthy++
        else if (s.status === 'degraded') acc.degraded++
        else if (s.status === 'unhealthy') acc.unhealthy++
        else acc.unknown++
      })
      return acc
    },
    { total: 0, healthy: 0, degraded: 0, unhealthy: 0, unknown: 0 }
  )

  const columns: ColumnsType<DataSourceStatus> = [
    {
      title: '市场',
      dataIndex: 'market_label',
      width: 120,
      render: (text: string, record: DataSourceStatus) => (
        <Space>
          <DatabaseOutlined />
          <Text strong>{text || record.market}</Text>
        </Space>
      ),
    },
    {
      title: '整体状态',
      dataIndex: 'overall_status',
      width: 110,
      render: (status: string) => <StatusTag status={status} />,
    },
    {
      title: '数据源数量',
      dataIndex: 'sources',
      width: 100,
      render: (sources: DataSourceInfo[]) => sources.length,
    },
    {
      title: '健康 / 降级 / 异常',
      width: 200,
      render: (_, record: DataSourceStatus) => {
        const h = record.sources.filter((s) => s.status === 'healthy').length
        const d = record.sources.filter((s) => s.status === 'degraded').length
        const u = record.sources.filter((s) => s.status === 'unhealthy').length
        return (
          <Space>
            <Tag color="success">{h}</Tag>
            <Tag color="warning">{d}</Tag>
            <Tag color="error">{u}</Tag>
          </Space>
        )
      },
    },
    {
      title: '最后更新',
      dataIndex: 'last_updated',
      width: 170,
      render: (t: string) => (
        <Text style={{ fontSize: 12 }}>{new Date(t).toLocaleString()}</Text>
      ),
    },
    {
      title: '操作',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewMarket(record)}
        >
          详情
        </Button>
      ),
    },
  ]

  const sourceColumns: ColumnsType<DataSourceInfo> = [
    {
      title: '数据源',
      dataIndex: 'name',
      width: 150,
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => <StatusTag status={status} />,
    },
    {
      title: '延迟',
      dataIndex: 'latency_ms',
      width: 90,
      render: (ms: number | undefined) =>
        ms != null ? <Text>{ms}ms</Text> : '-',
    },
    {
      title: '最后同步',
      dataIndex: 'last_sync_at',
      width: 170,
      render: (t: string | undefined) =>
        t ? (
          <Text style={{ fontSize: 12 }}>{new Date(t).toLocaleString()}</Text>
        ) : (
          '-'
        ),
    },
    {
      title: '下次同步',
      dataIndex: 'next_sync_at',
      width: 170,
      render: (t: string | undefined) =>
        t ? (
          <Text style={{ fontSize: 12 }}>{new Date(t).toLocaleString()}</Text>
        ) : (
          '-'
        ),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      ellipsis: true,
      render: (text: string | undefined) =>
        text ? <Text type="danger">{text}</Text> : '-',
    },
    {
      title: '操作',
      width: 180,
      fixed: 'right',
      render: (_, record) => {
        const key = `${currentMarket?.market ?? ''}-${record.type}-${record.id}`
        return (
          <Space size="small">
            <Button
              size="small"
              icon={<HistoryOutlined />}
              onClick={() =>
                handleViewHistory(
                  currentMarket?.market ?? '',
                  record.type
                )
              }
            >
              历史
            </Button>
            <Button
              size="small"
              type="primary"
              icon={<ThunderboltOutlined />}
              loading={retryLoading[key]}
              onClick={() =>
                handleRetry(
                  currentMarket?.market ?? '',
                  record.type,
                  record.id
                )
              }
            >
              重试
            </Button>
          </Space>
        )
      },
    },
  ]

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* 页面标题 + 统计 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <div>
            <Title level={4} style={{ margin: '0 0 8px' }}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              数据源状态
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              监控各市场数据源的同步状态和健康度
            </Text>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadOverview}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={handleRefreshAll}
              loading={refreshing}
            >
              全局刷新
            </Button>
          </Space>
        </div>

        {/* 统计卡片 */}
        <Row gutter={[16, 12]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={8} md={4}>
            <Statistic
              title="总计"
              value={stats.total}
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={5}>
            <Statistic
              title="健康"
              value={stats.healthy}
              valueStyle={{ color: '#52C41A' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={5}>
            <Statistic
              title="降级"
              value={stats.degraded}
              valueStyle={{ color: '#FAAD14' }}
              prefix={<WarningOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={5}>
            <Statistic
              title="异常"
              value={stats.unhealthy}
              valueStyle={{ color: '#FF4D4F' }}
              prefix={<CloseCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={5}>
            <Statistic
              title="未知"
              value={stats.unknown}
              prefix={<QuestionCircleOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* 市场概览表格 */}
      <Card size="small">
        <Table
          dataSource={overview}
          columns={columns}
          rowKey="market"
          loading={loading}
          size="small"
          scroll={{ x: 800 }}
          locale={{
            emptyText: (
              <Empty
                description="暂无数据源状态数据"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>

      {/* 市场详情弹窗 */}
      <Modal
        title={
          currentMarket
            ? `${currentMarket.market_label || currentMarket.market} - 数据源详情`
            : '数据源详情'
        }
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false)
          setCurrentMarket(null)
        }}
        footer={[
          <Button key="close" onClick={() => setDetailOpen(false)}>
            关闭
          </Button>,
        ]}
        width={900}
      >
        <Spin spinning={loading}>
          {currentMarket && (
            <div>
              <Descriptions bordered size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="市场">
                  {currentMarket.market_label || currentMarket.market}
                </Descriptions.Item>
                <Descriptions.Item label="整体状态">
                  <StatusTag status={currentMarket.overall_status} />
                </Descriptions.Item>
                <Descriptions.Item label="数据源数量">
                  {currentMarket.sources.length}
                </Descriptions.Item>
                <Descriptions.Item label="最后更新">
                  {new Date(currentMarket.last_updated).toLocaleString()}
                </Descriptions.Item>
              </Descriptions>

              <Table
                dataSource={currentMarket.sources}
                columns={sourceColumns}
                rowKey="id"
                size="small"
                scroll={{ x: 1000 }}
                pagination={false}
              />
            </div>
          )}
        </Spin>
      </Modal>

      {/* 历史记录弹窗 */}
      <Modal
        title="同步历史"
        open={historyOpen}
        onCancel={() => {
          setHistoryOpen(false)
          setHistoryData([])
        }}
        footer={[
          <Button key="close" onClick={() => setHistoryOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        <Spin spinning={historyLoading}>
          {historyData.length > 0 ? (
            <Timeline
              items={historyData.map((item) => ({
                color:
                  item.status === 'healthy'
                    ? 'green'
                    : item.status === 'degraded'
                      ? 'orange'
                      : item.status === 'unhealthy'
                        ? 'red'
                        : 'gray',
                children: (
                  <div>
                    <Text strong>
                      {new Date(item.timestamp).toLocaleString()}
                    </Text>
                    <div>
                      <StatusTag status={item.status} />
                      {item.latency_ms != null && (
                        <Text style={{ marginLeft: 8 }}>
                          延迟: {item.latency_ms}ms
                        </Text>
                      )}
                    </div>
                    {item.error_message && (
                      <Text type="danger">{item.error_message}</Text>
                    )}
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty
              description="暂无历史记录"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Spin>
      </Modal>
    </div>
  )
}
