import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '../api/request';
import { useAuth } from '../lib/auth';
import { addTicketFavorite, removeTicketFavorite, getTicketFavorites } from '../api/favorite';

type TicketProduct = { id: string; name: string; price: number; note: string; ticket_type?: string };
const fallbackProducts: TicketProduct[] = [
  { id: '1', name: '灵山胜境成人票', price: 210, note: '18周岁以上成年人，含灵山胜境主景区参观。' },
  { id: '2', name: '灵山胜境半价票', price: 105, note: '6-18周岁未成年人、全日制本科及以下学生、60-69周岁老人。' },
  { id: '3', name: '灵山胜境免票', price: 0, note: '6周岁以下或1.4米以下儿童、70周岁以上老人、现役军人、残疾人。' },
  { id: '4', name: '门票 + 观光车联票', price: 225, note: '包含景区门票和观光车服务，无限次乘坐，更划算。', ticket_type: '联票' },
  { id: '5', name: '观光车单独购票', price: 40, note: '景区内交通，适合体力有限的游客。', ticket_type: '观光车票' },
];
const fallbackServices: TicketProduct[] = [
  { id: '9001', name: '素面', price: 35, note: '景区内清淡素食，方便快捷。', ticket_type: '餐食服务' },
  { id: '9002', name: '素斋', price: 50, note: '体验佛门饮食文化的素斋套餐。', ticket_type: '餐食服务' },
  { id: '9003', name: '导游服务', price: 300, note: '景区历史文化深度讲解服务。', ticket_type: '导游服务' },
];

export function TicketPage() {
  const navigate = useNavigate();
  const { isAuthenticated, identityType, username } = useAuth();
  const [products, setProducts] = useState<TicketProduct[]>(fallbackProducts);
  const [services, setServices] = useState<TicketProduct[]>(fallbackServices);
  const [selected, setSelected] = useState('16');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [paid, setPaid] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [visitorName, setVisitorName] = useState('');
  const [visitorPhone, setVisitorPhone] = useState(username || '');
  const [notice, setNotice] = useState('');
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());
  const product = useMemo(() => [...products, ...services].find((item) => item.id === selected) ?? products[0], [products, services, selected]);

  useEffect(() => {
    request.get('/api/tickets').then((response) => {
      const body = response.data as { data?: { tickets?: TicketProduct[] } };
      const items = body.data?.tickets ?? [];
      const ticketItems = items.filter((item) => !['餐食服务', '导游服务'].includes(item.ticket_type || ''));
      const serviceItems = items.filter((item) => ['餐食服务', '导游服务'].includes(item.ticket_type || ''));
      if (ticketItems.length) setProducts(ticketItems);
      if (serviceItems.length) setServices(serviceItems);
      const available = [...(ticketItems.length ? ticketItems : products), ...(serviceItems.length ? serviceItems : services)];
      if (available.length) setSelected((current) => available.some((item) => item.id === current) ? current : available[0].id);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!isAuthenticated || identityType === 'guest') return;
    getTicketFavorites().then((items) => setFavoriteIds(new Set(items.map((f) => f.id)))).catch(() => {});
  }, [isAuthenticated, identityType]);

  const handleToggleFavorite = async (itemId: number) => {
    if (!isAuthenticated || identityType === 'guest') { navigate('/login'); return; }
    try {
      if (favoriteIds.has(itemId)) {
        await removeTicketFavorite(itemId);
        setFavoriteIds((prev) => { const next = new Set(prev); next.delete(itemId); return next; });
      } else {
        await addTicketFavorite(itemId);
        setFavoriteIds((prev) => new Set(prev).add(itemId));
      }
    } catch { /* ignore */ }
  };

  async function createOrder() {
    if (!isAuthenticated || identityType === 'guest') { navigate('/login'); return; }
    if (!visitorName.trim() || !visitorPhone.trim()) { setNotice('请先填写游客姓名和手机号'); return; }
    if (paid || submitting) return;
    setSubmitting(true);
    try {
      const response = await request.post('/api/orders', { ticket_id: Number(product.id), quantity: 1, visitor_name: visitorName.trim(), visitor_phone: visitorPhone.trim(), remark: `入园日期：${date}`, pay_direct: true });
      const body = response.data as { data?: { order_no?: string } };
      setPaid(true);
      setNotice(`✅ 支付成功！订单号：${body.data?.order_no || '已生成'}，可在"我的订单"中查看或退票。`);
    } catch (error) { setNotice(error instanceof Error ? error.message : '支付失败，请稍后重试'); }
    finally { setSubmitting(false); }
  }

  if (!product) return null;
  return (
    <main className="ticket-page">
      <header className="ticket-header"><button type="button" className="ticket-back" onClick={() => navigate(-1)}>返回</button><div><span className="ticket-kicker">LINGSHAN TICKETS</span><h1>在线购票</h1></div><button type="button" className="ticket-header-link" onClick={() => navigate('/orders')}>我的订单</button></header>
      <section className="ticket-notice"><strong>灵山胜境入园预约</strong><span>价格仅供参考，实际以官方购票渠道和当天公告为准。</span></section>
      <div className="ticket-purchase-grid"><section className="ticket-section"><h2>选择票种</h2><div className="ticket-products">{products.map((item) => { const id = Number(item.id); const isFav = favoriteIds.has(id); return <button type="button" key={item.id} className={`ticket-product${selected === item.id ? ' selected' : ''}`} onClick={() => setSelected(item.id)}><span><strong>{item.name}</strong><small>{item.note}</small></span><div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span style={{ cursor: 'pointer', fontSize: 18, color: isFav ? '#f59e0b' : '#ccc', userSelect: 'none' }} onClick={(e) => { e.stopPropagation(); handleToggleFavorite(id); }} title={isFav ? '取消收藏' : '收藏票种'}>{isFav ? '★' : '☆'}</span><b>¥{item.price}</b></div></button>; })}</div></section><section className="ticket-section ticket-service-section"><h2>导游餐食服务</h2><p className="ticket-section-hint">按需选择素食或景区导游服务</p><div className="ticket-products">{services.map((item) => { const id = Number(item.id); const isFav = favoriteIds.has(id); return <button type="button" key={item.id} className={`ticket-product${selected === item.id ? ' selected' : ''}`} onClick={() => setSelected(item.id)}><span><strong>{item.name}</strong><small>{item.note}</small></span><div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span style={{ cursor: 'pointer', fontSize: 18, color: isFav ? '#f59e0b' : '#ccc', userSelect: 'none' }} onClick={(e) => { e.stopPropagation(); handleToggleFavorite(id); }} title={isFav ? '取消收藏' : '收藏票种'}>{isFav ? '★' : '☆'}</span><b>¥{item.price}</b></div></button>; })}</div></section></div><section className="ticket-section"><h2>游客信息</h2><div className="ticket-visitor-fields"><input className="ticket-date" placeholder="游客姓名" value={visitorName} onChange={(event) => setVisitorName(event.target.value)} /><input className="ticket-date" placeholder="联系电话" value={visitorPhone} onChange={(event) => setVisitorPhone(event.target.value)} /></div></section>
      <section className="ticket-section"><h2>入园日期</h2><input className="ticket-date" type="date" min={new Date().toISOString().slice(0, 10)} value={date} onChange={(event) => setDate(event.target.value)} /></section>
      <section className="ticket-summary"><div><span>已选：{product.name}</span><small>{date} · 1 张</small></div><strong>¥{product.price}</strong>{paid ? <button type="button" className="ticket-pay-btn paid" disabled>✅ 已支付</button> : <button type="button" onClick={() => void createOrder()} disabled={submitting}>{submitting ? '支付中...' : '立即支付'}</button>}{notice ? <p className="ticket-order-notice">{notice} {notice.startsWith('✅ 支付成功') ? <><button type="button" className="ticket-inline-link" onClick={() => navigate('/orders')}>查看我的订单</button><button type="button" className="ticket-inline-link" onClick={() => { setPaid(false); setNotice(''); setVisitorName(''); setVisitorPhone(''); }}>继续购票</button></> : null}</p> : null}</section>
    </main>
  );
}