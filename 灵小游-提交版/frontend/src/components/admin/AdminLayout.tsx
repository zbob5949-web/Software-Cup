import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AdminErrorBoundary } from './AdminErrorBoundary';

interface NavItem {
  path: string;
  label: string;
}

const navItems: NavItem[] = [
  { path: '/admin', label: '首页概览' },
  { path: '/admin/knowledge', label: '知识库管理' },
  { path: '/admin/avatar', label: '数字人管理' },
  { path: '/admin/feedback', label: '游客反馈分析' },
  { path: '/admin/sentiment', label: '用户感受报告' },
  { path: '/admin/faqs', label: 'FAQ 管理' },
  { path: '/admin/statistics', label: '数据统计大屏' },
  { path: '/admin/consumption', label: '消费分析' },
  { path: '/admin/settings', label: '系统设置' },
  { path: '/admin/users', label: '用户管理' },
  { path: '/admin/admins', label: '管理员管理' },
  { path: '/admin/conversations', label: '用户会话管理' },
  { path: '/admin/spots', label: '景点信息管理' },
  { path: '/admin/tickets', label: '购票管理' },
  { path: '/admin/favorites', label: '用户收藏管理' },
  { path: '/admin/orders', label: '用户订单管理' },
];

export function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="admin-layout">
      {sidebarOpen ? <div className="admin-sidebar-overlay" onClick={() => setSidebarOpen(false)} /> : null}

      <aside className={`admin-sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="admin-sidebar-header">
          <div className="admin-brand-mark" aria-hidden="true">灵</div>
          <div className="admin-brand-text">
            <span className="admin-brand-title">灵山智游管理</span>
            <span className="admin-brand-sub">AI 数字人后台</span>
          </div>
        </div>

        <nav className="admin-sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/admin'}
              className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="admin-sidebar-footer">
          <NavLink to="/home" className="admin-nav-item back-link">
            <span>返回游客端</span>
          </NavLink>
        </div>
      </aside>

      <div className="admin-main">
        <header className="admin-top-bar">
          <button className="admin-menu-btn" onClick={() => setSidebarOpen(true)} aria-label="打开菜单">
            ☰
          </button>
          <div className="admin-top-bar-title">灵山智游管理后台</div>
        </header>

        <div className="admin-content">
          <AdminErrorBoundary>
            <Outlet />
          </AdminErrorBoundary>
        </div>
      </div>
    </div>
  );
}

