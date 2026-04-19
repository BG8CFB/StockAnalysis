/**
 * 管理员用户管理页面
 * 功能：用户列表、审批、角色管理、审计日志
 */

import { useState, useEffect, useRef } from 'react'
import {
  Card, Button, Space, Typography, Modal, Form, Input, Select,
  Tabs, Empty, Table, Tag,
} from 'antd'
import {
  TeamOutlined, ReloadOutlined, UserAddOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useUserManagement } from '@/features/admin/hooks/useUserManagement'
import UserTable from '@/features/admin/components/UserTable'
import UserApprovalDialog from '@/features/admin/components/UserApprovalDialog'
import { useAuthStore } from '@/stores/auth.store'
import type { AdminUser, UserRole } from '@/types/admin.types'
import type { AuditLogItem } from '@/types/admin.types'

const { Title, Text } = Typography

/** 角色选项 */
const ROLE_OPTIONS = [
  { value: 'GUEST', label: '访客' },
  { value: 'USER', label: '用户' },
  { value: 'ADMIN', label: '管理员' },
  { value: 'SUPER_ADMIN', label: '超级管理员' },
]

export default function UserManagementPage() {
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN'

  const um = useUserManagement()
  const [approvalOpen, setApprovalOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [resetPwdOpen, setResetPwdOpen] = useState(false)
  const [currentUser, setCurrentUser] = useState<AdminUser | null>(null)
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()
  const [resetPwdForm] = Form.useForm()
  const [activeTab, setActiveTab] = useState('users')
  const [auditPage, setAuditPage] = useState(1)
  const [auditPageSize, setAuditPageSize] = useState(20)

  const initializedRef = useRef(false)

  useEffect(() => {
    if (!isAdmin) return
    if (initializedRef.current) return
    initializedRef.current = true
    um.fetchUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin])

  // 标签页切换时加载对应数据
  useEffect(() => {
    if (!isAdmin) return
    if (activeTab === 'pending') {
      um.fetchPendingUsers()
    } else if (activeTab === 'audit') {
      um.fetchAuditLogs({ page: auditPage, page_size: auditPageSize })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isAdmin])

  /** 分页变化 */
  const handlePageChange = (p: number, ps?: number) => {
    const newPs = ps ?? um.pageSize
    um.fetchUsers({ page: p, page_size: newPs })
  }

  /** 创建用户 */
  const handleCreate = async (values: {
    username: string
    email: string
    password: string
    role?: UserRole
  }) => {
    const success = await um.create({
      username: values.username,
      email: values.email,
      password: values.password,
      role: values.role,
    })
    if (success) {
      setCreateOpen(false)
      createForm.resetFields()
    }
  }

  /** 编辑用户 */
  const handleEdit = (userItem: AdminUser) => {
    setCurrentUser(userItem)
    editForm.setFieldsValue({
      username: userItem.username,
      email: userItem.email,
      is_active: userItem.is_active,
    })
    setEditOpen(true)
  }

  const handleSaveEdit = async (values: {
    username?: string
    email?: string
    is_active?: boolean
  }) => {
    if (!currentUser) return
    const success = await um.update(currentUser.id, values)
    if (success) {
      setEditOpen(false)
      setCurrentUser(null)
    }
  }

  /** 重置密码 */
  const handleResetPassword = (userItem: AdminUser) => {
    setCurrentUser(userItem)
    resetPwdForm.resetFields()
    setResetPwdOpen(true)
  }

  const handleConfirmReset = async (values: { new_password: string }) => {
    if (!currentUser) return
    await um.resetPassword(currentUser.id, values.new_password)
    setResetPwdOpen(false)
    setCurrentUser(null)
    resetPwdForm.resetFields()
  }

  /** 审计日志分页 */
  const handleAuditPageChange = (p: number, ps?: number) => {
    setAuditPage(p)
    if (ps) setAuditPageSize(ps)
    um.fetchAuditLogs({ page: p, page_size: ps ?? auditPageSize })
  }

  // 非管理员无权访问
  if (!isAdmin) {
    return (
      <div style={{ padding: '0 0 24px' }}>
        <Empty
          description={
            <>
              <Text strong>权限不足</Text>
              <br />
              <Text type="secondary">您需要管理员权限才能访问此页面</Text>
            </>
          }
        />
      </div>
    )
  }

  const auditColumns: ColumnsType<AuditLogItem> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => (
        <Text style={{ fontSize: 12 }}>{new Date(t).toLocaleString()}</Text>
      ),
    },
    {
      title: '用户',
      dataIndex: 'username',
      width: 100,
      render: (text: string | undefined) => text || '-',
    },
    {
      title: '操作',
      dataIndex: 'action',
      width: 120,
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      width: 100,
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      width: 130,
      render: (text: string | undefined) => text || '-',
    },
    {
      title: '详情',
      dataIndex: 'details',
      ellipsis: true,
      render: (details: Record<string, unknown> | undefined) =>
        details ? JSON.stringify(details) : '-',
    },
  ]

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* 页面标题 */}
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
              <TeamOutlined style={{ marginRight: 8 }} />
              用户管理
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              管理系统用户、审批申请、查看审计日志
            </Text>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => um.fetchUsers()}
              loading={um.loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<UserAddOutlined />}
              onClick={() => setCreateOpen(true)}
            >
              创建用户
            </Button>
          </Space>
        </div>
      </Card>

      {/* 标签页内容 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'users',
            label: '用户列表',
            children: (
              <Card size="small">
                <UserTable
                  users={um.users}
                  total={um.total}
                  page={um.page}
                  pageSize={um.pageSize}
                  loading={um.loading}
                  actionLoading={um.actionLoading}
                  onPageChange={handlePageChange}
                  onDisable={um.disable}
                  onEnable={um.enable}
                  onDelete={um.remove}
                  onEdit={handleEdit}
                  onChangeRole={um.changeRole}
                  onResetPassword={handleResetPassword}
                />
              </Card>
            ),
          },
          {
            key: 'pending',
            label: (
              <Space>
                待审批
                {um.pendingUsers.length > 0 && (
                  <Tag color="red">{um.pendingUsers.length}</Tag>
                )}
              </Space>
            ),
            children: (
              <Card size="small">
                <UserTable
                  users={um.pendingUsers}
                  total={um.pendingUsers.length}
                  page={1}
                  pageSize={um.pendingUsers.length}
                  loading={um.loading}
                  actionLoading={um.actionLoading}
                  onPageChange={() => {}}
                  onDisable={um.disable}
                  onEnable={um.enable}
                  onDelete={um.remove}
                  onEdit={handleEdit}
                  onChangeRole={um.changeRole}
                  onResetPassword={handleResetPassword}
                />
              </Card>
            ),
          },
          {
            key: 'audit',
            label: '审计日志',
            children: (
              <Card size="small">
                <Table
                  dataSource={um.auditLogs}
                  columns={auditColumns}
                  rowKey="id"
                  loading={um.loading}
                  size="small"
                  scroll={{ x: 900 }}
                  pagination={{
                    current: auditPage,
                    pageSize: auditPageSize,
                    total: um.auditTotal,
                    showTotal: (t) => `共 ${t} 条`,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    onChange: handleAuditPageChange,
                  }}
                  locale={{
                    emptyText: (
                      <Empty
                        description="暂无审计日志"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                      />
                    ),
                  }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* 审批对话框 */}
      <UserApprovalDialog
        open={approvalOpen}
        onClose={() => setApprovalOpen(false)}
        pendingUsers={um.pendingUsers}
        loading={um.loading}
        actionLoading={um.actionLoading}
        onApprove={um.approve}
        onReject={um.reject}
        onRefresh={um.fetchPendingUsers}
      />

      {/* 创建用户对话框 */}
      <Modal
        title="创建用户"
        open={createOpen}
        onCancel={() => {
          setCreateOpen(false)
          createForm.resetFields()
        }}
        onOk={() => createForm.submit()}
        destroyOnHidden
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
            ]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="USER">
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑用户对话框 */}
      <Modal
        title="编辑用户"
        open={editOpen}
        onCancel={() => {
          setEditOpen(false)
          setCurrentUser(null)
        }}
        onOk={() => editForm.submit()}
        destroyOnHidden
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleSaveEdit}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="is_active"
            label="状态"
            valuePropName="checked"
          >
            <Select
              options={[
                { value: true, label: '启用' },
                { value: false, label: '禁用' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码对话框 */}
      <Modal
        title={`重置密码 - ${currentUser?.username ?? ''}`}
        open={resetPwdOpen}
        onCancel={() => {
          setResetPwdOpen(false)
          setCurrentUser(null)
          resetPwdForm.resetFields()
        }}
        onOk={() => resetPwdForm.submit()}
        destroyOnHidden
      >
        <Form
          form={resetPwdForm}
          layout="vertical"
          onFinish={handleConfirmReset}
        >
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
