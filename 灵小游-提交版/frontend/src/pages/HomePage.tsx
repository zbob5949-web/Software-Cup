import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLingshanWeather, type LingshanWeather } from '../api/weather';
import { getDigitalHumanConfig, type DigitalHumanConfig } from '../api/digitalHuman';
import { getLocale, t } from '../lib/i18n';

/* ===== Icon primitives (extracted from inline SVG) ===== */
const SunIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </svg>
);

const ChatIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const CloudIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.5 19H9a7 7 0 1 1 6.7-9h.3a5 5 0 0 1 1.5 9Z" />
  </svg>
);

const RainIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.5 14H9a7 7 0 1 1 6.7-9h.3a5 5 0 0 1 1.5 9Z" />
    <path d="m8 18-1 2M12 18l-1 2M16 18l-1 2" />
  </svg>
);

const SnowIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.5 14H9a7 7 0 1 1 6.7-9h.3a5 5 0 0 1 1.5 9Z" />
    <path d="M8 18h.01M12 20h.01M16 18h.01" />
  </svg>
);

const FogIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 10h16M3 14h18M5 18h14" />
  </svg>
);

function WeatherIcon({ icon }: { icon?: string }) {
  const iconCode = Number(icon);

  if (iconCode >= 300 && iconCode < 400) return <RainIcon />;
  if (iconCode >= 400 && iconCode < 500) return <SnowIcon />;
  if (iconCode >= 500 && iconCode < 600) return <FogIcon />;
  if (iconCode >= 101 && iconCode <= 104) return <CloudIcon />;
  return <SunIcon />;
}

const ArrowRightIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

const MapPinIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

const CompassIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
  </svg>
);

const RouteIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 12 6 9 9 12 12 9 15 12 18 9 21 12" />
    <polyline points="3 18 6 15 9 18 12 15 15 18 18 15 21 18" />
  </svg>
);

const FeedbackIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

/* ===== Weather Card ===== */
function WeatherCard({ weather, locale }: { weather: LingshanWeather | null; locale: ReturnType<typeof getLocale> }) {
  const location = weather?.city || weather?.location || '无锡灵山';
  const text = weather?.weather || '加载中';
  const rawTemperature = weather?.temperature ?? weather?.temp ?? weather?.tempMax ?? '--';
  const temp = String(rawTemperature).match(/-?\d+(?:\.\d+)?/)?.[0] ?? '--';
  const feelsLike = weather?.feels_like ?? '';
  const humidity = weather?.humidity ?? '';
  const advice = weather?.advice || weather?.suggestion || '正在获取今日游览建议...';

  return (
    <article className="hp-weather">
      <div className="hp-weather-main">
        <div className="hp-weather-icon">
          <WeatherIcon icon={weather?.icon} />
        </div>
        <div className="hp-weather-temp">{temp}<span className="hp-weather-deg">°</span></div>
        <div className="hp-weather-info">
          <span className="hp-weather-loc">{location}</span>
          <span className="hp-weather-condition">{text}</span>
          {feelsLike && <span className="hp-weather-detail">体感 {feelsLike}</span>}
        </div>
      </div>
      <div className="hp-weather-bottom">
        <span className="hp-weather-advice" style={{ fontSize: 12, lineHeight: 1.3 }}>{advice}</span>
      </div>
    </article>
  );
}

/* ===== AI Digital Human Hero Card ===== */
function AiHeroCard({
  locale,
  onClick,
  frameSrc,
}: {
  locale: ReturnType<typeof getLocale>;
  onClick: () => void;
  frameSrc: string;
}) {
  return (
    <article
      className="hp-ai-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onClick(); }}
    >
      {/* Glow border ring */}
      <div className="hp-ai-card-glow" />

      {/* AI badge */}
      <span className="hp-ai-badge">AI 智能导览</span>

      {/* Live2D Digital Human */}
      <div className="hp-ai-video-wrap">
        <iframe
          src={frameSrc}
          className="hp-ai-live2d-frame"
          allow="autoplay; microphone"
          title="灵山数字人"
          style={{ width: '100%', height: '100%', border: 0, background: 'transparent' }}
        />
      </div>

      {/* Bottom info */}
      <div className="hp-ai-body">
        <div className="hp-ai-content">
          <h2 className="hp-ai-title">{t('home.aiEntryTitle', locale)}</h2>
          <p className="hp-ai-sub">{t('home.aiEntryNote', locale)}</p>
        </div>
        <div className="hp-ai-cta">
          <span className="hp-ai-cta-text">{t('home.aiEntryAction', locale)}</span>
          <span className="hp-ai-cta-arrow"><ArrowRightIcon /></span>
        </div>
      </div>
    </article>
  );
}

/* ===== Quick Chat Input Bar ===== */
function QuickInputBar({
  locale,
  onClick,
}: {
  locale: ReturnType<typeof getLocale>;
  onClick: () => void;
}) {
  return (
    <div
      className="hp-input-bar"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onClick(); }}
    >
      <div className="hp-input-bar-inner">
        <div className="hp-input-bar-icon">
          <ChatIcon />
        </div>
        <span className="hp-input-bar-text">{t('home.inputPlaceholder', locale)}</span>
        <div className="hp-input-bar-send">
          <ArrowRightIcon />
        </div>
      </div>
    </div>
  );
}

/* ===== Service Card ===== */
interface ServiceItem {
  key: string;
  icon: ReactNode;
  label: string;
  desc: string;
  to: string;
  accent: string;
}

function ServiceCard({ item, onClick }: { item: ServiceItem; onClick: () => void }) {
  return (
    <div
      className="hp-service-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onClick(); }}
      style={{ '--card-accent': item.accent } as React.CSSProperties}
    >
      <div className="hp-service-icon" style={{ color: item.accent }}>
        {item.icon}
      </div>
      <span className="hp-service-label">{item.label}</span>
      <span className="hp-service-desc">{item.desc}</span>
    </div>
  );
}

/* ===== Service Grid ===== */
function ServiceGrid({ locale }: { locale: ReturnType<typeof getLocale> }) {
  const navigate = useNavigate();

  const services: ServiceItem[] = [
    {
      key: 'spots',
      icon: <MapPinIcon />,
      label: t('home.services.spots', locale),
      desc: t('home.services.spotsDesc', locale),
      to: '/guide?tab=map',
      accent: '#18A999',
    },
    {
      key: 'guide',
      icon: <CompassIcon />,
      label: t('home.services.guide', locale),
      desc: t('home.services.guideDesc', locale),
      to: '/guide?tab=map',
      accent: '#4F7CFF',
    },
    {
      key: 'routes',
      icon: <RouteIcon />,
      label: t('home.services.routes', locale),
      desc: t('home.services.routesDesc', locale),
      to: '/guide?tab=routes',
      accent: '#D6A84F',
    },
    {
      key: 'feedback',
      icon: <FeedbackIcon />,
      label: t('home.services.feedback', locale),
      desc: t('home.services.feedbackDesc', locale),
      to: '/profile',
      accent: '#EF4444',
    },
    {
      key: 'tickets',
      icon: <span aria-hidden="true" style={{ fontSize: 22, fontWeight: 700 }}>¥</span>,
      label: '在线购票',
      desc: '预约入园与观光车票',
      to: '/tickets',
      accent: '#D97706',
    },  ];

  return (
    <section className="hp-services">
      <h3 className="hp-services-title">快捷服务</h3>
      <div className="hp-service-grid">
        {services.map((item) => (
          <ServiceCard
            key={item.key}
            item={item}
            onClick={() => navigate(item.to)}
          />
        ))}
      </div>
    </section>
  );
}

/* ===== Main Page ===== */
export function HomePage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const [weather, setWeather] = useState<LingshanWeather | null>(null);
  const [dhConfig, setDhConfig] = useState<DigitalHumanConfig | null>(null);
  const frameSrc = dhConfig?.model_dir
    ? `/live2d/index.html?hideUI=1&model=${encodeURIComponent(dhConfig.model_dir)}&api=${encodeURIComponent(window.location.origin)}`
    : `/live2d/index.html?hideUI=1&model=Haru&api=${encodeURIComponent(window.location.origin)}`;

  useEffect(() => {
    getLingshanWeather()
      .then(setWeather)
      .catch(() => {
        setWeather({
          location: '无锡灵山',
          weather: '天气暂不可用',
          temp: '--',
          suggestion: '天气暂不可用，仍可正常查看导览服务',
        });
      });
  }, []);

  useEffect(() => {
    const refreshTimer = window.setInterval(() => {
      getLingshanWeather()
        .then(setWeather)
        .catch(() => undefined);
    }, 10 * 60 * 1000);

    return () => window.clearInterval(refreshTimer);
  }, []);

  useEffect(() => {
    getDigitalHumanConfig()
      .then(setDhConfig)
      .catch(() => undefined);
  }, []);

  return (
    <div className="hp-page">
      {/* Welcome Header */}
      <header className="hp-header">
        <span className="hp-kicker">灵山景区 / LINGSHAN</span>
        <h1 className="hp-title">{t('home.welcome', locale)}</h1>
      </header>

      {/* Weather */}
      <WeatherCard weather={weather} locale={locale} />

      {/* AI Digital Human Hero */}
      <AiHeroCard
        locale={locale}
        frameSrc={frameSrc}
        onClick={() => navigate('/ai-chat')}
      />

      {/* Quick Input */}
      <QuickInputBar
        locale={locale}
        onClick={() => navigate('/ai-chat')}
      />

      {/* Service Grid */}
      <ServiceGrid locale={locale} />
    </div>
  );
}

