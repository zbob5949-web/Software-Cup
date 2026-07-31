import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getFavorites, getRouteFavorites, getTicketFavorites, removeFavorite, removeRouteFavorite, removeTicketFavorite, type FavoriteItem } from '../api/favorite';
import { useAuth } from '../lib/auth';

const TABS = [
  { key: 'spot', label: '景点' },
  { key: 'route', label: '路线' },
  { key: 'ticket', label: '票种' },
];

export function FavoritesPage() {
  const navigate = useNavigate();
  const { isAuthenticated, identityType } = useAuth();
  const [allItems, setAllItems] = useState<Record<string, FavoriteItem[]>>({ spot: [], route: [], ticket: [] });
  const [activeTab, setActiveTab] = useState('spot');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    if (!isAuthenticated || identityType === 'guest') {
      setAllItems({ spot: [], route: [], ticket: [] });
      setLoading(false);
      setError(identityType === 'guest' ? '游客模式不能使用收藏，请注册或登录' : '请先登录后查看收藏');
      return;
    }
    setLoading(true);
    setError('');
    Promise.all([
      getFavorites().catch(() => []),
      getRouteFavorites().catch(() => []),
      getTicketFavorites().catch(() => []),
    ]).then(([spot, route, ticket]) => {
      setAllItems({ spot, route, ticket });
      if (route.length > 0) setActiveTab('route');
      else if (ticket.length > 0) setActiveTab('ticket');
      else setActiveTab('spot');
    }).catch(() => setError('获取收藏列表失败'))
      .finally(() => setLoading(false));
  }, [isAuthenticated, identityType]);

  useEffect(() => { load(); }, [load]);

  const handleRemove = async (itemId: number, type: string) => {
    try {
      if (type === 'spot') await removeFavorite(itemId);
      else if (type === 'route') await removeRouteFavorite(itemId);
      else await removeTicketFavorite(itemId);
      setAllItems((prev) => ({
        ...prev,
        [type]: prev[type].filter((item) => item.id !== itemId),
      }));
    } catch { /* ignore */ }
  };

  const items = allItems[activeTab] || [];

  return (
    <div className="favorites-page">
      <header className="favorites-header">
        <button className="favorites-back" onClick={() => navigate(-1)}>← 返回</button>
        <h1>我的收藏</h1>
      </header>

      {loading ? (
        <div className="favorites-empty">加载中...</div>
      ) : error ? (
        <div className="favorites-empty">
          <p>{error}</p>
          {(!isAuthenticated || identityType === 'guest') && (
            <button className="guide-spot-btn primary" onClick={() => navigate('/login')} style={{ marginTop: 16 }}>
              去登录
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="favorites-tabs">
            {TABS.map((tab) => (
              <button key={tab.key} className={`favorites-tab${activeTab === tab.key ? ' active' : ''}`}
                onClick={() => setActiveTab(tab.key)}>
                {tab.label} ({allItems[tab.key]?.length || 0})
              </button>
            ))}
          </div>

          {items.length === 0 ? (
            <div className="favorites-empty">
              <p>还没有收藏{TABS.find(t => t.key === activeTab)?.label}</p>
              <button className="guide-spot-btn primary" onClick={() => navigate(activeTab === 'ticket' ? '/tickets' : '/guide')} style={{ marginTop: 16 }}>
                {activeTab === 'ticket' ? '去购票' : '去发现'}
              </button>
            </div>
          ) : (
            <div className="favorites-list">
              {items.map((item) => (
                <div key={`${activeTab}-${item.id}`} className="favorite-card">
                  <div className="favorite-card-body">
                    <h3>{item.name || `项目 #${item.id}`}</h3>
                    {item.category && <span className="favorite-category">{item.category}</span>}
                    {item.ticket_type && <span className="favorite-category">{item.ticket_type}</span>}
                    {item.price !== undefined && <span className="favorite-category">¥{item.price}</span>}
                    {item.duration && <span className="favorite-category">{item.duration}</span>}
                    {item.difficulty && <span className="favorite-category">{item.difficulty}</span>}
                    {item.description && <p className="favorite-desc">{item.description.slice(0, 80)}...</p>}
                    {item.favorited_at && <span className="favorite-time">收藏于 {item.favorited_at}</span>}
                  </div>
                  <div className="favorite-card-actions">
                    <button className="guide-spot-btn" onClick={() => {
                      if (activeTab === 'ticket') navigate('/tickets');
                      else navigate(`/guide?spot=${item.id}`);
                    }}>查看</button>
                    <button className="guide-spot-btn" style={{ color: '#EF4444', borderColor: 'rgba(239,68,68,0.2)' }}
                      onClick={() => handleRemove(item.id, activeTab)}>取消收藏</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}