/**
 * 用户审批对话框
 * 展示待审批用户列表，支持批量审批/拒绝
 */

import { useState, useEffect } from 'react'
import {
  Modal, Table, Button, Space, Tag, Typography, Empty, Spin,
} from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { AdminUser } from '@/types/admin.types'

const { Text } = Typography

interface UserApprovalDialogProps {
  open: boolean
  onClose: () => void
  pendingUsers: AdminUser[]
  loading: boolean
  actionLoading: Record<string, boolean>
  onApprove: (userId: string) => Promise<void>
  onReject: (userId: string) => Promise<void>
  onRefresh: () => Promise<void>
}

export default function UserApprovalDialog({
  open,
  onClose,
  pendingUsers,
  loading,
  actionLoading,
  onApprove,
  onReject,
  onRefresh,
}: UserApprovalDialogProps) {
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])

  useEffect(() => {
    if (open) {
      onRefresh()
      setSelectedRowKeys([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const columns: ColumnsType<AdminUser> = [
    {
      title: '用户名',
      dataIndex: 'username',
      width: 120,
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      width: 180,
      render: (text: string) => text || '-',
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
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (status: string) => (
        <Tag color="orange">{status === 'pending' ? '待审批' : status}</Tag>
      ),
    },
    {
      title: '操作',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            type="primary"
            icon={<CheckCircleOutlined />}
            loading={actionLoading[record.id]}
            onClick={() => onApprove(record.id)}
          >
            通过
          </Button>
          <Button
            size="small"
            danger
            icon={<CloseCircleOutlined />}
            loading={actionLoading[record.id]}
            onClick={() => onReject(record.id)}
          >
            拒绝
          </Button>
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  }

  return (
    <Modal
      title="用户审批"
      open={open}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>关闭</Button>,
      ]}
    >
      <Spin spinning={loading}>
        <Table
          dataSource={pendingUsers}
          columns={columns}
          rowKey="id"
          rowSelection={rowSelection}
          size="small"
          pagination={false}
          scroll={{ x: 700 }}
          locale={{
            emptyText: (
              <Empty
                description="暂无待审批用户"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Spin>
    </Modal>
  )
}
