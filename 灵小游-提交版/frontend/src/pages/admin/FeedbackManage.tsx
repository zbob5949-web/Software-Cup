import { useEffect, useState } from 'react';
import {
  deleteAdminFeedback,
  getAdminFeedbackList,
  type FeedbackItem,
  type FeedbackStats,
} from '../../api/admin';

const categoryList = ['服务体验', '景点讲解', '路线推荐', '语音交互', '其他'];

function FeedbackStatsPanel({ stats }: { stats: FeedbackStats }) {
  const total = stats.total || 1;

  return (
    <div className="admin-feedback-stats">
      <div className="admin-feedback-stat-card">
        <span className="admin-feedback-stat-value" style={{ color: '#18A999' }}>
          {stats.positive}
        </span>
        <span className="admin-feedback-stat-label">好评 ({Math.round((stats.positive / total) * 100)}%)</span>
      </div>
      <div className="admin-feedback-stat-card">
        <span className="admin-feedback-stat-value" style={{ color: '#F0C48A' }}>
          {stats.neutral}
        </span>
        <span className="admin-feedback-stat-label">中评 ({Math.round((stats.neutral / total) * 100)}%)</span>
      </div>
      <div className="admin-feedback-stat-card">
        <span className="admin-feedback-stat-value" style={{ color: '#F3A6B3' }}>
          {stats.negative}
        </span>
        <span className="admin-feedback-stat-label">差评 ({Math.round((stats.negative / total) * 100)}%)</span>
      </div>
    </div>
  );
}

export function FeedbackManage() {
  const [feedbackList, setFeedbackList] = useState<FeedbackItem[]>([]);
  const [stats, setStats] = useState<FeedbackStats>({ total: 0, positive: 0, neutral: 0, negative: 0, avg_rating: 0 });
  const [searchText, setSearchText] = useState('');
  const [ratingFilter, setRatingFilter] = useState<number | ''>('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    getAdminFeedbackList({
      search: searchText || undefined,
      category: categoryFilter || undefined,
      rating: ratingFilter === '' ? undefined : ratingFilter,
    })
      .then((data) => {
        if (!active) return;
        if (!data) {
          setError('反馈数据加载失败');
          return;
        }
        setFeedbackList(data.items ?? []);
        setStats(data.stats ?? { total: 0, positive: 0, neutral: 0, negative: 0, avg_rating: 0 });
        setError('');
      })
      .catch(() => {
        if (!active) return;
        setError('反馈数据加载失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [searchText, categoryFilter, ratingFilter]);

  const handleDelete = async (id: string) => {
    try {
      await deleteAdminFeedback(id);
      const next = feedbackList.filter((item) => item.id !== id);
      setFeedbackList(next);
      const positive = next.filter((item) => item.rating >= 4).length;
      const neutral = next.filter((item) => item.rating === 3).length;
      const negative = next.filter((item) => item.rating <= 2).length;
      setStats({
        total: next.length,
        positive,
        neutral,
        negative,
        avg_rating: next.length ? Number((next.reduce((sum, item) => sum + item.rating, 0) / next.length).toFixed(2)) : 0,
      });
    } catch {
      setError('删除反馈失败');
    }
  };

  const renderStars = (rating: number) =>
    Array.from({ length: 5 }, (_, i) => (
      <svg
        key={i}
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill={i < rating ? '#D6A84F' : '#E8ECF8'}
        stroke={i < rating ? '#D6A84F' : '#DDE5EF'}
        strokeWidth="1"
      >
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ));

  const ratingLabel: Record<number, string> = {
    5: '非常满意',
    4: '满意',
    3: '一般',
    2: '不满意',
    1: '非常不满意',
  };

  return (
    <div className="admin-page-feedback">
      <div className="admin-page-header">
        <h2>游客反馈分析</h2>
        <p className="admin-page-subtitle">查看游客评价、反馈内容与满意度统计</p>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}

      <FeedbackStatsPanel stats={stats} />

      <div className="admin-toolbar">
        <div className="admin-toolbar-left">
          <input
            className="admin-search-input"
            type="text"
            placeholder="搜索用户名或反馈内容..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <select className="admin-filter-select" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="">全部分类</option>
            {categoryList.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            className="admin-filter-select"
            value={ratingFilter}
            onChange={(e) => setRatingFilter(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <option value="">全部评分</option>
            <option value={5}>5星</option>
            <option value={4}>4星</option>
            <option value={3}>3星</option>
            <option value={2}>2星</option>
            <option value={1}>1星</option>
          </select>
        </div>
      </div>

      <div className="admin-feedback-list">
        {feedbackList.map((item) => (
          <div key={item.id} className="admin-feedback-card">
            <div className="admin-feedback-header">
              <div className="admin-feedback-user">
                <div className="admin-feedback-avatar">{(item.username || '游')[0]}</div>
                <div>
                  <span className="admin-feedback-username">{item.username}</span>
                  <span className="admin-feedback-date">{item.date}</span>
                </div>
              </div>
              <div className="admin-feedback-rating">
                <div className="admin-feedback-stars">{renderStars(item.rating)}</div>
                <span className="admin-feedback-rating-text">{ratingLabel[item.rating]}</span>
              </div>
            </div>
            <p className="admin-feedback-content">{item.content}</p>
            <div className="admin-feedback-footer">
              <span className="admin-category-tag">{item.category}</span>
              <button className="admin-action-btn admin-action-danger" onClick={() => handleDelete(item.id)}>
                删除
              </button>
            </div>
          </div>
        ))}
        {!loading && feedbackList.length === 0 ? <div className="admin-table-empty">暂无匹配的反馈数据</div> : null}
        {loading ? <div className="admin-table-empty">正在加载...</div> : null}
      </div>
    </div>
  );
}
