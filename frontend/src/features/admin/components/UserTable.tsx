/**
 * 用户列表表格组件
 * 展示用户数据，支持搜索、筛选、分页和操作
 */

import { useState, useMemo } from 'react'
import {
  Table, Tag, Button, Space, Input, Select, Typography, Popconfirm,
  Tooltip,
} from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined, PauseCircleOutlined,
  PlayCircleOutlined, DeleteOutlined, EditOutlined, KeyOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { AdminUser, UserRole, UserStatus } from '@/types/admin.types'

const { Text } = Typography

interface UserTableProps {
  users: AdminUser[]
  total: number
  page: number
  pageSize: number
  loading: boolean
  actionLoading: Record<string, boolean>
  onPageChange: (page: number, pageSize?: number) => void
  onDisable: (userId: string) => void
  onEnable: (userId: string) => void
  onDelete: (userId: string) => void
  onEdit: (user: AdminUser) => void
  onChangeRole: (userId: string, role: string) => void
  onResetPassword: (user: AdminUser) => void
}

const ROLE_OPTIONS: { value: UserRole; label: string; color: string }[] = [
  { value: 'GUEST', label: '访客', color: 'default' },
  { value: 'USER', label: '用户', color: 'blue' },
  { value: 'ADMIN', label: '管理员', color: 'purple' },
  { value: 'SUPER_ADMIN', label: '超级管理员', color: 'red' },
]

function getStatusTag(status: UserStatus, isActive: boolean) {
  if (!isActive) {
    return <Tag color="red">已禁用</Tag>
  }
  switch (status) {
    case 'active':
      return <Tag color="success" icon={<CheckCircleOutlined />}>正常</Tag>
    case 'pending':
      return <Tag color="orange">待审批</Tag>
    case 'rejected':
      return <Tag color="red" icon={<CloseCircleOutlined />}>已拒绝</Tag>
    case 'disabled':
      return <Tag color="red" icon={<PauseCircleOutlined />}>已禁用</Tag>
    default:
      return <Tag>{status}</Tag>
  }
}

export default function UserTable({
  users,
  total,
  page,
  pageSize,
  loading,
  actionLoading,
  onPageChange,
  onDisable,
  onEnable,
  onDelete,
  onEdit,
  onChangeRole,
  onResetPassword,
}: UserTableProps) {
  const [keyword, setKeyword] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('')
  const [statusFilter, setStatusFilter] = useState<UserStatus | ''>('')

  const filteredUsers = useMemo(() => {
    let result = [...users]

    if (keyword.trim()) {
      const kw = keyword.toLowerCase()
      result = result.filter(
        (u) =>
          u.username.toLowerCase().includes(kw) ||
          u.email.toLowerCase().includes(kw) ||
          u.id.toLowerCase().includes(kw)
      )
    }

    if (roleFilter) {
      result = result.filter((u) => u.role === roleFilter)
    }

    if (statusFilter) {
      result = result.filter((u) => u.status === statusFilter)
    }

    return result
  }, [users, keyword, roleFilter, statusFilter])

  const columns: ColumnsType<AdminUser> = [
    {
      title: '用户名',
      dataIndex: 'username',
      width: 120,
      render: (text: string, record: AdminUser) => (
        <Space>
          <Text strong>{text}</Text>
          {record.is_verified && (
            <Tooltip title="已验证">
              <CheckCircleOutlined style={{ color: '#52C41A' }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      width: 180,
      render: (text: string) => text || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      width: 110,
      render: (role: UserRole, record: AdminUser) => {
        return (
          <Select
            size="small"
            value={role}
            onChange={(value) => onChangeRole(record.id, value)}
            style={{ width: 100 }}
            options={ROLE_OPTIONS.map((r) => ({
              value: r.value,
              label: r.label,
            }))}
          />
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: UserStatus, record: AdminUser) =>
        getStatusTag(status, record.is_active),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => (
        <Text style={{ fontSize: 12 }}>{new Date(t).toLocaleString()}</Text>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      width: 170,
      render: (t: string | undefined) =>
        t ? (
          <Text style={{ fontSize: 12 }}>{new Date(t).toLocaleString()}</Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>从未登录</Text>
        ),
    },
    {
      title: '操作',
      width: 260,
      fixed: 'right',
      render: (_, record) => (
        <Space size={2}>
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
            />
          </Tooltip>
          <Tooltip title="重置密码">
            <Button
              size="small"
              icon={<KeyOutlined />}
              onClick={() => onResetPassword(record)}
            />
          </Tooltip>
          {record.is_active ? (
            <Popconfirm
              title="确定要禁用该用户吗？"
              onConfirm={() => onDisable(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                size="small"
                icon={<PauseCircleOutlined />}
                loading={actionLoading[record.id]}
              >
                禁用
              </Button>
            </Popconfirm>
          ) : (
            <Button
              size="small"
              icon={<PlayCircleOutlined />}
              loading={actionLoading[record.id]}
              onClick={() => onEnable(record.id)}
              style={{ color: '#52C41A' }}
            >
              启用
            </Button>
          )}
          <Popconfirm
            title="确定要删除该用户吗？此操作不可恢复"
            onConfirm={() => onDelete(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              loading={actionLoading[record.id]}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* 搜索和筛选栏 */}
      <Space style={{ marginBottom: 12 }} wrap>
        <Input
          placeholder="搜索用户名/邮箱..."
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          allowClear
          style={{ width: 220 }}
        />
        <Select
          placeholder="角色筛选"
          value={roleFilter || undefined}
          onChange={setRoleFilter}
          allowClear
          style={{ width: 120 }}
          options={ROLE_OPTIONS.map((r) => ({
            value: r.value,
            label: r.label,
          }))}
        />
        <Select
          placeholder="状态筛选"
          value={statusFilter || undefined}
          onChange={setStatusFilter}
          allowClear
          style={{ width: 120 }}
          options={[
            { value: 'active', label: '正常' },
            { value: 'pending', label: '待审批' },
            { value: 'disabled', label: '已禁用' },
            { value: 'rejected', label: '已拒绝' },
          ]}
        />
        {(keyword || roleFilter || statusFilter) && (
          <Button
            size="small"
            onClick={() => {
              setKeyword('')
              setRoleFilter('')
              setStatusFilter('')
            }}
          >
            重置
          </Button>
        )}
      </Space>

      {/* 用户表格 */}
      <Table
        dataSource={filteredUsers}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        scroll={{ x: 1100 }}
        pagination={{
          current: page,
          pageSize,
          total,
          showTotal: (t) => `共 ${t} 条`,
          showSizeChanger: true,
          showQuickJumper: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          onChange: onPageChange,
        }}
        locale={{
          emptyText:
            filteredUsers.length === 0 && users.length > 0
              ? '没有匹配的用户'
              : '暂无用户数据',
        }}
      />
    </div>
  )
}
