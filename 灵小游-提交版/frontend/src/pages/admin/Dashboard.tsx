import { useEffect, useState } from 'react';
import {
  getAdminDashboard,
  type AdminStatCard,
  type DashboardWeather,
  type HotQuestion,
  type SatisfactionSummary,
} from '../../api/admin';

function StatCards({ stats }: { stats: AdminStatCard[] }) {
  return (
    <div className="admin-stat-grid">
      {stats.map((stat) => (
        <div key={stat.title} className="admin-stat-card">
          <div className="admin-stat-info">
            <span className="admin-stat-label">{stat.title}</span>
            <span className="admin-stat-value">{stat.value}</span>
            <span className={`admin-stat-change ${stat.changeType}`}>{stat.change}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function HotQuestions({ items }: { items: HotQuestion[] }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>热门问题 TOP5</h3>
      </div>
      <div className="admin-card-body">
        {items.map((item) => (
          <div key={item.rank} className="admin-hot-item">
            <span className={`admin-hot-rank rank-${item.rank}`}>{item.rank}</span>
            <span className="admin-hot-question">{item.question}</span>
            <span className="admin-hot-count">{item.count}次</span>
          </div>
        ))}
        {items.length === 0 ? <div className="admin-table-empty">暂无会话数据</div> : null}
      </div>
    </div>
  );
}

function SatisfactionChart({ data }: { data: SatisfactionSummary }) {
  const total = data.positive + data.neutral + data.negative || 1;
  const positiveDeg = (data.positive / total) * 360;
  const neutralDeg = (data.neutral / total) * 360;

  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>游客满意度</h3>
      </div>
      <div className="admin-card-body admin-satisfaction-body">
        <div className="admin-donut-chart">
          <svg width="140" height="140" viewBox="0 0 36 36">
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#E8ECF8"
              strokeWidth="3"
            />
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#18A999"
              strokeWidth="3"
              strokeDasharray={`${(positiveDeg / 360) * 100} ${100 - (positiveDeg / 360) * 100}`}
            />
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#F0C48A"
              strokeWidth="3"
              strokeDasharray={`${(neutralDeg / 360) * 100} ${100 - (neutralDeg / 360) * 100}`}
              strokeDashoffset={`${-(100 - (positiveDeg / 360) * 100)}`}
            />
          </svg>
          <div className="admin-donut-label">{data.positive}%</div>
        </div>
        <div className="admin-satisfaction-legend">
          <div className="admin-legend-item">
            <span className="admin-legend-dot" style={{ background: '#18A999' }} />
            <span>好评 ({data.positive}%)</span>
          </div>
          <div className="admin-legend-item">
            <span className="admin-legend-dot" style={{ background: '#F0C48A' }} />
            <span>中评 ({data.neutral}%)</span>
          </div>
          <div className="admin-legend-item">
            <span className="admin-legend-dot" style={{ background: '#F3A6B3' }} />
            <span>差评 ({data.negative}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function WeatherWidget({ weather }: { weather: DashboardWeather }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <h3>实时天气</h3>
      </div>
      <div className="admin-card-body admin-weather-body">
        <div className="admin-weather-top">
          <div className="admin-weather-now">
            <span className="admin-weather-temp">{weather.temp}</span>
            <span className="admin-weather-desc">{weather.weather}</span>
          </div>
        </div>
        <div className="admin-weather-details">
          <div className="admin-weather-detail-item">
            <span>位置</span>
            <span>{weather.location}</span>
          </div>
          <div className="admin-weather-detail-item">
            <span>湿度</span>
            <span>{weather.humidity}</span>
          </div>
          <div className="admin-weather-detail-item">
            <span>体感</span>
            <span>{weather.feels_like}</span>
          </div>
          <div className="admin-weather-detail-item">
            <span>建议</span>
            <span>{weather.advice}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Dashboard() {
  const [stats, setStats] = useState<AdminStatCard[]>([]);
  const [hotQuestions, setHotQuestions] = useState<HotQuestion[]>([]);
  const [satisfaction, setSatisfaction] = useState<SatisfactionSummary>({ positive: 0, neutral: 0, negative: 0 });
  const [weather, setWeather] = useState<DashboardWeather>({
    location: '无锡灵山',
    weather: '加载中',
    temp: '--',
    humidity: '--',
    feels_like: '--',
    advice: '正在获取天气数据',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    getAdminDashboard()
      .then((data) => {
        if (!active) return;
        if (!data) {
          setError('管理看板数据加载失败');
          return;
        }
        setStats(data.stats ?? []);
        setHotQuestions(data.hotQuestions ?? []);
        setSatisfaction(data.satisfaction ?? { positive: 0, neutral: 0, negative: 0 });
        setWeather(data.weather ?? {
          location: '无锡灵山',
          weather: '--',
          temp: '--',
          humidity: '--',
          feels_like: '--',
          advice: '天气数据获取失败',
        });
        setError('');
      })
      .catch(() => {
        if (!active) return;
        setError('管理看板数据加载失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="admin-page-dashboard">
      <div className="admin-page-header">
        <h2>首页概览</h2>
        <p className="admin-page-subtitle">灵山景区 AI 数字人管理后台数据总览</p>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}
      {loading ? <div className="admin-table-empty">正在加载数据...</div> : null}

      <StatCards stats={stats} />

      <div className="admin-dashboard-grid">
        <HotQuestions items={hotQuestions} />
        <SatisfactionChart data={satisfaction} />
        <WeatherWidget weather={weather} />
      </div>
    </div>
  );
}
