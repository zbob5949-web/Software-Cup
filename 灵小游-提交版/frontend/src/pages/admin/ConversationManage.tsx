import { useCallback, useEffect, useState } from 'react';
import {
  deleteAdminConversation,
  getAdminConversationDetail,
  getAdminConversations,
  type AdminConversation,
  type AdminConversationMessage,
} from '../../api/admin';

function formatDate(value?: string): string {
  if (!value) return '未知时间';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
}

export function ConversationManage() {
  const [items, setItems] = useState<AdminConversation[]>([]);
  const [selected, setSelected] = useState<AdminConversation | null>(null);
  const [messages, setMessages] = useState<AdminConversationMessage[]>([]);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await getAdminConversations({ keyword: keyword.trim() || undefined, limit: 100 });
      setItems(result.sessions);
      setTotal(result.total);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '会话列表加载失败');
    } finally {
      setLoading(false);
    }
  }, [keyword]);

  useEffect(() => { void load(); }, [load]);

  async function openConversation(item: AdminConversation) {
    setSelected(item);
    setDetailLoading(true);
    try {
      setMessages(await getAdminConversationDetail(item.session_id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '会话详情加载失败');
      setMessages([]);
    } finally {
      setDetailLoading(false);
    }
  }

  async function removeConversation(item: AdminConversation) {
    if (!window.confirm(`确定删除“${item.title}”吗？删除后不可恢复。`)) return;
    try {
      await deleteAdminConversation(item.session_id);
      if (selected?.session_id === item.session_id) {
        setSelected(null);
        setMessages([]);
      }
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '会话删除失败');
    }
  }

  return (
    <div className="admin-page-knowledge">
      <div className="admin-page-header">
        <h1>用户会话管理</h1>
        <p className="admin-page-subtitle">查看游客与用户和 AI 导游的历史对话，定位服务问题并管理会话记录</p>
      </div>
      {error ? <div className="inline-error">{error}</div> : null}
      <div className="admin-card admin-conversation-card">
        <div className="admin-user-toolbar">
          <input
            className="admin-search-input"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') void load(); }}
            placeholder="搜索手机号或会话编号"
          />
          <button type="button" className="admin-btn admin-btn-primary" onClick={() => void load()}>刷新</button>
          <span className="admin-conversation-total">共 {total} 个会话</span>
        </div>
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th>会话主题</th><th>用户</th><th>消息数</th><th>最近消息</th><th>操作</th></tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={5} className="admin-table-empty">正在加载...</td></tr> : null}
              {!loading && items.length === 0 ? <tr><td colSpan={5} className="admin-table-empty">暂无用户会话</td></tr> : null}
              {!loading ? items.map((item) => (
                <tr key={item.session_id} className={selected?.session_id === item.session_id ? 'admin-conversation-selected' : ''}>
                  <td className="admin-table-title">
                    <button type="button" className="admin-conversation-title" onClick={() => void openConversation(item)}>{item.title}</button>
                    <small className="admin-conversation-id">{item.session_id}</small>
                    <small className="admin-conversation-preview">{item.preview}</small>
                  </td>
                  <td>{item.phone || '游客'}</td>
                  <td>{item.message_count}</td>
                  <td className="admin-table-date">{formatDate(item.last_message_at)}</td>
                  <td className="admin-table-actions">
                    <button type="button" className="admin-action-btn" onClick={() => void openConversation(item)}>查看</button>
                    <button type="button" className="admin-action-btn admin-action-danger" onClick={() => void removeConversation(item)}>删除</button>
                  </td>
                </tr>
              )) : null}
            </tbody>
          </table>
        </div>
      </div>

      {selected ? (
        <div className="admin-card admin-conversation-detail-card">
          <div className="admin-card-header">
            <div><h3>{selected.title}</h3><p className="admin-page-subtitle">{selected.phone} · {selected.session_id}</p></div>
            <button type="button" className="admin-action-btn" onClick={() => { setSelected(null); setMessages([]); }}>关闭详情</button>
          </div>
          <div className="admin-conversation-detail">
            {detailLoading ? <div className="admin-table-empty">正在加载消息...</div> : null}
            {!detailLoading && messages.length === 0 ? <div className="admin-table-empty">暂无消息</div> : null}
            {!detailLoading ? messages.map((message) => (
              <div key={message.id ?? `${message.created_at}-${message.content}`} className={`admin-conversation-message ${message.role}`}>
                <div className="admin-conversation-message-meta">{message.role === 'user' ? '用户' : 'AI 导游'} · {formatDate(message.created_at)}</div>
                <p>{message.content}</p>
              </div>
            )) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}