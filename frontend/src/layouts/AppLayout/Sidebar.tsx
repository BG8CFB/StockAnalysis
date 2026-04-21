import { useState, useEffect } from 'react'
import { Layout, Menu, Button, Drawer } from 'antd'
import useIsMobile from '@/hooks/useIsMobile'
import {
  DashboardOutlined,
  LineChartOutlined,
  BookOutlined,
  UserOutlined,
  RobotOutlined,
  ToolOutlined,
  SolutionOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
  TeamOutlined,
  SearchOutlined,
  HeartOutlined,
  StockOutlined,
  FundOutlined,
  FileTextOutlined,
  CloudServerOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  AuditOutlined,
  CodeOutlined,
  IdcardOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  AppstoreOutlined,
  SettingOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAppStore, getEffectiveTheme } from '@/stores/app.store'

const { Sider } = Layout

/** 响应式断点：小于此宽度视为移动端 */
const MOBILE_BREAKPOINT = 768

const menuItems = [
  // ====== 工作台 ======
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },

  // ====== 投资研究 ======
  {
    key: 'research',
    icon: <LineChartOutlined />,
    label: '投资研究',
    children: [
      { key: '/screening', icon: <SearchOutlined />, label: '智能筛选' },
      { key: '/favorites', icon: <HeartOutlined />, label: '我的自选股' },
      { key: '/analysis/single', icon: <StockOutlined />, label: '单股分析' },
      { key: '/analysis/batch', icon: <FundOutlined />, label: '批量分析' },
      { key: '/tasks', icon: <SolutionOutlined />, label: '任务中心' },
      { key: '/reports', icon: <FileTextOutlined />, label: '分析报告' },
    ],
  },

  // ====== 学习中心 ======
  { key: '/learning', icon: <BookOutlined />, label: '学习中心' },

  // ====== 个人中心 ======
  {
    key: 'personal',
    icon: <UserOutlined />,
    label: '个人中心',
    children: [
      { key: '/settings/profile', icon: <IdcardOutlined />, label: '个人资料' },
      { key: '/settings/usage', icon: <BarChartOutlined />, label: '使用统计' },
    ],
  },

  // ====== AI 配置 ======
  {
    key: 'ai-settings',
    icon: <RobotOutlined />,
    label: 'AI 配置',
    children: [
      { key: '/settings/agents', icon: <ThunderboltOutlined />, label: '智能体管理' },
      { key: '/settings/mcp', icon: <ApiOutlined />, label: 'MCP 服务' },
      { key: '/settings/mcp-tools', icon: <AppstoreOutlined />, label: 'MCP 工具' },
      { key: '/settings/config', icon: <SettingOutlined />, label: '模型与数据源' },
    ],
  },

  // ====== 系统运维 ======
  {
    key: 'system',
    icon: <ToolOutlined />,
    label: '系统运维',
    children: [
      { key: '/system/data-source-status', icon: <CloudServerOutlined />, label: '数据源状态' },
      { key: '/system/sync', icon: <SyncOutlined />, label: '数据同步' },
      { key: '/system/scheduler', icon: <ClockCircleOutlined />, label: '定时任务' },
      { key: '/settings/cache', icon: <DeleteOutlined />, label: '缓存管理' },
      { key: '/system/database', icon: <DatabaseOutlined />, label: '数据库管理' },
      { key: '/system/operation-logs', icon: <AuditOutlined />, label: '操作日志' },
      { key: '/system/system-logs', icon: <CodeOutlined />, label: '系统日志' },
    ],
  },

  // ====== 管理后台 ======
  {
    key: 'admin',
    icon: <TeamOutlined />,
    label: '管理后台',
    children: [
      { key: '/admin/users', icon: <UserAddOutlined />, label: '用户管理' },
    ],
  },
]

/** 菜单内容（桌面端 Sider 和移动端 Drawer 共用） */
function MenuContent({
  collapsed,
  openKeys,
  setOpenKeys,
  selectedKeys,
  onNavigate,
  effectiveTheme,
}: {
  collapsed: boolean
  openKeys: string[]
  setOpenKeys: (keys: string[]) => void
  selectedKeys: string[]
  onNavigate: (key: string) => void
  effectiveTheme: 'light' | 'dark'
}) {
  return (
    <>
      <Menu
        mode="inline"
        theme={effectiveTheme === 'dark' ? 'dark' : 'light'}
        selectedKeys={selectedKeys}
        openKeys={collapsed ? [] : openKeys}
        onOpenChange={setOpenKeys}
        items={menuItems as unknown as []}
        onClick={({ key }) => onNavigate(key)}
        style={{
          background: 'transparent',
          borderRight: 'none',
          paddingTop: 8,
        }}
      />
    </>
  )
}

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebar, setSidebarCollapsed, theme } = useAppStore()
  const effectiveTheme = getEffectiveTheme(theme)
  const [openKeys, setOpenKeys] = useState<string[]>([])
  const isMobile = useIsMobile(MOBILE_BREAKPOINT)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 移动端自动折叠侧边栏
  useEffect(() => {
    if (isMobile) setSidebarCollapsed(true)
  }, [isMobile, setSidebarCollapsed])

  const selectedKeys = [location.pathname]

  /** 导航并关闭移动端菜单 */
  const handleNavigate = (key: string) => {
    if (key.startsWith('/')) {
      navigate(key)
      if (isMobile) setDrawerOpen(false)
    }
  }

  /** 移动端打开菜单 */
  const handleOpenMobileMenu = () => setDrawerOpen(true)

  // ========== 移动端渲染 ==========
  if (isMobile) {
    return (
      <>
        {/* 移动端汉堡按钮 */}
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={handleOpenMobileMenu}
          style={{
            position: 'fixed',
            top: 12,
            left: 12,
            zIndex: 1001,
            fontSize: 18,
            color: 'var(--text-primary)',
          }}
        />
        {/* 移动端抽屉菜单 */}
        <Drawer
          placement="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          width={280}
          styles={{ body: { padding: 0, background: 'var(--bg-sidebar)' } }}
          closable={false}
        >
          <div style={{ height: 56, display: 'flex', alignItems: 'center', padding: '0 20px', borderBottom: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent-primary)', letterSpacing: 1 }}>
              TA
            </span>
          </div>
          <Menu
            mode="inline"
            theme={effectiveTheme === 'dark' ? 'dark' : 'light'}
            selectedKeys={selectedKeys}
            openKeys={openKeys}
            onOpenChange={setOpenKeys}
            items={menuItems as unknown as []}
            onClick={({ key }) => handleNavigate(key)}
            style={{ background: 'transparent', borderRight: 'none', paddingTop: 8 }}
          />
        </Drawer>
      </>
    )
  }

  // ========== 桌面端渲染 ==========
  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={sidebarCollapsed}
      width={240}
      collapsedWidth={72}
      style={{
        background: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-color)',
        position: 'sticky',
        top: 0,
        height: '100vh',
        left: 0,
        overflow: 'auto',
      }}
    >
      <div
        style={{
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: sidebarCollapsed ? 'center' : 'space-between',
          padding: sidebarCollapsed ? 0 : '0 24px',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        {!sidebarCollapsed && (
          <span
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: 'var(--accent-primary)',
              letterSpacing: 1,
            }}
          >
            TA
          </span>
        )}
        <Button
          type="text"
          icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={toggleSidebar}
          style={{ color: 'var(--text-secondary)' }}
        />
      </div>

      <MenuContent
        collapsed={sidebarCollapsed}
        openKeys={openKeys}
        setOpenKeys={setOpenKeys}
        selectedKeys={selectedKeys}
        onNavigate={(key) => { if (key.startsWith('/')) navigate(key) }}
        effectiveTheme={effectiveTheme}
      />
    </Sider>
  )
}
