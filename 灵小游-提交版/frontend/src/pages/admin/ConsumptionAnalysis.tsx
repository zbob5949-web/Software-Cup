import { useEffect, useState } from 'react';
import request from '../../api/request';

type CostItem = { key: string; name: string; amount: number; ratio: number };
type SegmentItem = { name: string; count: number };
type ConsumptionReport = {
  source: string;
  record_count: number;
  basis_columns: string[];
  financial: {
    total_revenue: number;
    average_spend: number;
    average_group_size: number;
    average_satisfaction: number;
    cost_breakdown: CostItem[];
  };
  segments: { gender: SegmentItem[]; age_groups: SegmentItem[]; attraction_types: SegmentItem[] };
  monthly: { month: string; visitors: number; revenue: number }[];
};

function BarList({ items, money = false }: { items: { name: string; count?: number; amount?: number; ratio?: number }[]; money?: boolean }) {
  if (!items || items.length === 0) return <div className="admin-table-empty">暂无数据</div>;
  const max = Math.max(...items.map((item) => money ? item.amount || 0 : item.count || 0), 1);
  return <div style={{ display: 'grid', gap: 10 }}>
    {items.map((item) => {
      const value = money ? item.amount || 0 : item.count || 0;
      return <div key={item.name}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, fontSize: 13 }}>
          <span>{item.name}</span><strong>{money ? `¥${value.toLocaleString()}` : value.toLocaleString()}{money && item.ratio ? ` · ${item.ratio}%` : ''}</strong>
        </div>
        <div style={{ height: 8, background: '#edf3ef', borderRadius: 4, marginTop: 5, overflow: 'hidden' }}><div style={{ height: '100%', width: `${(value / max) * 100}%`, background: '#18a999', borderRadius: 4 }} /></div>
      </div>;
    })}
  </div>;
}

export function ConsumptionAnalysis() {
  const [report, setReport] = useState<ConsumptionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    request.get('/api/admin/consumption-analysis')
      .then((response) => {
        const data = (response.data as { code: number; data: ConsumptionReport } | undefined);
        if (data?.data) setReport(data.data);
        else setError('消费分析数据格式异常');
      })
      .catch(() => setError('消费分析数据加载失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="admin-table-empty">正在加载消费分析...</div>;
  if (error || !report) return <div className="inline-error">{error || '暂无消费分析数据'}</div>;
  const financial = report.financial || {} as ConsumptionReport['financial'];
  const segments = report.segments || {} as ConsumptionReport['segments'];
  const monthly = report.monthly || [];

  return <div className="admin-page-statistics">
    <div className="admin-page-header"><div><h2>消费分析</h2><p className="admin-page-subtitle">基于景区旅游行为数据的消费结构与财务报告</p></div></div>
    <div className="admin-card" style={{ marginBottom: 16 }}>
      <div className="admin-card-body" style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'center' }}>
        <span>分析记录 <strong>{report.record_count.toLocaleString()}</strong> 条</span>
        <span>数据来源 <strong>{report.source}</strong></span>
        <span style={{ color: 'var(--text-light)', fontSize: 12 }}>仅使用消费金额、用户画像、日期、团体规模和满意度字段</span>
      </div>
    </div>
    <div className="admin-stat-grid">
      <div className="admin-stat-card"><div className="admin-stat-info"><span className="admin-stat-label">消费总额</span><span className="admin-stat-value">¥{(financial.total_revenue ?? 0).toLocaleString()}</span><span className="admin-stat-change flat">样本累计</span></div></div>
      <div className="admin-stat-card"><div className="admin-stat-info"><span className="admin-stat-label">人均消费</span><span className="admin-stat-value">¥{financial.average_spend ?? '--'}</span><span className="admin-stat-change flat">按记录计算</span></div></div>
      <div className="admin-stat-card"><div className="admin-stat-info"><span className="admin-stat-label">平均团体规模</span><span className="admin-stat-value">{financial.average_group_size ?? '--'} 人</span><span className="admin-stat-change flat">用户行为</span></div></div>
      <div className="admin-stat-card"><div className="admin-stat-info"><span className="admin-stat-label">平均满意度</span><span className="admin-stat-value">{financial.average_satisfaction ?? '--'}</span><span className="admin-stat-change flat">满分 5 分</span></div></div>
    </div>
    <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
      <div className="admin-card"><div className="admin-card-header"><h3>财务报告 · 消费结构</h3></div><div className="admin-card-body"><BarList items={financial.cost_breakdown ?? []} money /></div></div>
      <div className="admin-card"><div className="admin-card-header"><h3>用户年龄分布</h3></div><div className="admin-card-body"><BarList items={segments.age_groups ?? []} /></div></div>
    </div>
    <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
      <div className="admin-card"><div className="admin-card-header"><h3>景区类型偏好</h3></div><div className="admin-card-body"><BarList items={segments.attraction_types ?? []} /></div></div>
      <div className="admin-card"><div className="admin-card-header"><h3>客群性别分布</h3></div><div className="admin-card-body"><BarList items={segments.gender ?? []} /></div></div>
    </div>
    <div className="admin-card" style={{ marginTop: 16 }}><div className="admin-card-header"><h3>月度消费趋势</h3></div><div className="admin-card-body"><BarList items={monthly.map((item) => ({ name: item.month, amount: item.revenue }))} money /></div></div>
  </div>;
}
