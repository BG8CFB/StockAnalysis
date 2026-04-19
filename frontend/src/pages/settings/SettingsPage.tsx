/**
 * 个人设置页面
 * 用户个人信息管理、偏好设置、核心设置、通知设置、配额信息
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Card, Form, Input, Button, Select, message, Typography, Divider, Avatar, Space, Upload,
  Switch, Row, Col, Statistic, Spin, Progress,
} from 'antd'
import {
  UserOutlined, MailOutlined, SaveOutlined, CameraOutlined, ReloadOutlined,
  GlobalOutlined, SettingOutlined, BellOutlined, DashboardOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/auth.store'
import {
  getCoreSettings, updateCoreSettings,
  getNotificationSettings, updateNotificationSettings,
  getQuotaInfo,
  updateUserProfile,
  type CoreSettings, type NotificationSettings, type QuotaInfo,
} from '@/services/api/settings'

const { Title, Paragraph } = Typography

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore()
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingCore, setSavingCore] = useState(false)
  const [savingNotifications, setSavingNotifications] = useState(false)
  const [loading, setLoading] = useState(false)

  const [profileForm] = Form.useForm()
  const [coreForm] = Form.useForm()
  const [notificationForm] = Form.useForm()

  const [, setCoreSettings] = useState<CoreSettings | null>(null)
  const [, setNotificationSettings] = useState<NotificationSettings | null>(null)
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const [coreRes, notifRes, quotaRes] = await Promise.all([
        getCoreSettings().catch(() => null),
        getNotificationSettings().catch(() => null),
        getQuotaInfo().catch(() => null),
      ])

      if (coreRes?.data) {
        const cs = coreRes.data as CoreSettings
        setCoreSettings(cs)
        coreForm.setFieldsValue(cs)
      }

      if (notifRes?.data) {
        const ns = notifRes.data as NotificationSettings
        setNotificationSettings(ns)
        notificationForm.setFieldsValue(ns)
      }

      if (quotaRes?.data) {
        setQuotaInfo(quotaRes.data as QuotaInfo)
      }
    } finally {
      setLoading(false)
    }
  }, [coreForm, notificationForm])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  // ========== Profile ==========

  const handleSaveProfile = async () => {
    try {
      const values = await profileForm.validateFields()
      setSavingProfile(true)
      const updated = await updateUserProfile({
        display_name: values.display_name,
        email: values.email,
      })
      updateUser(updated)
      message.success('个人资料保存成功')
    } catch {
      // 表单验证失败或请求失败
    } finally {
      setSavingProfile(false)
    }
  }

  // ========== Core Settings ==========

  const handleSaveCore = async () => {
    try {
      const values = await coreForm.validateFields()
      setSavingCore(true)
      const res = await updateCoreSettings(values)
      if (res.data) {
        setCoreSettings(res.data as CoreSettings)
      }
      message.success('核心设置保存成功')
    } catch {
      // 表单验证失败或请求失败
    } finally {
      setSavingCore(false)
    }
  }

  // ========== Notifications ==========

  const handleSaveNotifications = async () => {
    try {
      const values = await notificationForm.validateFields()
      setSavingNotifications(true)
      const res = await updateNotificationSettings(values)
      if (res.data) {
        setNotificationSettings(res.data as NotificationSettings)
      }
      message.success('通知设置保存成功')
    } catch {
      // 表单验证失败或请求失败
    } finally {
      setSavingNotifications(false)
    }
  }

  // ========== Quota Helpers ==========

  const dailyPercent = quotaInfo?.daily_quota
    ? Math.min(100, Math.round((quotaInfo.daily_used / quotaInfo.daily_quota) * 100))
    : 0

  const monthlyPercent = quotaInfo?.monthly_quota
    ? Math.min(100, Math.round((quotaInfo.monthly_used / quotaInfo.monthly_quota) * 100))
    : 0

  return (
    <Spin spinning={loading}>
      <div style={{ maxWidth: 800 }}>
        <Title level={4} style={{ marginBottom: 24 }}>
          <SettingOutlined style={{ marginRight: 8 }} />
          个人设置
        </Title>

        {/* ===== Section 1: Profile ===== */}
        <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
          <Form
            form={profileForm}
            layout="vertical"
            initialValues={{
              username: user?.username ?? '',
              email: user?.email ?? '',
              display_name: (user as unknown as Record<string, unknown>)?.display_name ?? '',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
              <Avatar
                size={64}
                icon={<UserOutlined />}
                src={user?.avatar}
                style={{ backgroundColor: 'var(--accent-primary)' }}
              />
              <div>
                <Upload showUploadList={false} beforeUpload={() => false} accept="image/*">
                  <Button icon={<CameraOutlined />} size="small">更换头像</Button>
                </Upload>
              </div>
            </div>

            <Form.Item name="username" label="用户名">
              <Input prefix={<UserOutlined />} disabled />
            </Form.Item>

            <Space style={{ width: '100%' }} wrap>
              <Form.Item
                name="display_name"
                label="显示名称"
                style={{ flex: 1, minWidth: 200 }}
              >
                <Input placeholder="显示名称" />
              </Form.Item>
              <Form.Item
                name="email"
                label="邮箱"
                rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
                style={{ flex: 1, minWidth: 240 }}
              >
                <Input prefix={<MailOutlined />} type="email" placeholder="邮箱地址" />
              </Form.Item>
            </Space>

            <Form.Item style={{ marginTop: 16, textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveProfile}
                loading={savingProfile}
              >
                保存修改
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* ===== Section 2: Core Settings ===== */}
        <Card
          title={<Space><GlobalOutlined /><span>核心设置</span></Space>}
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Form form={coreForm} layout="vertical">
            <Form.Item
              name="default_market"
              label="默认分析市场"
              rules={[{ required: true, message: '请选择默认市场' }]}
            >
              <Select
                options={[
                  { value: 'china_a', label: 'A 股市场' },
                  { value: 'us_stock', label: '美股市场' },
                  { value: 'hk_stock', label: '港股市场' },
                ]}
                placeholder="选择默认市场"
              />
            </Form.Item>

            <Form.Item
              name="default_depth"
              label="默认分析深度"
              rules={[{ required: true, message: '请选择分析深度' }]}
            >
              <Select
                options={[
                  { value: 'quick', label: '快速分析' },
                  { value: 'standard', label: '标准分析' },
                  { value: 'deep', label: '深度分析' },
                ]}
                placeholder="选择分析深度"
              />
            </Form.Item>

            <Form.Item
              name="language"
              label="界面语言"
              rules={[{ required: true, message: '请选择语言' }]}
            >
              <Select
                options={[
                  { value: 'zh-CN', label: '简体中文' },
                  { value: 'en-US', label: 'English' },
                ]}
                placeholder="选择语言"
              />
            </Form.Item>

            <Form.Item
              name="timezone"
              label="时区"
              rules={[{ required: true, message: '请选择时区' }]}
            >
              <Select
                options={[
                  { value: 'Asia/Shanghai', label: '北京时间 (Asia/Shanghai)' },
                  { value: 'Asia/Hong_Kong', label: '香港时间 (Asia/Hong_Kong)' },
                  { value: 'America/New_York', label: '纽约时间 (America/New_York)' },
                  { value: 'UTC', label: 'UTC' },
                ]}
                placeholder="选择时区"
              />
            </Form.Item>

            <Form.Item style={{ marginTop: 16, textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveCore}
                loading={savingCore}
              >
                保存设置
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* ===== Section 3: Notification Preferences ===== */}
        <Card
          title={<Space><BellOutlined /><span>通知偏好</span></Space>}
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Form form={notificationForm} layout="vertical">
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item
                  name="email_enabled"
                  label="邮件通知"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="push_enabled"
                  label="推送通知"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                </Form.Item>
              </Col>
            </Row>

            <Divider style={{ margin: '12px 0' }} />
            <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 12 }}>
              通知事件
            </Paragraph>

            <Row gutter={24}>
              <Col span={12}>
                <Form.Item
                  name="task_completed"
                  label="任务完成"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="通知" unCheckedChildren="静默" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="task_failed"
                  label="任务失败"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="通知" unCheckedChildren="静默" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={24}>
              <Col span={12}>
                <Form.Item
                  name="daily_digest"
                  label="每日摘要"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="通知" unCheckedChildren="静默" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="marketing_emails"
                  label="营销邮件"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="通知" unCheckedChildren="静默" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item style={{ marginTop: 16, textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveNotifications}
                loading={savingNotifications}
              >
                保存偏好
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* ===== Section 4: Quota & Usage ===== */}
        <Card
          title={<Space><DashboardOutlined /><span>配额与用量</span></Space>}
          size="small"
          style={{ marginBottom: 16 }}
          extra={
            <Button icon={<ReloadOutlined />} size="small" onClick={loadSettings}>刷新</Button>
          }
        >
          {quotaInfo ? (
            <Row gutter={[24, 24]}>
              <Col xs={24} sm={12}>
                <Card size="small" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  <Statistic
                    title="今日用量"
                    value={`${quotaInfo.daily_used} / ${quotaInfo.daily_quota}`}
                    suffix="次"
                    styles={{ content: { fontSize: 20 } }}
                  />
                  <Progress
                    percent={dailyPercent}
                    size="small"
                    status={dailyPercent >= 90 ? 'exception' : dailyPercent >= 70 ? 'normal' : 'success'}
                    style={{ marginTop: 8 }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12}>
                <Card size="small" style={{ background: 'var(--bg-card)', border: 'none' }}>
                  <Statistic
                    title="本月用量"
                    value={`${quotaInfo.monthly_used} / ${quotaInfo.monthly_quota}`}
                    suffix="次"
                    styles={{ content: { fontSize: 20 } }}
                  />
                  <Progress
                    percent={monthlyPercent}
                    size="small"
                    status={monthlyPercent >= 90 ? 'exception' : monthlyPercent >= 70 ? 'normal' : 'success'}
                    style={{ marginTop: 8 }}
                  />
                </Card>
              </Col>
              {quotaInfo.reset_time && (
                <Col xs={24}>
                  <Paragraph type="secondary" style={{ fontSize: 12 }}>
                    下次重置时间: {new Date(quotaInfo.reset_time).toLocaleString()}
                  </Paragraph>
                </Col>
              )}
            </Row>
          ) : (
            <Paragraph type="secondary">暂无配额信息</Paragraph>
          )}
        </Card>
      </div>
    </Spin>
  )
}
