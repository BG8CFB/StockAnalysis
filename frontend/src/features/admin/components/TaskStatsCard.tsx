import { Card, Row, Col, Statistic, Spin } from 'antd'
import {
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { TaskStats } from '@/services/api/admin-trading-agents'

interface TaskStatsCardProps {
  stats: TaskStats | null
  loading?: boolean
}

export default function TaskStatsCard({ stats, loading = false }: TaskStatsCardProps) {
  const items = [
    {
      title: '总任务数',
      value: stats?.total ?? 0,
      icon: <FileTextOutlined />,
      color: 'var(--accent-blue)',
    },
    {
      title: '运行中',
      value: stats?.running ?? 0,
      icon: <ThunderboltOutlined />,
      color: 'var(--accent-primary)',
    },
    {
      title: '待处理',
      value: stats?.pending ?? 0,
      icon: <ClockCircleOutlined />,
      color: '#D48806',
    },
    {
      title: '已完成',
      value: stats?.completed ?? 0,
      icon: <CheckCircleOutlined />,
      color: '#52C41A',
    },
    {
      title: '失败',
      value: stats?.failed ?? 0,
      icon: <CloseCircleOutlined />,
      color: '#FF4D4F',
    },
  ]

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        {items.map((item) => (
          <Col xs={12} sm={8} md={6} lg={4} key={item.title}>
            <Card size="small" style={{ background: 'var(--bg-card)', border: 'none' }}>
              <Statistic
                title={
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.title}</span>
                }
                value={item.value}
                prefix={item.icon}
                styles={{ content: { color: item.color, fontSize: 20 } }}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </Spin>
  )
}
