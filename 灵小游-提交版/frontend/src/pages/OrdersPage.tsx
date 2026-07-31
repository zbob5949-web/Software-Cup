import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMyOrders, refundOrder, type OrderItem } from '../api/order';
import { useAuth } from '../lib/auth';

const statusLabels: Record<string, string> = {
  pending: '未支付',
  paid: '已支付',
  refunded: '已退款',
};

const tabs = [
  { value: 'all', label: '全部' },
  { value: 'paid', label: '已支付' },
  { value: 'pending', label: '未支付' },
  { value: 'refunded', label: '已退款' },
] as const;

function formatDate(value?: string) {
  if (!value) return '时间未知';
  return value.replace('T', ' ').slice(0, 16);
}

function maskPhone(phone: string) {
  return phone.length >= 7 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone;
}

export function OrdersPage() {
  const navigate = useNavigate();
  const { isAuthenticated, identityType } = useAuth();
  const [items, setItems] = useState<OrderItem[]>([]);
  const [filter, setFilter] = useState<(typeof tabs)[number]['value']>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    if (!isAuthenticated || identityType === 'guest') {
      setItems([]);
      setLoading(false);
      setError(identityType === 'guest' ? '游客模式不能查看订单，请注册或登录' : '请先登录后查看订单');
      return;
    }
    setLoading(true);
    setError('');
    getMyOrders()
      .then(setItems)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '获取订单列表失败'))
      .finally(() => setLoading(false));
  }, [identityType, isAuthenticated]);

  useEffect(() => { load(); }, [load]);

  const handleRefund = useCallback(async (orderNo: string) => {
    if (!window.confirm('确认退票？退款将原路返回。')) return;
    try {
      await refundOrder(orderNo);
      load(); // 刷新列表
    } catch (e) {
      alert(e instanceof Error ? e.message : '退票失败');
    }
  }, [load]);

  const visibleItems = useMemo(
    () => filter === 'all' ? items : items.filter((item) => item.order_status === filter),
    [filter, items],
  );

  return (
    <main className="orders-page">
      <header className="favorites-header orders-header">
        <button type="button" className="favorites-back" onClick={() => navigate(-1)}>← 返回</button>
        <h1>我的订单</h1>
        <button type="button" className="ticket-header-link" onClick={() => navigate('/tickets')}>在线购票</button>
      </header>

      {loading ? <div className="favorites-empty">加载中...</div> : error ? (
        <div className="favorites-empty">
          <p>{error}</p>
          <button type="button" className="guide-spot-btn primary" onClick={() => navigate('/login')} style={{ marginTop: 16 }}>去登录</button>
        </div>
      ) : (
        <>
          <div className="orders-toolbar" role="tablist" aria-label="订单状态筛选">
            {tabs.map((tab) => (
              <button
                type="button"
                role="tab"
                aria-selected={filter === tab.value}
                key={tab.value}
                className={`orders-status-tab${filter === tab.value ? ' active' : ''}`}
                onClick={() => setFilter(tab.value)}
              >{tab.label}</button>
            ))}
          </div>
          {visibleItems.length === 0 ? (
            <div className="favorites-empty">
              <p>{items.length ? '当前状态暂无订单' : '还没有订单'}</p>
              <button type="button" className="guide-spot-btn primary" onClick={() => navigate('/tickets')} style={{ marginTop: 16 }}>去购票</button>
            </div>
          ) : (
            <div className="orders-list">
              {visibleItems.map((item) => (
                <article className="order-card" key={item.order_no}>
                  <div className="order-card-top">
                    <div>
                      <h2>{item.ticket_name || `票种 #${item.ticket_id}`}</h2>
                      <p>订单号：{item.order_no}</p>
                    </div>
                    <span className={`order-status-badge order-status-${item.order_status}`}>{statusLabels[item.order_status] || item.order_status}</span>
                  </div>
                  <div className="order-card-info">
                    <span>游客：{item.visitor_name}</span>
                    <span>联系电话：{maskPhone(item.visitor_phone)}</span>
                    <span>下单时间：{formatDate(item.created_at)}</span>
                    <span>数量：{item.quantity} 张</span>
                  </div>
                  <div className="order-card-bottom">
                    <strong>¥{Number(item.total_amount).toFixed(2)}</strong>
                    {item.order_status === 'paid' && (
                      <button type="button" className="guide-spot-btn cancel" onClick={() => handleRefund(item.order_no)}>申请退票</button>
                    )}
                    <button type="button" className="guide-spot-btn primary" onClick={() => navigate('/tickets')}>再次购票</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
