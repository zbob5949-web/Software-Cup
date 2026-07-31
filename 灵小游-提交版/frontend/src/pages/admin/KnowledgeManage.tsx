import { useEffect, useState } from 'react';
import {
  createKnowledgeItem,
  deleteKnowledgeItem,
  getKnowledgeList,
  updateKnowledgeItem,
  type KnowledgeItem,
} from '../../api/admin';

const categoryOptions = ['景点介绍', 'FAQ', '景区公告', '游玩攻略', '交通指引'];

function KnowledgeForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: KnowledgeItem;
  onSave: (item: Omit<KnowledgeItem, 'id' | 'updatedAt'>) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? '');
  const [category, setCategory] = useState(initial?.category ?? categoryOptions[0]);
  const [status, setStatus] = useState<'published' | 'draft' | 'archived'>(
    initial?.status ?? 'draft',
  );
  const [content, setContent] = useState(initial?.content ?? '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ title, category, status, content });
  };

  return (
    <form className="admin-knowledge-form" onSubmit={handleSubmit}>
      <div className="admin-form-group">
        <label className="admin-form-label">标题</label>
        <input
          className="admin-form-input"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="请输入知识标题"
          required
        />
      </div>
      <div className="admin-form-row">
        <div className="admin-form-group">
          <label className="admin-form-label">分类</label>
          <select className="admin-form-select" value={category} onChange={(e) => setCategory(e.target.value)}>
            {categoryOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div className="admin-form-group">
          <label className="admin-form-label">状态</label>
          <select
            className="admin-form-select"
            value={status}
            onChange={(e) => setStatus(e.target.value as 'published' | 'draft' | 'archived')}
          >
            <option value="published">已发布</option>
            <option value="draft">草稿</option>
            <option value="archived">已归档</option>
          </select>
        </div>
      </div>
      <div className="admin-form-group">
        <label className="admin-form-label">内容</label>
        <textarea
          className="admin-form-textarea"
          rows={6}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="请输入知识内容"
          required
        />
      </div>
      <div className="admin-form-actions">
        <button type="button" className="admin-btn admin-btn-secondary" onClick={onCancel}>
          取消
        </button>
        <button type="submit" className="admin-btn admin-btn-primary">
          {initial ? '保存修改' : '新增知识'}
        </button>
      </div>
    </form>
  );
}

export function KnowledgeManage() {
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeItem[]>([]);
  const [searchText, setSearchText] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<KnowledgeItem | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);

    getKnowledgeList({ search: searchText, category: filterCategory })
      .then((data) => {
        if (!active) return;
        setKnowledgeList(data);
        setError('');
      })
      .catch(() => {
        if (!active) return;
        setError('知识库数据加载失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [searchText, filterCategory]);

  const handleAdd = () => {
    setEditingItem(undefined);
    setShowForm(true);
  };

  const handleEdit = (item: KnowledgeItem) => {
    setEditingItem(item);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteKnowledgeItem(id);
      setKnowledgeList((prev) => prev.filter((item) => item.id !== id));
    } catch {
      setError('删除知识条目失败');
    }
  };

  const handleSave = async (data: Omit<KnowledgeItem, 'id' | 'updatedAt'>) => {
    setSubmitting(true);
    try {
      if (editingItem) {
        await updateKnowledgeItem(editingItem.id, data);
      } else {
        await createKnowledgeItem(data);
      }

      const refreshed = await getKnowledgeList({ search: searchText, category: filterCategory });
      setKnowledgeList(refreshed);
      setShowForm(false);
      setEditingItem(undefined);
      setError('');
    } catch {
      setError(editingItem ? '更新知识条目失败' : '新增知识条目失败');
    } finally {
      setSubmitting(false);
    }
  };

  const statusLabel: Record<string, string> = {
    published: '已发布',
    draft: '草稿',
    archived: '已归档',
  };

  const statusClass: Record<string, string> = {
    published: 'admin-status-published',
    draft: 'admin-status-draft',
    archived: 'admin-status-archived',
  };

  return (
    <div className="admin-page-knowledge">
      <div className="admin-page-header">
        <h2>知识库管理</h2>
        <p className="admin-page-subtitle">管理景区知识内容，支持文本录入和发布状态控制</p>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}

      <div className="admin-toolbar">
        <div className="admin-toolbar-left">
          <input
            className="admin-search-input"
            type="text"
            placeholder="搜索知识标题或内容..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <select className="admin-filter-select" value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
            <option value="">全部分类</option>
            {categoryOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div className="admin-toolbar-right">
          <button className="admin-btn admin-btn-primary" onClick={handleAdd}>
            新增知识
          </button>
        </div>
      </div>

      {showForm ? (
        <div className="admin-modal-overlay">
          <div className="admin-modal">
            <div className="admin-modal-header">
              <h3>{editingItem ? '编辑知识' : '新增知识'}</h3>
              <button className="admin-modal-close" onClick={() => { setShowForm(false); setEditingItem(undefined); }}>
                ×
              </button>
            </div>
            <div className="admin-modal-body">
              <KnowledgeForm
                initial={editingItem}
                onSave={handleSave}
                onCancel={() => { setShowForm(false); setEditingItem(undefined); }}
              />
              {submitting ? <div className="hint">正在保存...</div> : null}
            </div>
          </div>
        </div>
      ) : null}

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>标题</th>
              <th>分类</th>
              <th>状态</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {knowledgeList.map((item) => (
              <tr key={item.id}>
                <td className="admin-table-title">{item.title}</td>
                <td>
                  <span className="admin-category-tag">{item.category}</span>
                </td>
                <td>
                  <span className={`admin-status-tag ${statusClass[item.status]}`}>{statusLabel[item.status]}</span>
                </td>
                <td className="admin-table-date">{item.updatedAt}</td>
                <td>
                  <div className="admin-table-actions">
                    <button className="admin-action-btn" onClick={() => handleEdit(item)}>
                      编辑
                    </button>
                    <button className="admin-action-btn" onClick={async () => { const nextStatus = item.status === 'published' ? 'draft' : 'published'; await updateKnowledgeItem(item.id, { title: item.title, category: item.category, status: nextStatus, content: item.content }); setKnowledgeList((prev) => prev.map((current) => current.id === item.id ? { ...current, status: nextStatus } : current)); }}>
                      {item.status === 'published' ? '停用' : '启用'}
                    </button>
                    <button className="admin-action-btn admin-action-danger" onClick={() => handleDelete(item.id)}>
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && knowledgeList.length === 0 ? (
              <tr>
                <td colSpan={5} className="admin-table-empty">
                  暂无数据
                </td>
              </tr>
            ) : null}
            {loading ? (
              <tr>
                <td colSpan={5} className="admin-table-empty">
                  正在加载...
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
