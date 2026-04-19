/**
 * 管理员 - TradingAgents 管理页面
 * 功能：AI 模型管理、任务监控、报告统计、告警处理
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Card, Tabs, Table, Button, Space, Typography, Tag, Popconfirm,
  message, Modal, Form, Input, InputNumber, Row, Col, Statistic, Spin,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  RobotOutlined, FileTextOutlined,
  WarningOutlined, ReloadOutlined, DeleteOutlined, PlusOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import PieChart from '@/components/charts/PieChart'
import BarChart from '@/components/charts/BarChart'
import TaskStatsCard from '@/features/admin/components/TaskStatsCard'
import AlertsTable from '@/features/admin/components/AlertsTable'
import {
  getModels, createModel, deleteModel,
  getTasks, getTaskStats, deleteTask,
  getReports, getReportStats,
  getAlerts, getAlertStats,
  type AIModel, type Task, type Report, type Alert,
  type TaskStats, type ReportStats, type AlertStats,
} from '@/services/api/admin-trading-agents'

const { Title, Paragraph } = Typography

type TabKey = 'overview' | 'tasks' | 'models' | 'reports' | 'alerts'

export default function TradingAgentsAdminPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')

  // Overview stats
  const [taskStats, setTaskStats] = useState<TaskStats | null>(null)
  const [reportStats, setReportStats] = useState<ReportStats | null>(null)
  const [alertStats, setAlertStats] = useState<AlertStats | null>(null)
  const [overviewLoading, setOverviewLoading] = useState(false)

  // Tasks
  const [tasks, setTasks] = useState<Task[]>([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [taskPagination, setTaskPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  // Models
  const [models, setModels] = useState<AIModel[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelModalOpen, setModelModalOpen] = useState(false)
  const [modelForm] = Form.useForm()
  const [creatingModel, setCreatingModel] = useState(false)

  // Reports
  const [reports, setReports] = useState<Report[]>([])
  const [reportsLoading, setReportsLoading] = useState(false)
  const [reportPagination, setReportPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  // Alerts
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [alertsLoading, setAlertsLoading] = useState(false)

  // ========== Loaders ==========

  const loadOverview = useCallback(async () => {
    setOverviewLoading(true)
    try {
      const [ts, rs, as] = await Promise.all([
        getTaskStats().catch(() => null),
        getReportStats().catch(() => null),
        getAlertStats().catch(() => null),
      ])
      if (ts?.data) setTaskStats(ts.data as TaskStats)
      if (rs?.data) setReportStats(rs.data as ReportStats)
      if (as?.data) setAlertStats(as.data as AlertStats)
    } finally {
      setOverviewLoading(false)
    }
  }, [])

  const loadTasks = useCallback(async (page = 1, pageSize = 20) => {
    setTasksLoading(true)
    try {
      const res = await getTasks({ page, page_size: pageSize })
      const data = res.data as { items: Task[]; total: number } | undefined
      setTasks(data?.items ?? [])
      setTaskPagination({ current: page, pageSize, total: data?.total ?? 0 })
    } catch {
      message.error('加载任务失败')
    } finally {
      setTasksLoading(false)
    }
  }, [])

  const loadModels = useCallback(async () => {
    setModelsLoading(true)
    try {
      const res = await getModels()
      setModels((res.data as AIModel[] | undefined) ?? [])
    } catch {
      message.error('加载模型失败')
    } finally {
      setModelsLoading(false)
    }
  }, [])

  const loadReports = useCallback(async (page = 1, pageSize = 20) => {
    setReportsLoading(true)
    try {
      const res = await getReports({ page, page_size: pageSize })
      const data = res.data as { items: Report[]; total: number } | undefined
      setReports(data?.items ?? [])
      setReportPagination({ current: page, pageSize, total: data?.total ?? 0 })
    } catch {
      message.error('加载报告失败')
    } finally {
      setReportsLoading(false)
    }
  }, [])

  const loadAlerts = useCallback(async () => {
    setAlertsLoading(true)
    try {
      const res = await getAlerts()
      setAlerts((res.data as Alert[] | undefined) ?? [])
    } catch {
      message.error('加载告警失败')
    } finally {
      setAlertsLoading(false)
    }
  }, [])

  // Tab change handler
  const handleTabChange = useCallback((key: string) => {
    setActiveTab(key as TabKey)
    switch (key as TabKey) {
      case 'overview':
        loadOverview()
        break
      case 'tasks':
        loadTasks()
        break
      case 'models':
        loadModels()
        break
      case 'reports':
        loadReports()
        break
      case 'alerts':
        loadAlerts()
        break
    }
  }, [loadOverview, loadTasks, loadModels, loadReports, loadAlerts])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  // ========== Actions ==========

  const handleDeleteTask = async (id: string) => {
    try {
      await deleteTask(id)
      message.success('任务已删除')
      loadTasks(taskPagination.current, taskPagination.pageSize)
    } catch {
      message.error('删除失败')
    }
  }

  const handleDeleteModel = async (id: string) => {
    try {
      await deleteModel(id)
      message.success('模型已删除')
      loadModels()
    } catch {
      message.error('删除失败')
    }
  }

  const handleCreateModel = async () => {
    try {
      const values = await modelForm.validateFields()
      setCreatingModel(true)
      await createModel(values)
      message.success('模型创建成功')
      setModelModalOpen(false)
      modelForm.resetFields()
      loadModels()
    } catch {
      // validation or request error
    } finally {
      setCreatingModel(false)
    }
  }

  // ========== Columns ==========

  const taskColumns: ColumnsType<Task> = [
    { title: 'ID', dataIndex: 'id', width: 200, ellipsis: true },
    { title: '用户', dataIndex: 'user_id', width: 200, ellipsis: true },
    { title: '股票代码', dataIndex: 'stock_code', width: 120 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => {
        const color =
          status === 'completed' ? 'success' :
          status === 'failed' ? 'error' :
          status === 'running' ? 'processing' :
          status === 'pending' ? 'default' : 'default'
        const label =
          status === 'completed' ? '已完成' :
          status === 'failed' ? '失败' :
          status === 'running' ? '运行中' :
          status === 'pending' ? '待处理' : status
        return <Tag color={color}>{label}</Tag>
      },
    },
    { title: '进度', dataIndex: 'progress', width: 100, render: (v: number) => `${v}%` },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => new Date(t).toLocaleString(),
    },
    {
      title: '操作',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Popconfirm title="确定删除此任务？" onConfirm={() => handleDeleteTask(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  const modelColumns: ColumnsType<AIModel> = [
    { title: '名称', dataIndex: 'name', width: 180 },
    { title: '提供商', dataIndex: 'provider', width: 120 },
    { title: '模型ID', dataIndex: 'model_id', width: 180, ellipsis: true },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '最大Token', dataIndex: 'max_tokens', width: 120 },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '操作',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Popconfirm title="确定删除此模型？" onConfirm={() => handleDeleteModel(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  const reportColumns: ColumnsType<Report> = [
    { title: 'ID', dataIndex: 'id', width: 200, ellipsis: true },
    { title: '任务ID', dataIndex: 'task_id', width: 200, ellipsis: true },
    { title: '用户', dataIndex: 'user_id', width: 200, ellipsis: true },
    { title: '股票代码', dataIndex: 'stock_code', width: 120 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '分析类型', dataIndex: 'analysis_type', width: 120 },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => new Date(t).toLocaleString(),
    },
  ]

  // ========== Chart Data ==========

  const reportTypeData = reportStats?.by_type
    ? Object.entries(reportStats.by_type).map(([name, value]) => ({ name, value }))
    : []

  const reportDateData = reportStats?.by_date
    ? Object.entries(reportStats.by_date).map(([name, value]) => ({ name: name.slice(5), value })).slice(-14)
    : []

  const alertLevelData = alertStats?.by_level
    ? Object.entries(alertStats.by_level).map(([name, value]) => ({ name, value }))
    : []

  // ========== Render ==========

  return (
    <div style={{ padding: '0 0 24px' }}>
      <Title level={4} style={{ marginBottom: 8 }}>
        <RobotOutlined style={{ marginRight: 8 }} />
        TradingAgents 管理
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 20 }}>
        AI 模型、任务、报告和告警的集中管理
      </Paragraph>

      <Tabs activeKey={activeTab} onChange={handleTabChange} type="card">
        {/* ===== Overview ===== */}
        <Tabs.TabPane tab="概览" key="overview">
          <Spin spinning={overviewLoading}>
            {/* Task Stats */}
            <Card size="small" title="任务统计" style={{ marginBottom: 16 }}>
              <TaskStatsCard stats={taskStats} />
            </Card>

            {/* Report & Alert Stats */}
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col xs={24} lg={8}>
                <Card size="small" title="报告总数" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  <Statistic
                    value={reportStats?.total ?? 0}
                    prefix={<FileTextOutlined />}
                    styles={{ content: { color: 'var(--accent-blue)', fontSize: 24 } }}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card size="small" title="告警总数" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  <Statistic
                    value={alertStats?.total ?? 0}
                    prefix={<WarningOutlined />}
                    styles={{ content: { color: '#FF4D4F', fontSize: 24 } }}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card size="small" title="未解决告警" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  <Statistic
                    value={alertStats?.unresolved ?? 0}
                    prefix={<ClockCircleOutlined />}
                    styles={{ content: { color: '#D48806', fontSize: 24 } }}
                  />
                </Card>
              </Col>
            </Row>

            {/* Charts */}
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Card size="small" title="报告类型分布" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  {reportTypeData.length > 0 ? (
                    <PieChart data={reportTypeData} height={240} showLegend />
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>暂无数据</div>
                  )}
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card size="small" title="告警级别分布" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  {alertLevelData.length > 0 ? (
                    <PieChart data={alertLevelData} height={240} showLegend />
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>暂无数据</div>
                  )}
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card size="small" title="报告趋势（近14天）" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  {reportDateData.length > 0 ? (
                    <BarChart data={reportDateData} height={240} />
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>暂无数据</div>
                  )}
                </Card>
              </Col>
            </Row>
          </Spin>
        </Tabs.TabPane>

        {/* ===== Tasks ===== */}
        <Tabs.TabPane tab="任务" key="tasks">
          <Card
            size="small"
            title="任务列表"
            extra={
              <Button icon={<ReloadOutlined />} size="small" onClick={() => loadTasks(taskPagination.current, taskPagination.pageSize)}>
                刷新
              </Button>
            }
          >
            <Table
              dataSource={tasks}
              columns={taskColumns}
              rowKey="id"
              loading={tasksLoading}
              size="small"
              pagination={{
                current: taskPagination.current,
                pageSize: taskPagination.pageSize,
                total: taskPagination.total,
                showSizeChanger: true,
                onChange: (page, pageSize) => loadTasks(page, pageSize ?? 20),
              }}
              scroll={{ x: 900 }}
            />
          </Card>
        </Tabs.TabPane>

        {/* ===== Models ===== */}
        <Tabs.TabPane tab="模型" key="models">
          <Card
            size="small"
            title="AI 模型"
            extra={
              <Space>
                <Button icon={<ReloadOutlined />} size="small" onClick={loadModels}>刷新</Button>
                <Button type="primary" icon={<PlusOutlined />} size="small" onClick={() => setModelModalOpen(true)}>
                  添加模型
                </Button>
              </Space>
            }
          >
            <Table
              dataSource={models}
              columns={modelColumns}
              rowKey="id"
              loading={modelsLoading}
              size="small"
              pagination={false}
              scroll={{ x: 800 }}
              locale={{ emptyText: '暂无模型' }}
            />
          </Card>
        </Tabs.TabPane>

        {/* ===== Reports ===== */}
        <Tabs.TabPane tab="报告" key="reports">
          <Card
            size="small"
            title="报告列表"
            extra={
              <Button icon={<ReloadOutlined />} size="small" onClick={() => loadReports(reportPagination.current, reportPagination.pageSize)}>
                刷新
              </Button>
            }
          >
            <Table
              dataSource={reports}
              columns={reportColumns}
              rowKey="id"
              loading={reportsLoading}
              size="small"
              pagination={{
                current: reportPagination.current,
                pageSize: reportPagination.pageSize,
                total: reportPagination.total,
                showSizeChanger: true,
                onChange: (page, pageSize) => loadReports(page, pageSize ?? 20),
              }}
              scroll={{ x: 900 }}
            />
          </Card>
        </Tabs.TabPane>

        {/* ===== Alerts ===== */}
        <Tabs.TabPane tab="告警" key="alerts">
          <Card
            size="small"
            title="告警列表"
            extra={
              <Button icon={<ReloadOutlined />} size="small" onClick={loadAlerts}>
                刷新
              </Button>
            }
          >
            <AlertsTable alerts={alerts} loading={alertsLoading} onResolved={loadAlerts} />
          </Card>
        </Tabs.TabPane>
      </Tabs>

      {/* Create Model Modal */}
      <Modal
        title="添加 AI 模型"
        open={modelModalOpen}
        onCancel={() => { setModelModalOpen(false); modelForm.resetFields() }}
        onOk={handleCreateModel}
        confirmLoading={creatingModel}
        okText="创建"
        cancelText="取消"
      >
        <Form form={modelForm} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：GPT-4" />
          </Form.Item>
          <Form.Item name="provider" label="提供商" rules={[{ required: true, message: '请输入提供商' }]}>
            <Input placeholder="例如：OpenAI" />
          </Form.Item>
          <Form.Item name="model_id" label="模型ID" rules={[{ required: true, message: '请输入模型ID' }]}>
            <Input placeholder="例如：gpt-4" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="模型描述" />
          </Form.Item>
          <Form.Item name="max_tokens" label="最大 Token">
            <InputNumber style={{ width: '100%' }} placeholder="例如：4096" min={1} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
