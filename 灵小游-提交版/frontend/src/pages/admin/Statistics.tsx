import { useEffect, useState } from 'react';
import { getSentimentReport, getStatistics, type DailyStat, type HotQuestion, type SatisfactionPoint, type SentimentPoint, type SourceRatio, type StatisticsKpi, type StatisticsPayload, type SentimentReport } from '../../api/admin';

function KpiCards({ items }: { items: StatisticsKpi[] }) {
  return (
    <div className="admin-stat-grid">
      {items.map((kpi) => (
        <div key={kpi.title} className="admin-stat-card">
          <div className="admin-stat-info">
            <span className="admin-stat-label">{kpi.title}</span>
            <span className="admin-stat-value">{kpi.value}</span>
            <span className={`admin-stat-change ${kpi.changeType}`}>{kpi.change}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function VerticalBarChart({ data, height = 200 }: { data: DailyStat[]; height?: number }) {
  const maxVal = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="admin-chart-container">
      <div className="admin-chart-y-labels">
        <span>{maxVal}</span>
        <span>{Math.round(maxVal / 2)}</span>
        <span>0</span>
      </div>
      <div className="admin-bar-chart" style={{ height }}>
        {data.map((item) => (
          <div key={item.date} className="admin-bar-item">
            <div className="admin-bar" style={{ height: `${(item.count / maxVal) * (height - 40)}px` }}>
              <span className="admin-bar-value">{item.count}</span>
            </div>
            <span className="admin-bar-label">{item.date}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HotQuestionsCard({ items }: { items: HotQuestion[] }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>热门问题 TOP10</h3>
      </div>
      <div className="admin-card-body" style={{ padding: '12px 20px' }}>
        {items.map((item) => (
          <div key={item.rank} className="admin-hot-item">
            <span className={`admin-hot-rank rank-${item.rank}`}>{item.rank}</span>
            <span className="admin-hot-question">{item.question}</span>
            <span className="admin-hot-count">{item.count}次</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SourceRatioChart({ items }: { items: SourceRatio[] }) {
  const total = items.reduce((sum, item) => sum + item.value, 0) || 1;

  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>回答来源分布</h3>
      </div>
      <div className="admin-card-body">
        <div className="admin-stacked-bar">
          {items.map((item) => (
            <div
              key={item.name}
              className="admin-stacked-bar-segment"
              style={{ width: `${(item.value / total) * 100}%`, background: item.color }}
              title={`${item.name}: ${item.value}%`}
            />
          ))}
        </div>
        <div className="admin-source-legend" style={{ marginTop: 12 }}>
          {items.map((item) => (
            <div key={item.name} className="admin-legend-item" style={{ marginBottom: 6 }}>
              <span className="admin-legend-dot" style={{ background: item.color }} />
              <span style={{ flex: 1 }}>{item.name}</span>
              <strong>{item.value}%</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SatisfactionTrendChart({ items }: { items: SatisfactionPoint[] }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>满意度趋势</h3>
      </div>
      <div className="admin-card-body">
        <div className="admin-line-chart">
          {items.map((pt, i) => {
            const xPct = items.length > 1 ? (i / (items.length - 1)) * 100 : 50;
            const yPct = 100 - pt.satisfaction * 0.8;
            return (
              <div key={pt.date} className="admin-line-dot" style={{ left: `${xPct}%`, top: `${yPct}%` }}>
                <span className="admin-line-dot-tooltip">
                  {pt.date}
                  <br />
                  {pt.satisfaction}%
                </span>
              </div>
            );
          })}
          {[0, 25, 50, 75, 100].map((v) => (
            <div key={v} className="admin-line-gridline" style={{ top: `${100 - v * 0.8}%` }}>
              <span className="admin-line-gridlabel">{v}%</span>
            </div>
          ))}
        </div>
        <div className="admin-line-xlabels" style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          {items.map((pt) => (
            <span key={pt.date} style={{ fontSize: '0.72rem', color: 'var(--text-light)' }}>
              {pt.date}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function SentimentStackedBar({ items }: { items: SentimentPoint[] }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>情感倾向趋势</h3>
      </div>
      <div className="admin-card-body">
        <div className="admin-sentiment-chart">
          {items.map((pt) => {
            const total = pt.positive + pt.neutral + pt.negative || 1;
            return (
              <div key={pt.date} className="admin-sentiment-col">
                <div className="admin-sentiment-bar-wrap">
                  <div className="admin-sentiment-bar" style={{ height: `${(pt.positive / total) * 100}%`, background: '#18A999' }} />
                  <div className="admin-sentiment-bar" style={{ height: `${(pt.neutral / total) * 100}%`, background: '#D6A84F' }} />
                  <div className="admin-sentiment-bar" style={{ height: `${(pt.negative / total) * 100}%`, background: '#F3A6B3' }} />
                </div>
                <span className="admin-sentiment-label">{pt.date}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function Statistics() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'report'>('dashboard');
  const [trendDays, setTrendDays] = useState<7 | 30>(7);
  const [payload, setPayload] = useState<StatisticsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeKeywordTab, setActiveKeywordTab] = useState<'positive' | 'negative'>('positive');
  const [report, setReport] = useState<SentimentReport | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);

    getStatistics(trendDays)
      .then((data) => {
        if (!active) return;
        if (!data) {
          setError('统计数据加载失败');
          return;
        }
        setPayload({
          kpis: data.kpis ?? [],
          trend: data.trend ?? [],
          hotQuestions: data.hotQuestions ?? [],
          sourceRatio: data.sourceRatio ?? [],
          satisfactionTrend: data.satisfactionTrend ?? [],
          sentimentTrend: data.sentimentTrend ?? [],
          sentimentSummary: data.sentimentSummary ?? {
            totalAnalyzed: 0,
            positiveRatio: 0,
            neutralRatio: 0,
            negativeRatio: 0,
            avgSentimentScore: 0,
            positiveTrend: '--',
            trend: 'flat' as const,
          },
          sentimentKeywords: data.sentimentKeywords ?? { positive: [], negative: [] },
        });
        setError('');
      })
      .catch(() => {
        if (!active) return;
        setError('统计数据加载失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [trendDays]);

  useEffect(() => {
    if (activeTab !== 'report') return undefined;
    let active = true;
    getSentimentReport({ use_ai: false }).then((data) => { if (active && data) setReport(data); else if (active) setReport(null); }).catch(() => { if (active) setReport(null); });
    return () => { active = false; };
  }, [activeTab]);
  const keywords =
    activeKeywordTab === 'positive'
      ? payload?.sentimentKeywords.positive ?? []
      : payload?.sentimentKeywords.negative ?? [];

  return (
    <div className="admin-page-statistics">
      <div className="admin-page-header" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 style={{ margin: 0 }}>数据统计大屏</h2>
          <div className="admin-trend-tabs" style={{ marginLeft: 16 }}>
            <button className={`admin-trend-tab${activeTab === 'dashboard' ? ' active' : ''}`} onClick={() => setActiveTab('dashboard')}>
              数据大屏
            </button>
            <button className={`admin-trend-tab${activeTab === 'report' ? ' active' : ''}`} onClick={() => setActiveTab('report')}>
              感受度报告
            </button>
          </div>
        </div>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}
      {loading ? <div className="admin-table-empty">正在加载统计数据...</div> : null}

      {payload && activeTab === 'dashboard' ? (
        <>
          <KpiCards items={payload.kpis} />

          <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
            <div className="admin-card">
              <div className="admin-card-header">
                <h3>对话趋势</h3>
                <div className="admin-trend-tabs">
                  <button className={`admin-trend-tab${trendDays === 7 ? ' active' : ''}`} onClick={() => setTrendDays(7)}>
                    近7天
                  </button>
                  <button className={`admin-trend-tab${trendDays === 30 ? ' active' : ''}`} onClick={() => setTrendDays(30)}>
                    近30天
                  </button>
                </div>
              </div>
              <div className="admin-card-body">
                <VerticalBarChart data={payload.trend} />
              </div>
            </div>
            <HotQuestionsCard items={payload.hotQuestions} />
          </div>

          <div className="admin-dashboard-grid" style={{ marginTop: 16 }}>
            <SourceRatioChart items={payload.sourceRatio} />
            <SatisfactionTrendChart items={payload.satisfactionTrend} />
          </div>
        </>
      ) : null}

      {activeTab === 'report' && report ? (
        <div className="admin-card" style={{ marginBottom: 16 }}>
          <div className="admin-card-header"><h3>文本情感分析报告</h3><span className="admin-table-date">{report.period.start_date} 至 {report.period.end_date} · {report.analyzer}</span></div>
          <div className="admin-card-body">
            <p className="admin-report-summary">{report.summary}</p>
            <div className="admin-sentiment-summary-grid">
              <div className="admin-feedback-stat-card"><span className="admin-feedback-stat-value" style={{ color: '#18A999' }}>{report.counts.positive}</span><span className="admin-feedback-stat-label">正向文本</span></div>
              <div className="admin-feedback-stat-card"><span className="admin-feedback-stat-value" style={{ color: '#D6A84F' }}>{report.counts.neutral}</span><span className="admin-feedback-stat-label">中性文本</span></div>
              <div className="admin-feedback-stat-card"><span className="admin-feedback-stat-value" style={{ color: '#F3A6B3' }}>{report.counts.negative}</span><span className="admin-feedback-stat-label">负向文本</span></div>
            </div>
            <div className="admin-report-suggestions">{report.suggestions.map((item) => <div key={item}>· {item}</div>)}</div>
          </div>
        </div>
      ) : null}
      {payload && activeTab === 'report' ? (
        <>
          <div className="admin-sentiment-summary-grid">
            <div className="admin-feedback-stat-card">
              <span className="admin-feedback-stat-value" style={{ color: '#18A999' }}>
                {payload.sentimentSummary.positiveRatio}%
              </span>
              <span className="admin-feedback-stat-label">正面评价比例</span>
            </div>
            <div className="admin-feedback-stat-card">
              <span className="admin-feedback-stat-value" style={{ color: '#D6A84F' }}>
                {payload.sentimentSummary.neutralRatio}%
              </span>
              <span className="admin-feedback-stat-label">中性评价比例</span>
            </div>
            <div className="admin-feedback-stat-card">
              <span className="admin-feedback-stat-value" style={{ color: '#F3A6B3' }}>
                {payload.sentimentSummary.negativeRatio}%
              </span>
              <span className="admin-feedback-stat-label">负面评价比例</span>
            </div>
            <div className="admin-feedback-stat-card">
              <span className="admin-feedback-stat-value" style={{ color: '#4F7CFF' }}>
                {payload.sentimentSummary.avgSentimentScore.toFixed(2)}
              </span>
              <span className="admin-feedback-stat-label">平均情感得分</span>
            </div>
          </div>

          <div className="admin-statistics-grid" style={{ marginTop: 16 }}>
            <SentimentStackedBar items={payload.sentimentTrend} />

            <div className="admin-card">
              <div className="admin-card-header">
                <h3>情感关键词提取</h3>
                <div className="admin-trend-tabs">
                  <button
                    className={`admin-trend-tab${activeKeywordTab === 'positive' ? ' active' : ''}`}
                    onClick={() => setActiveKeywordTab('positive')}
                  >
                    正面关键词
                  </button>
                  <button
                    className={`admin-trend-tab${activeKeywordTab === 'negative' ? ' active' : ''}`}
                    onClick={() => setActiveKeywordTab('negative')}
                  >
                    负面关键词
                  </button>
                </div>
              </div>
              <div className="admin-card-body">
                <div className="admin-keyword-cloud">
                  {keywords.map((kw, i) => {
                    const sizes = ['0.85rem', '1rem', '1.15rem', '1.3rem', '1.45rem'];
                    const idx = i % sizes.length;
                    return (
                      <span
                        key={kw}
                        className="admin-keyword-tag"
                        style={{
                          fontSize: sizes[idx],
                          color: activeKeywordTab === 'positive' ? '#18A999' : '#F3A6B3',
                        }}
                      >
                        {kw}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
