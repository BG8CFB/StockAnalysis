import { Table, Tag, Button, Space, Popconfirm } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { globalMessage } from '@/services/http/message-ref'
import {
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import type { Alert } from '@/services/api/admin-trading-agents'
import { resolveAlert } from '@/services/api/admin-trading-agents'
import { useState, useCallback } from 'react'

interface AlertsTableProps {
  alerts: Alert[]
  loading?: boolean
  onResolved?: () => void
}

const LEVEL_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  info: { color: 'blue', icon: <InfoCircleOutlined /> },
  warning: { color: 'orange', icon: <WarningOutlined /> },
  error: { color: 'red', icon: <CloseCircleOutlined /> },
  critical: { color: 'purple', icon: <CloseCircleOutlined /> },
}

export default function AlertsTable({ alerts, loading = false, onResolved }: AlertsTableProps) {
  const [resolving, setResolving] = useState<Set<string>>(new Set())

  const handleResolve = useCallback(async (id: string) => {
    setResolving((prev) => new Set(prev).add(id))
    try {
      await resolveAlert(id)
      globalMessage?.success('告警已解决')
      onResolved?.()
    } catch {
      globalMessage?.error('解决失败')
    } finally {
      setResolving((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }, [onResolved])

  const columns: ColumnsType<Alert> = [
    {
      title: '级别',
      dataIndex: 'level',
      width: 100,
      render: (level: string) => {
        const config = LEVEL_CONFIG[level] ?? LEVEL_CONFIG.info
        return (
          <Tag color={config.color} icon={config.icon}>
            {level === 'critical' ? '严重' : level === 'error' ? '错误' : level === 'warning' ? '警告' : '信息'}
          </Tag>
        )
      },
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
    },
    {
      title: '消息',
      dataIndex: 'message',
      ellipsis: true,
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'resolved',
      width: 100,
      render: (resolved: boolean) =>
        resolved ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>已解决</Tag>
        ) : (
          <Tag color="default">未解决</Tag>
        ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => new Date(t).toLocaleString(),
    },
    {
      title: '操作',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {!record.resolved && (
            <Popconfirm
              title="确认解决此告警？"
              onConfirm={() => handleResolve(record.id)}
            >
              <Button
                size="small"
                type="primary"
                loading={resolving.has(record.id)}
              >
                解决
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Table
      dataSource={alerts}
      columns={columns}
      rowKey="id"
      loading={loading}
      size="small"
      pagination={{ pageSize: 20 }}
      scroll={{ x: 900 }}
      locale={{ emptyText: '暂无告警' }}
    />
  )
}
