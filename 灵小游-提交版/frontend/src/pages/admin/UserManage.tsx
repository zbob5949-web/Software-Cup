import { useEffect, useMemo, useState } from 'react';
import { getAdminUsers, updateAdminUser, type AdminUser } from '../../api/admin';

export function UserManage({ adminsOnly = false }: { adminsOnly?: boolean }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState<'all' | 'active' | 'disabled'>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatingIds, setUpdatingIds] = useState<Set<number>>(new Set());

  const load = () => { setLoading(true); getAdminUsers().then(setUsers).catch((e) => setError(e.message || '用户列表加载失败')).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  async function update(user: AdminUser, payload: Partial<AdminUser>) {
    // 乐观更新：先更新本地 state，再调 API
    setUpdatingIds(prev => new Set(prev).add(user.id));
    // 保存旧值用于回滚
    const oldUsers = [...users];
    setUsers(prev => prev.map(u => u.id === user.id ? { ...u, ...payload } : u));
    try {
      await updateAdminUser(user.id, payload);
    } catch (e) {
      // 回滚
      setUsers(oldUsers);
      setError(e instanceof Error ? e.message : '更新失败');
    } finally {
      setUpdatingIds(prev => { const next = new Set(prev); next.delete(user.id); return next; });
    }
  }
  const visibleUsers = useMemo(() => users.filter((user) => (!adminsOnly || user.role === 'admin') && (adminsOnly || user.role === 'user') && (!keyword.trim() || user.phone.includes(keyword.trim())) && (status === 'all' || (status === 'active' ? user.is_active : !user.is_active))), [users, keyword, status, adminsOnly]);
  return <div className="admin-page-knowledge"><div className="admin-page-header"><h1>{adminsOnly ? '管理员管理' : '用户管理'}</h1><p className="admin-page-subtitle">管理账号启用状态、访问角色、超级管理员权限及登录信息</p></div>{error ? <div className="inline-error">{error}</div> : null}<div className="admin-card admin-user-management-card"><div className="admin-user-toolbar"><input className="admin-search-input" value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="输入手机号搜索" /><select className="admin-filter-select" value={status} onChange={(e) => setStatus(e.target.value as typeof status)}><option value="all">账户状态</option><option value="active">已启用</option><option value="disabled">已停用</option></select><button className="admin-btn admin-btn-primary" onClick={load}>刷新</button></div><div className="admin-table-wrapper"><table className="admin-table"><thead><tr><th>ID</th><th>用户名/手机号</th><th>角色</th><th>权限</th><th>状态</th><th>最后登录时间</th><th>登录 IP 地址</th><th>操作</th></tr></thead><tbody>{loading ? <tr><td colSpan={8} className="admin-table-empty">正在加载...</td></tr> : visibleUsers.length === 0 ? <tr><td colSpan={8} className="admin-table-empty">暂无匹配账号</td></tr> : visibleUsers.map(user => <tr key={user.id} className={user.is_super_admin ? 'admin-user-super-row' : ''}><td>{user.id}</td><td className="admin-table-title">{user.phone}</td><td>{adminsOnly ? (user.phone === 'admin' ? <span className="admin-table-date">系统主管理员</span> : <select className="admin-form-select admin-user-role-select" value={user.role} onChange={e => void update(user, { role: e.target.value as AdminUser['role'] })}><option value="admin">管理员</option></select>) : <span className="admin-table-date">普通用户</span>}</td><td>{user.is_super_admin ? (user.phone === 'admin' ? <span className="admin-user-super-tag">超级管理员 · 系统主管理员</span> : <button type="button" className="admin-user-super-tag admin-user-super-button" onClick={() => void update(user, { is_super_admin: false })}>超级管理员 · 取消</button>) : adminsOnly ? <button className="admin-action-btn" onClick={() => void update(user, { is_super_admin: true })}>设为超级管理员</button> : <span className="admin-table-date">普通账号</span>}</td><td>{user.phone === 'admin' ? <span className={`admin-user-status active`}><span />已启用</span> : <button type="button" className={`admin-user-status ${user.is_active ? 'active' : 'disabled'}`} disabled={updatingIds.has(user.id)} onClick={() => void update(user, { is_active: !user.is_active })}><span />{updatingIds.has(user.id) ? '更新中...' : user.is_active ? '已启用' : '已停用'}</button>}</td><td className="admin-table-date">{user.last_login || '未登录'}</td><td className="admin-table-date">{user.last_login_ip || '暂无记录'}</td><td>{user.phone === 'admin' ? <span className="admin-table-date">受保护</span> : <button className="admin-action-btn" disabled={updatingIds.has(user.id)} onClick={() => void update(user, { is_active: !user.is_active })}>{updatingIds.has(user.id) ? '更新中...' : user.is_active ? '停用' : '启用'}</button>}</td></tr>)}</tbody></table></div><div className="admin-user-table-footer">共 {visibleUsers.length} 个账号</div></div></div>;
}