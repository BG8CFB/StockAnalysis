/**
 * 智能体管理页面
 * 功能：我的智能体（查看/编辑/启用/禁用/删除/重置/导入/导出）+ 公共配置模板（管理员）
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Card, Button, Space, Typography, Table, Tag, Switch, Modal, Form,
  Input, Select, Popconfirm, Spin, Empty, Descriptions, Alert,
  Segmented, Collapse, Tooltip,
} from 'antd'
import { globalMessage } from '@/services/http/message-ref'
import {
  ReloadOutlined, PlusOutlined, EditOutlined, DeleteOutlined,
  RobotOutlined, EyeOutlined, UndoOutlined, DownloadOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useAuthStore } from '@/stores/auth.store'
import {
  listAgents, saveAgent, deleteAgent,
  resetAgentConfig, exportAgentConfig, importAgentConfig,
  getPublicAgentConfig, updatePublicAgentConfig, restorePublicAgentConfig,
  type AgentItem, type AgentConfig, type AgentConfigResponse, type AgentConfigUpdateRequest,
} from '@/services/api/agents'

const { Title, Text } = Typography

// ==================== 常量 ====================

/** 阶段中文映射（flat agents 用） */
const STAGE_LABELS: Record<string, string> = {
  analysis: '分析阶段',
  research: '研究阶段',
  risk: '风险阶段',
  trading: '交易阶段',
}

/** 阶段颜色 */
const STAGE_COLORS: Record<string, string> = {
  analysis: 'blue',
  research: 'purple',
  risk: 'orange',
  trading: 'gold',
}

/** 公共配置阶段标签 */
const PHASE_LABELS: Record<string, string> = {
  phase1: '分析阶段 (Phase 1)',
  phase2: '研究阶段 (Phase 2)',
  phase3: '风险阶段 (Phase 3)',
  phase4: '交易阶段 (Phase 4)',
}

const PHASE_KEYS = ['phase1', 'phase2', 'phase3', 'phase4']

// ==================== 组件 ====================

export default function AgentManagementPage() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN'

  // 视图切换（仅管理员）
  const [activeView, setActiveView] = useState<'my' | 'public'>('my')

  // ===== 我的智能体状态 =====
  const [agents, setAgents] = useState<AgentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [editingAgent, setEditingAgent] = useState<AgentItem | null>(null)
  const [viewingAgent, setViewingAgent] = useState<AgentItem | null>(null)
  const [saving, setSaving] = useState(false)
  const importInputRef = useRef<HTMLInputElement>(null)

  // ===== 公共配置状态 =====
  const [publicConfig, setPublicConfig] = useState<AgentConfigResponse | null>(null)
  const [publicLoading, setPublicLoading] = useState(false)
  const [publicEditOpen, setPublicEditOpen] = useState(false)
  const [editingPublicAgent, setEditingPublicAgent] = useState<{
    phase: string
    agentIndex: number
  } | null>(null)
  const [publicSaving, setPublicSaving] = useState(false)

  // ========== 我的智能体：数据加载 ==========

  const fetchAgents = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listAgents()
      setAgents(Array.isArray(res) ? res : [])
    } catch {
      globalMessage?.error('加载智能体列表失败')
      setAgents([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeView === 'my') fetchAgents()
  }, [activeView, fetchAgents])

  // ========== 公共配置：数据加载 ==========

  const fetchPublicConfig = useCallback(async () => {
    setPublicLoading(true)
    try {
      const config = await getPublicAgentConfig(true)
      setPublicConfig(config)
    } catch {
      globalMessage?.error('加载公共配置失败')
    } finally {
      setPublicLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeView === 'public' && isAdmin) fetchPublicConfig()
  }, [activeView, isAdmin, fetchPublicConfig])

  // ========== 我的智能体：CRUD 操作 ==========

  const handleEdit = (agent: AgentItem) => {
    setEditingAgent(agent)
    setEditOpen(true)
  }

  const handleAdd = () => {
    setEditingAgent(null)
    setEditOpen(true)
  }

  const handleViewDetail = (agent: AgentItem) => {
    setViewingAgent(agent)
    setDetailOpen(true)
  }

  const handleSave = async (values: Partial<AgentItem>) => {
    setSaving(true)
    try {
      if (editingAgent) {
        await saveAgent({ ...editingAgent, ...values })
        globalMessage?.success('智能体配置已更新')
      } else {
        await saveAgent({
          id: `custom_${Date.now()}`,
          name: values.name || '新智能体',
          stage: values.stage || 'analysis',
          type: values.type || 'custom',
          description: values.description || '',
          prompt: values.prompt || '',
          enabled: true,
        })
        globalMessage?.success('智能体已创建')
      }
      setEditOpen(false)
      await fetchAgents()
    } catch {
      globalMessage?.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (agentId: string) => {
    try {
      const res = await deleteAgent(agentId)
      globalMessage?.success(res.message || '删除成功')
      await fetchAgents()
    } catch {
      globalMessage?.error('删除失败')
    }
  }

  const handleToggleEnabled = async (agent: AgentItem, enabled: boolean) => {
    try {
      await saveAgent({ ...agent, enabled })
      globalMessage?.success(`${enabled ? '启用' : '禁用'}成功`)
      await fetchAgents()
    } catch {
      globalMessage?.error('操作失败')
    }
  }

  // ========== 我的智能体：配置重置/导入/导出 ==========

  const handleResetConfig = async () => {
    setSaving(true)
    try {
      await resetAgentConfig()
      globalMessage?.success('已重置为公共默认配置')
      await fetchAgents()
    } catch {
      globalMessage?.error('重置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleExportConfig = async () => {
    try {
      const res = await exportAgentConfig()
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agent-config-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
      globalMessage?.success('配置已导出')
    } catch {
      globalMessage?.error('导出失败')
    }
  }

  const handleImportConfig = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      await importAgentConfig(data)
      globalMessage?.success('配置已导入')
      await fetchAgents()
    } catch {
      globalMessage?.error('导入失败，请检查文件格式')
    }
    // 重置 input 以支持重复选择同一文件
    if (importInputRef.current) importInputRef.current.value = ''
  }

  // ========== 公共配置：操作 ==========

  const handlePublicEdit = (phase: string, agentIndex: number) => {
    setEditingPublicAgent({ phase, agentIndex })
    setPublicEditOpen(true)
  }

  const handlePublicSave = async (values: {
    name: string
    role_definition: string
    when_to_use: string
    enabled: boolean
  }) => {
    if (!publicConfig || !editingPublicAgent) return
    setPublicSaving(true)
    try {
      const { phase, agentIndex } = editingPublicAgent
      const phaseData = (publicConfig as unknown as Record<string, { agents: AgentConfig[] }>)[phase]
      if (!phaseData) return

      const updatedAgents = phaseData.agents.map((a, i) =>
        i === agentIndex ? { ...a, ...values } : a,
      )
      const payload: AgentConfigUpdateRequest = { [phase]: { ...phaseData, agents: updatedAgents } }
      await updatePublicAgentConfig(payload)
      globalMessage?.success('公共配置已更新')
      setPublicEditOpen(false)
      await fetchPublicConfig()
    } catch {
      globalMessage?.error('更新公共配置失败')
    } finally {
      setPublicSaving(false)
    }
  }

  const handlePublicToggleEnabled = async (phase: string, agentIndex: number, enabled: boolean) => {
    if (!publicConfig) return
    const phaseData = (publicConfig as unknown as Record<string, { agents: AgentConfig[] }>)[phase]
    if (!phaseData) return

    const updatedAgents = phaseData.agents.map((a, i) =>
      i === agentIndex ? { ...a, enabled } : a,
    )
    try {
      const payload: AgentConfigUpdateRequest = { [phase]: { ...phaseData, agents: updatedAgents } }
      await updatePublicAgentConfig(payload)
      globalMessage?.success(`${enabled ? '启用' : '禁用'}成功`)
      await fetchPublicConfig()
    } catch {
      globalMessage?.error('操作失败')
    }
  }

  const handleRestoreDefaults = async () => {
    setPublicSaving(true)
    try {
      await restorePublicAgentConfig()
      globalMessage?.success('公共配置已恢复为 YAML 默认值')
      await fetchPublicConfig()
    } catch {
      globalMessage?.error('恢复默认配置失败')
    } finally {
      setPublicSaving(false)
    }
  }

  // ========== 我的智能体：表格列 ==========

  const columns: ColumnsType<AgentItem> = [
    {
      title: '名称',
      dataIndex: 'name',
      width: 160,
      render: (text, record) => (
        <Space>
          <RobotOutlined style={{ color: '#C9A96E' }} />
          <Text strong>{text}</Text>
          {record.is_system && <Tag color="processing">系统</Tag>}
        </Space>
      ),
    },
    {
      title: '阶段',
      dataIndex: 'stage',
      width: 100,
      render: (stage: string) => (
        <Tag color={STAGE_COLORS[stage] ?? 'default'}>{STAGE_LABELS[stage] || stage}</Tag>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      width: 100,
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      render: (desc: string) => desc || <Text type="secondary">-</Text>,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 80,
      render: (enabled: boolean, record) => (
        <Switch
          size="small"
          checked={enabled}
          onChange={(checked) => handleToggleEnabled(record, checked)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '操作',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)} />
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          {!record.is_system && (
            <Popconfirm
              title={`确定要删除「${record.name}」吗？`}
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  // ========== 公共配置：表格列 ==========

  const getPublicColumns = (phase: string): ColumnsType<AgentConfig> => [
    {
      title: '名称',
      dataIndex: 'name',
      width: 180,
      render: (text, record) => (
        <Space>
          <RobotOutlined style={{ color: '#C9A96E' }} />
          <Text strong>{text}</Text>
          <Tag color="processing">{record.slug}</Tag>
        </Space>
      ),
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 80,
      render: (enabled: boolean, _, index) => (
        <Switch
          size="small"
          checked={enabled}
          onChange={(checked) => handlePublicToggleEnabled(phase, index, checked)}
        />
      ),
    },
    {
      title: '提示词',
      dataIndex: 'role_definition',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: 500 }}>
          <Text type="secondary" ellipsis style={{ maxWidth: 300, display: 'inline-block' }}>
            {text ? text.slice(0, 80) + (text.length > 80 ? '...' : '') : '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      width: 80,
      render: (_, __, index) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => handlePublicEdit(phase, index)} />
      ),
    },
  ]

  // ========== 渲染 ==========

  /** 获取当前编辑的公共智能体 */
  const currentEditingPublicAgent = (() => {
    if (!publicConfig || !editingPublicAgent) return null
    const phaseData = (publicConfig as unknown as Record<string, { agents: AgentConfig[] }>)[
      editingPublicAgent.phase
    ]
    return phaseData?.agents[editingPublicAgent.agentIndex] ?? null
  })()

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>
          <RobotOutlined style={{ marginRight: 8 }} />
          智能体管理
        </Title>
      </div>

      {/* 管理员视图切换 */}
      {isAdmin && (
        <Segmented
          options={[
            { value: 'my', label: '我的智能体' },
            { value: 'public', label: '公共配置模板' },
          ]}
          value={activeView}
          onChange={(v) => setActiveView(v as 'my' | 'public')}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* ===== 我的智能体视图 ===== */}
      {activeView === 'my' && (
        <>
          {/* 提示信息 */}
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            description={
              <span>
                系统内置了研究阶段（Bull/Bear Researcher + Research Manager）、风险阶段（Risk Manager）和交易阶段（Trader）共
                5 个智能体。您可以编辑参数或添加自定义智能体。支持重置为公共默认配置、导入导出配置。
              </span>
            }
          />

          {/* 操作栏 */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <Space>
              <Popconfirm
                title="重置后个人自定义配置将丢失，确定吗？"
                onConfirm={handleResetConfig}
                okText="确定"
                cancelText="取消"
              >
                <Button icon={<UndoOutlined />} loading={saving}>
                  重置为默认
                </Button>
              </Popconfirm>
              <Button icon={<DownloadOutlined />} onClick={handleExportConfig}>
                导出配置
              </Button>
              <Button icon={<UploadOutlined />} onClick={() => importInputRef.current?.click()}>
                导入配置
              </Button>
              <input
                ref={importInputRef}
                type="file"
                accept=".json"
                style={{ display: 'none' }}
                onChange={handleImportConfig}
              />
              <Button icon={<ReloadOutlined />} onClick={fetchAgents} loading={loading}>
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                添加智能体
              </Button>
            </Space>
          </div>

          {/* 智能体列表 */}
          <Card>
            <Spin spinning={loading}>
              {agents.length === 0 && !loading ? (
                <Empty description="暂无智能体配置" />
              ) : (
                <Table
                  dataSource={agents}
                  columns={columns}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  scroll={{ x: 900 }}
                />
              )}
            </Spin>
          </Card>
        </>
      )}

      {/* ===== 公共配置模板视图（仅管理员） ===== */}
      {activeView === 'public' && isAdmin && (
        <>
          {/* 提示信息 */}
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            description="公共配置模板是所有未自定义配置的用户使用的默认智能体配置。修改此配置将影响所有未自定义的用户。"
          />

          {/* 操作栏 */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <Space>
              <Popconfirm
                title="恢复后公共配置将回到 YAML 默认值，确定吗？"
                onConfirm={handleRestoreDefaults}
                okText="确定"
                cancelText="取消"
              >
                <Button icon={<UndoOutlined />} loading={publicSaving}>
                  恢复 YAML 默认值
                </Button>
              </Popconfirm>
              <Button icon={<ReloadOutlined />} onClick={fetchPublicConfig} loading={publicLoading}>
                刷新
              </Button>
            </Space>
          </div>

          {/* 四阶段配置面板 */}
          <Card>
            <Spin spinning={publicLoading}>
              {publicConfig ? (
                <Collapse
                  defaultActiveKey={PHASE_KEYS}
                  items={PHASE_KEYS.map((phase) => {
                    const phaseData = (publicConfig as unknown as Record<string, { agents: AgentConfig[] }>)[phase]
                    const agents = phaseData?.agents ?? []
                    return {
                      key: phase,
                      label: (
                        <Space>
                          <Tag color={STAGE_COLORS[PHASE_KEYS.indexOf(phase) < 2 ? ['analysis', 'research'][PHASE_KEYS.indexOf(phase)] : ['risk', 'trading'][PHASE_KEYS.indexOf(phase) - 2]]}>
                            {PHASE_LABELS[phase]}
                          </Tag>
                          <Text type="secondary">{agents.length} 个智能体</Text>
                        </Space>
                      ),
                      children: (
                        <Table
                          dataSource={agents}
                          columns={getPublicColumns(phase)}
                          rowKey="slug"
                          pagination={false}
                          size="small"
                        />
                      ),
                    }
                  })}
                />
              ) : (
                <Empty description="暂无公共配置" />
              )}
            </Spin>
          </Card>
        </>
      )}

      {/* ===== 我的智能体：编辑/新增对话框 ===== */}
      <Modal
        title={editingAgent ? `编辑智能体：${editingAgent.name}` : '添加智能体'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        destroyOnHidden
        footer={null}
        width={600}
      >
        <Form
          layout="vertical"
          initialValues={editingAgent ?? { stage: 'analysis', type: 'custom', enabled: true }}
          onFinish={handleSave}
        >
          {!editingAgent && (
            <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
              <Input placeholder="输入智能体名称" />
            </Form.Item>
          )}
          {editingAgent && (
            <Form.Item label="ID">
              <Input value={editingAgent.id} disabled />
            </Form.Item>
          )}
          <Space style={{ width: '100%' }} wrap>
            <Form.Item name="stage" label="所属阶段" style={{ flex: 1, minWidth: 150 }}
              rules={[{ required: true }]}>
              <Select options={[
                { value: 'analysis', label: '分析阶段' },
                { value: 'research', label: '研究阶段' },
                { value: 'risk', label: '风险阶段' },
                { value: 'trading', label: '交易阶段' },
              ]} />
            </Form.Item>
            <Form.Item name="type" label="类型" style={{ flex: 1, minWidth: 150 }}>
              <Input placeholder="如 market, social, custom" />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="智能体的功能描述" />
          </Form.Item>
          <Form.Item name="prompt" label="Prompt 模板">
            <Input.TextArea rows={4} placeholder="智能体的角色定义和指令模板" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setEditOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={saving}>保存</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* ===== 我的智能体：详情对话框 ===== */}
      <Modal
        title={`智能体详情：${viewingAgent?.name ?? ''}`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailOpen(false)}>
            关闭
          </Button>,
          <Button
            key="edit"
            type="primary"
            icon={<EditOutlined />}
            onClick={() => {
              setDetailOpen(false)
              if (viewingAgent) handleEdit(viewingAgent)
            }}
          >
            编辑
          </Button>,
        ]}
        width={650}
      >
        {viewingAgent && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{viewingAgent.id}</Descriptions.Item>
            <Descriptions.Item label="名称">{viewingAgent.name}</Descriptions.Item>
            <Descriptions.Item label="阶段">
              <Tag color={STAGE_COLORS[viewingAgent.stage] ?? 'default'}>
                {STAGE_LABELS[viewingAgent.stage] || viewingAgent.stage}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag>{viewingAgent.type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="是否系统">
              {viewingAgent.is_system ? <Tag color="processing">是</Tag> : <Tag>否</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="启用状态">
              <Tag color={viewingAgent.enabled ? 'success' : 'default'}>
                {viewingAgent.enabled ? '已启用' : '已禁用'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              {viewingAgent.description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Prompt">
              {viewingAgent.prompt ? (
                <pre style={{
                  margin: 0, padding: 8, background: '#f5f5f5', borderRadius: 4,
                  fontSize: 12, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto',
                }}>
                  {viewingAgent.prompt}
                </pre>
              ) : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* ===== 公共配置：编辑对话框 ===== */}
      <Modal
        title={`编辑公共智能体：${currentEditingPublicAgent?.name ?? ''}`}
        open={publicEditOpen}
        onCancel={() => setPublicEditOpen(false)}
        destroyOnHidden
        footer={null}
        width={650}
      >
        {currentEditingPublicAgent && (
          <Form
            layout="vertical"
            initialValues={{
              name: currentEditingPublicAgent.name,
              role_definition: currentEditingPublicAgent.role_definition,
              when_to_use: currentEditingPublicAgent.when_to_use ?? '',
              enabled: currentEditingPublicAgent.enabled,
            }}
            onFinish={handlePublicSave}
          >
            <Form.Item label="Slug">
              <Input value={currentEditingPublicAgent.slug} disabled />
            </Form.Item>
            <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
              <Input placeholder="智能体名称" />
            </Form.Item>
            <Form.Item name="when_to_use" label="使用场景">
              <Input.TextArea rows={2} placeholder="描述该智能体的使用场景" />
            </Form.Item>
            <Form.Item name="role_definition" label="角色定义 (Prompt)" rules={[{ required: true }]}>
              <Input.TextArea rows={6} placeholder="智能体的角色定义和指令" />
            </Form.Item>
            <Form.Item name="enabled" label="启用" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
            <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
              <Space>
                <Button onClick={() => setPublicEditOpen(false)}>取消</Button>
                <Button type="primary" htmlType="submit" loading={publicSaving}>保存</Button>
              </Space>
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  )
}
