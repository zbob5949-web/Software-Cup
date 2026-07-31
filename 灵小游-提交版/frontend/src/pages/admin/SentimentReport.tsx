import { useEffect, useState } from 'react';
import {
  getUserSentimentReport,
  getSentimentReport,
  type UserSentimentPayload,
  type SentimentReport,
} from '../../api/admin';

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 70 ? '#18A999' : score >= 50 ? '#D6A84F' : '#F3A6B3';
  const label = score >= 80 ? '优秀' : score >= 70 ? '良好' : score >= 50 ? '一般' : '需关注';
  return (
    <div className="admin-card" style={{ textAlign: 'center' }}>
      <div className="admin-card-header"><h3>综合感受评分</h3></div>
      <div className="admin-card-body">
        <div style={{ position: 'relative', display: 'inline-block', margin: '8px 0' }}>
          <svg width="160" height="90" viewBox="0 0 160 90">
            <path d="M20 80 A60 60 0 0 1 140 80" fill="none" stroke="#e8ecf0" strokeWidth="12" />
            <path
              d="M20 80 A60 60 0 0 1 140 80"
              fill="none"
              stroke={color}
              strokeWidth="12"
              strokeDasharray={`${(score / 100) * 188} 188`}
              strokeLinecap="round"
            />
          </svg>
          <div style={{ position: 'absolute', bottom: -4, left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color }}>{score}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>{label}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ items }: { items: { label: string; value: string | number; color?: string }[] }) {
  return (
    <div className="admin-sentiment-summary-grid">
      {items.map((it) => (
        <div key={it.label} className="admin-feedback-stat-card">
          <span className="admin-feedback-stat-value" style={it.color ? { color: it.color } : undefined}>
            {it.value}
          </span>
          <span className="admin-feedback-stat-label">{it.label}</span>
        </div>
      ))}
    </div>
  );
}

function BarChart({ data, barKey, labelKey, color }: { data: Record<string, any>[]; barKey: string; labelKey: string; color: string }) {
  const max = Math.max(...data.map((d) => Number(d[barKey]) || 0), 1);
  return (
    <div className="admin-bar-chart" style={{ height: 160, alignItems: 'flex-end' }}>
      {data.map((item) => (
        <div key={item[labelKey]} className="admin-bar-item">
          <div className="admin-bar" style={{ height: `${(Number(item[barKey]) / max) * 120}px`, background: color }}>
            <span className="admin-bar-value">{item[barKey]}</span>
          </div>
          <span className="admin-bar-label">{item[labelKey]}</span>
        </div>
      ))}
    </div>
  );
}

function SentimentStackedBars({ items }: { items: { date: string; positive: number; neutral: number; negative: number; total?: number }[] }) {
  if (!items.length) return <div className="admin-table-empty">暂无数据</div>;
  return (
    <div className="admin-sentiment-chart">
      {items.map((pt) => {
        const t = (pt.positive + pt.neutral + pt.negative) || 1;
        return (
          <div key={pt.date} className="admin-sentiment-col">
            <div className="admin-sentiment-bar-wrap">
              <div className="admin-sentiment-bar" style={{ height: `${(pt.positive / t) * 100}%`, background: '#18A999' }} />
              <div className="admin-sentiment-bar" style={{ height: `${(pt.neutral / t) * 100}%`, background: '#D6A84F' }} />
              <div className="admin-sentiment-bar" style={{ height: `${(pt.negative / t) * 100}%`, background: '#F3A6B3' }} />
            </div>
            <span className="admin-sentiment-label">{pt.date.slice(5)}</span>
          </div>
        );
      })}
    </div>
  );
}

function PainPointCard({ items }: { items: { label: string; score: number; keywords: string[] }[] }) {
  if (!items.length) return <div className="admin-table-empty">暂无明显痛点</div>;
  const maxScore = Math.max(...items.map((p) => p.score), 1);
  return (
    <div>
      {items.map((p) => (
        <div key={p.label} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{p.label}</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>{p.score}次提及</span>
          </div>
          <div style={{ background: '#e8ecf0', borderRadius: 6, height: 8, overflow: 'hidden' }}>
            <div style={{ width: `${(p.score / maxScore) * 100}%`, height: '100%', background: 'linear-gradient(90deg, #F3A6B3, #e27e91)', borderRadius: 6 }} />
          </div>
          <div style={{ marginTop: 3, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {p.keywords.map((kw) => (
              <span key={kw} className="admin-keyword-tag" style={{ fontSize: '0.7rem', color: '#F3A6B3' }}>{kw}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ExampleList({ items, type }: { items: { text: string; rating: number; date: string }[]; type: 'positive' | 'negative' }) {
  if (!items.length) return <div className="admin-table-empty">暂无数据</div>;
  const color = type === 'positive' ? '#18A999' : '#F3A6B3';
  return (
    <div>
      {items.map((ex, i) => (
        <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--line, #eee)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <span style={{ color, fontWeight: 700, fontSize: '0.8rem', minWidth: 28 }}>{'★'.repeat(ex.rating)}</span>
          <span style={{ flex: 1, fontSize: '0.82rem', lineHeight: 1.5 }}>{ex.text}</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-light)', whiteSpace: 'nowrap' }}>{ex.date}</span>
        </div>
      ))}
    </div>
  );
}

function SuggestionList({ items }: { items: string[] }) {
  return (
    <div>
      {items.map((s, i) => (
        <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--line, #eee)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <span style={{ background: '#4F7CFF', color: '#fff', borderRadius: '50%', width: 20, height: 20, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', flexShrink: 0, marginTop: 1 }}>{i + 1}</span>
          <span style={{ fontSize: '0.85rem', lineHeight: 1.5 }}>{s}</span>
        </div>
      ))}
    </div>
  );
}

export function SentimentReport() {
  const [data, setData] = useState<UserSentimentPayload | null>(null);
  const [textReport, setTextReport] = useState<SentimentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeConsumptionTab, setActiveConsumptionTab] = useState<'breakdown' | 'satisfaction'>('breakdown');

  useEffect(() => {
    let active = true;
    setLoading(true);

    Promise.all([
      getUserSentimentReport(),
      getSentimentReport({ use_ai: false }),
    ])
      .then(([d, tr]) => {
        if (!active) return;
        if (d) setData(d);
        if (tr) setTextReport(tr);
        if (!d && !tr) setError('数据加载失败');
      })
      .catch(() => {
        if (active) setError('用户感受报告数据加载失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);

  if (loading) return <div className="admin-page-sentiment"><div className="admin-page-header"><h2>用户感受报告</h2></div><div className="admin-table-empty">正在加载报告数据...</div></div>;
  if (error && !data && !textReport) return <div className="admin-page-sentiment"><div className="admin-page-header"><h2>用户感受报告</h2></div><div className="inline-error">{error}</div></div>;

  return (
    <div className="admin-page-sentiment">
      <div className="admin-page-header">
        <h2>用户感受报告</h2>
        <p className="admin-page-subtitle">
          综合反馈评分 · 对话情感 · 消费满意度 · 文本情感分析
          {data ? <span style={{ marginLeft: 12, fontSize: '0.75rem', color: 'var(--text-light)' }}>{data.period.start_date} 至 {data.period.end_date}</span> : null}
        </p>
      </div>

      {/* ── 综合评分 ── */}
      {data ? (
        <>
          <div className="admin-dashboard-grid" style={{ marginBottom: 16 }}>
            <ScoreGauge score={data.overallScore} />
            <div className="admin-card">
              <div className="admin-card-header"><h3>总体概况</h3></div>
              <div className="admin-card-body">
                <p style={{ fontSize: '0.9rem', lineHeight: 1.7, color: 'var(--text-mid)' }}>{data.overallSummary}</p>
              </div>
            </div>
          </div>

          {/* ── 反馈统计 ── */}
          <StatRow items={[
            { label: '反馈总数', value: data.feedback.total, color: '#4F7CFF' },
            { label: '好评率', value: data.feedback.satisfactionPct + '%', color: '#18A999' },
            { label: '平均评分', value: data.feedback.avgRating.toFixed(1), color: '#D6A84F' },
            { label: '差评数', value: data.feedback.negative, color: '#F3A6B3' },
          ]} />

          {/* ── 反馈分类 ── */}
          {data.feedback.categories.length > 0 ? (
            <div className="admin-card" style={{ marginTop: 16 }}>
              <div className="admin-card-header"><h3>反馈分类统计</h3></div>
              <div className="admin-card-body">
                <BarChart
                  data={data.feedback.categories.map((c) => ({ name: c.name, value: c.total }))}
                  barKey="value"
                  labelKey="name"
                  color="#4F7CFF"
                />
              </div>
            </div>
          ) : null}

          {/* ── 对话情感 ── */}
          <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
            <div className="admin-card">
              <div className="admin-card-header"><h3>用户对话情感分析</h3></div>
              <div className="admin-card-body">
                <StatRow items={[
                  { label: '正向情绪', value: data.chatSentiment.positiveRatio + '%', color: '#18A999' },
                  { label: '中性情绪', value: data.chatSentiment.neutralRatio + '%', color: '#D6A84F' },
                  { label: '负向情绪', value: data.chatSentiment.negativeRatio + '%', color: '#F3A6B3' },
                  { label: '分析消息数', value: data.chatSentiment.totalMessages, color: '#4F7CFF' },
                ]} />
              </div>
            </div>
            <div className="admin-card">
              <div className="admin-card-header"><h3>情感趋势（日）</h3></div>
              <div className="admin-card-body">
                <SentimentStackedBars items={data.chatSentiment.trend} />
              </div>
            </div>
          </div>

          {/* ── 消费维度 ── */}
          {data.consumption.available ? (
            <div className="admin-card" style={{ marginTop: 16 }}>
              <div className="admin-card-header">
                <h3>消费满意度维度</h3>
                <div className="admin-trend-tabs">
                  <button className={`admin-trend-tab${activeConsumptionTab === 'breakdown' ? ' active' : ''}`} onClick={() => setActiveConsumptionTab('breakdown')}>消费结构</button>
                  <button className={`admin-trend-tab${activeConsumptionTab === 'satisfaction' ? ' active' : ''}`} onClick={() => setActiveConsumptionTab('satisfaction')}>关键指标</button>
                </div>
              </div>
              <div className="admin-card-body">
                {activeConsumptionTab === 'breakdown' ? (
                  <BarChart
                    data={data.consumption.costBreakdown.map((c) => ({ name: c.name, value: c.amount }))}
                    barKey="value"
                    labelKey="name"
                    color="#D6A84F"
                  />
                ) : (
                  <StatRow items={[
                    { label: '消费满意度', value: data.consumption.avgSatisfaction ? (data.consumption.avgSatisfaction / 5 * 100).toFixed(0) + '%' : '--', color: '#18A999' },
                    { label: '人均消费', value: data.consumption.avgSpend ? '¥' + data.consumption.avgSpend.toFixed(0) : '--', color: '#D6A84F' },
                    { label: '总营收', value: data.consumption.totalRevenue ? '¥' + (data.consumption.totalRevenue / 10000).toFixed(0) + '万' : '--', color: '#4F7CFF' },
                    { label: '消费记录数', value: data.consumption.recordCount ?? '--', color: '#818CF8' },
                  ]} />
                )}
              </div>
            </div>
          ) : null}
        </>
      ) : null}

      {/* ── 文本情感分析（来自情感分析API） ── */}
      {textReport ? (
        <div className="admin-card" style={{ marginTop: 16 }}>
          <div className="admin-card-header">
            <h3>文本级情感分析</h3>
            <span className="admin-table-date">{textReport.period.start_date} 至 {textReport.period.end_date} · 分析器: {textReport.analyzer}</span>
          </div>
          <div className="admin-card-body">
            <p style={{ fontSize: '0.9rem', lineHeight: 1.7, color: 'var(--text-mid)', marginBottom: 16 }}>{textReport.summary}</p>
            <StatRow items={[
              { label: '正向文本', value: textReport.counts.positive, color: '#18A999' },
              { label: '中性文本', value: textReport.counts.neutral, color: '#D6A84F' },
              { label: '负向文本', value: textReport.counts.negative, color: '#F3A6B3' },
              { label: '总分析量', value: textReport.total_messages, color: '#4F7CFF' },
            ]} />
            {textReport.focus_points && textReport.focus_points.length > 0 ? (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 6 }}>游客关注焦点</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {textReport.focus_points.map((fp: any, i: number) => (
                    <span key={i} className="admin-keyword-tag" style={{ color: '#4F7CFF' }}>
                      {typeof fp === 'string' ? fp : (fp.word || fp.keyword || '')}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* ── 痛点分析 + 好评差评案例 ── */}
      {data ? (
        <>
          <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
            <div className="admin-card">
              <div className="admin-card-header"><h3>高频痛点分析</h3></div>
              <div className="admin-card-body">
                <PainPointCard items={data.painPoints} />
              </div>
            </div>
            <div className="admin-card">
              <div className="admin-card-header"><h3>好评典型案例</h3></div>
              <div className="admin-card-body">
                <ExampleList items={data.feedback.positiveExamples} type="positive" />
              </div>
            </div>
          </div>

          <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
            <div className="admin-card">
              <div className="admin-card-header"><h3>差评典型案例</h3></div>
              <div className="admin-card-body">
                <ExampleList items={data.feedback.negativeExamples} type="negative" />
              </div>
            </div>
            <div className="admin-card">
              <div className="admin-card-header"><h3>改进建议</h3></div>
              <div className="admin-card-body">
                <SuggestionList items={data.suggestions} />
              </div>
            </div>
          </div>
        </>
      ) : null}

      {data ? (
        <div style={{ textAlign: 'right', marginTop: 16, fontSize: '0.7rem', color: 'var(--text-light)' }}>
          报告生成时间: {new Date(data.generatedAt).toLocaleString('zh-CN')}
        </div>
      ) : null}
    </div>
  );
}
