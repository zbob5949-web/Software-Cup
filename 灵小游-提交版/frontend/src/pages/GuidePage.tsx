import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getRoutes, getRecommendedRoutes, type Route } from '../api/route';
import { getSpotDetail, getSpotList, type Spot } from '../api/spot';
import { addFavorite, removeFavorite, getFavorites, addRouteFavorite, removeRouteFavorite, getRouteFavorites } from '../api/favorite';
import { getLocale, t } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { LeafletMap, type MapSpot, type MapRoute } from '../components/LeafletMap';
import { sendDigitalHumanChat } from '../api/digitalHuman';
import { revokeAudioUrl, textToSpeech } from '../api/tts';
import request from '../api/request';

type GuideTab = 'map' | 'routes';

type RouteCard = {
  id?: number;
  icon: string;
  title: string;
  description: string;
  tag: string;
  askPrompt: string;
};

const scenicSpotPresets = [
  { id: 11, nameZh: '灵山大佛', brief: '景区核心地标，适合第一次到访游客。', askPrompt: '请介绍灵山大佛的历史和看点' },
  { id: 6, nameZh: '九龙灌浴', brief: '热门演艺点位，适合安排固定场次观看。', askPrompt: '请介绍九龙灌浴的演出时间和玩法' },
  { id: 14, nameZh: '梵宫', brief: '文化体验重点区域，适合深度参观。', askPrompt: '请介绍梵宫的参观重点' },
  { id: 15, nameZh: '五印坛城', brief: '适合喜欢建筑与宗教文化的游客。', askPrompt: '请介绍五印坛城和值得看的内容' },
  { id: 8, nameZh: '阿育王柱', brief: '适合串联文化路线进行打卡。', askPrompt: '请介绍阿育王柱的文化背景' },
  { id: 9, nameZh: '降魔浮雕', brief: '适合与大佛片区一同浏览。', askPrompt: '请介绍降魔浮雕的内容' },
];

const fallbackRoutes: RouteCard[] = [
  { icon: '半', title: '经典半日游', description: '覆盖灵山主要景点，适合首次游览与时间有限的游客。', tag: '推荐', askPrompt: '请为我讲解灵山经典半日游路线' },
  { icon: '深', title: '一日深度游', description: '适合想完整体验文化与建筑内容的游客。', tag: '深度', askPrompt: '请为我讲解灵山一日深度游路线' },
  { icon: '亲', title: '亲子轻松游', description: '节奏舒缓，适合老人和小孩共同出行。', tag: '亲子', askPrompt: '请推荐适合老人和孩子的灵山路线' },
  { icon: '文', title: '文化体验游', description: '重点围绕佛教文化、梵宫与讲解类内容展开。', tag: '文化', askPrompt: '请推荐灵山文化体验路线' },
];

function buildRouteCardsFromApi(items: Route[]): RouteCard[] {
  if (!items.length) return fallbackRoutes;
  return items.slice(0, 5).map((item, index) => ({
    id: item.id,
    icon: ['荐', '游', '文', '轻', '景'][index] ?? '游',
    title: item.name || `推荐路线 ${index + 1}`,
    description: [item.duration, item.difficulty].filter(Boolean).join(' · ') || '适合灵山景区导览使用',
    tag: item.difficulty || '推荐',
    askPrompt: `请讲解一下"${item.name || `推荐路线 ${index + 1}`}"这条灵山游览路线`,
  }));
}

export function GuidePage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const { isAuthenticated, identityType } = useAuth();
  const isFormalUser = isAuthenticated && identityType !== 'guest';
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<GuideTab>('map');
  const [selectedSpotId, setSelectedSpotId] = useState<number>(scenicSpotPresets[0].id);
  const [selectedMapSpot, setSelectedMapSpot] = useState<MapSpot | null>(null);
  const [navigationNotice, setNavigationNotice] = useState('');
  const navigationAudioRef = useRef<HTMLAudioElement | null>(null);
  const [navRoute, setNavRoute] = useState<MapRoute | null>(null);
  const [navStepIndex, setNavStepIndex] = useState(-1);  // -1 = 未开始
  const [navTargetSpot, setNavTargetSpot] = useState<MapSpot | null>(null);
  const navAbortRef = useRef(false);
  const [spotDetail, setSpotDetail] = useState<Spot | null>(null);
  const [spotLoading, setSpotLoading] = useState(false);
  const [spotError, setSpotError] = useState('');
  const [routeCards, setRouteCards] = useState<RouteCard[]>(fallbackRoutes);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState('');
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());
  const [routeFavoriteIds, setRouteFavoriteIds] = useState<Set<number>>(new Set());
  const [favToggling, setFavToggling] = useState(false);
  const [mapRoutes, setMapRoutes] = useState<MapRoute[]>([]);
  const [activeRouteId, setActiveRouteId] = useState<number | null>(null);

  // 离开页面立刻停止所有导航音频
  useEffect(() => {
    return () => {
      navAbortRef.current = true;
      navigationAudioRef.current?.pause();
      navigationAudioRef.current = null;
      window.speechSynthesis?.cancel();
    };
  }, []);

  useEffect(() => {
    const spot = searchParams.get('spot');
    if (spot && /^\\d+$/.test(spot)) setSelectedSpotId(Number(spot));
  }, [searchParams]);

  useEffect(() => {
    const nextTab = searchParams.get('tab');
    if (nextTab === 'routes' || nextTab === 'map') setTab(nextTab);
  }, [searchParams]);

  const selectedPreset = useMemo(
    () => scenicSpotPresets.find((item) => item.id === selectedSpotId) ?? scenicSpotPresets[0],
    [selectedSpotId],
  );

  // Load spot detail
  useEffect(() => {
    let active = true;
    setSpotLoading(true);
    setSpotError('');

    getSpotDetail(selectedSpotId)
      .then((data) => { if (active) setSpotDetail(data); })
      .catch(async () => {
        try {
          const spots = await getSpotList();
          const local = spots.find((spot) => spot.id === selectedSpotId || spot.name.includes(selectedMapSpot?.name ?? selectedPreset.nameZh) || (selectedMapSpot?.name ?? selectedPreset.nameZh).includes(spot.name));
          if (active && local) { setSpotDetail(local); setSpotError(''); return; }
        } catch { /* use local fallback */ }
        if (active) {
          setSpotDetail(selectedMapSpot ? { id: selectedMapSpot.id, name: selectedMapSpot.name, category: selectedMapSpot.category, description: selectedMapSpot.description } : { id: selectedSpotId, name: selectedPreset.nameZh, category: '', description: selectedPreset.brief });
          setSpotError('');
        }
      })
      .finally(() => { if (active) setSpotLoading(false); });

    return () => { active = false; };
  }, [selectedSpotId, selectedMapSpot]);

  // Load routes
  useEffect(() => {
    let active = true;
    setRouteLoading(true);
    setRouteError('');

    const load = async () => {
      try {
        // Load the complete route list first. One failed recommendation must not hide all routes.
        const all = await getRoutes();
        if (all.length > 0) {
          if (active) { setRouteCards(buildRouteCardsFromApi(all)); setRouteError(''); }
          return;
        }
        const results = await Promise.allSettled([
          getRecommendedRoutes({ interest: '文化', hours: 4 }),
          getRecommendedRoutes({ interest: '亲子', hours: 3 }),
          getRecommendedRoutes({ interest: '风光', hours: 5 }),
        ]);
        const merged = results.flatMap((result) => result.status === 'fulfilled' ? result.value : []);
        if (active) {
          setRouteCards(buildRouteCardsFromApi(merged));
          setRouteError(merged.length ? '' : '');
        }
      } catch {
        const results = await Promise.allSettled([
          getRecommendedRoutes({ interest: '文化', hours: 4 }),
          getRecommendedRoutes({ interest: '亲子', hours: 3 }),
          getRecommendedRoutes({ interest: '风光', hours: 5 }),
        ]);
        const merged = results.flatMap((result) => result.status === 'fulfilled' ? result.value : []);
        if (active) {
          setRouteCards(buildRouteCardsFromApi(merged));
          setRouteError(merged.length ? '' : '');
        }
      } finally {
        if (active) setRouteLoading(false);
      }
    };
    load();
    return () => { active = false; };
  }, []);

  // Load favorites
  const refreshFavorites = useCallback(() => {
    if (!isAuthenticated) { setFavoriteIds(new Set()); setRouteFavoriteIds(new Set()); return; }
    getFavorites()
      .then((items) => setFavoriteIds(new Set(items.map((f) => f.id))))
      .catch(() => {});
    getRouteFavorites()
      .then((items) => setRouteFavoriteIds(new Set(items.map((f) => f.id))))
      .catch(() => {});
  }, [isAuthenticated]);

  useEffect(() => { refreshFavorites(); }, [refreshFavorites]);

  const handleToggleFavorite = useCallback(async (spotId: number) => {
    if (!isFormalUser) { navigate('/login'); return; }
    setFavToggling(true);
    try {
      if (favoriteIds.has(spotId)) {
        await removeFavorite(spotId);
        setFavoriteIds((prev) => { const next = new Set(prev); next.delete(spotId); return next; });
      } else {
        await addFavorite(spotId);
        setFavoriteIds((prev) => new Set(prev).add(spotId));
      }
    } catch { /* ignore */ }
    setFavToggling(false);
  }, [isFormalUser, favoriteIds, navigate]);

  const handleToggleRouteFavorite = useCallback(async (routeId: number) => {
    if (!isFormalUser) { navigate('/login'); return; }
    try {
      if (routeFavoriteIds.has(routeId)) {
        await removeRouteFavorite(routeId);
        setRouteFavoriteIds((prev) => { const next = new Set(prev); next.delete(routeId); return next; });
      } else {
        await addRouteFavorite(routeId);
        setRouteFavoriteIds((prev) => new Set(prev).add(routeId));
      }
    } catch { /* ignore */ }
  }, [isFormalUser, routeFavoriteIds, navigate]);

  function askDigitalHuman(prompt: string) {
    navigate(`/ai-chat?ask=${encodeURIComponent(prompt)}`);
  }

  /** 播报单段导航，返回 true 表示成功播完 */
  const speakStep = useCallback(async (step: { instruction: string }, spotName: string, current: number, total: number): Promise<boolean> => {
    const isFirst = current === 0;
    const isLast = current === total - 1;
    let prompt: string;
    if (isFirst) {
      prompt = `开始导航前往${spotName}，全程${total}段。${step.instruction}`;
    } else if (isLast) {
      prompt = `最后一段，${step.instruction}，即将到达${spotName}。`;
    } else {
      prompt = `下一段，${step.instruction}`;
    }
    setNavigationNotice(prompt);
    try {
      const reply = (await sendDigitalHumanChat('', prompt)).reply || prompt;
      const tts = await textToSpeech(reply);
      navigationAudioRef.current?.pause();
      const audio = new Audio(tts.url);
      navigationAudioRef.current = audio;
      return new Promise((resolve) => {
        audio.onended = () => { revokeAudioUrl(tts.url); navigationAudioRef.current = null; resolve(true); };
        audio.onerror = () => { revokeAudioUrl(tts.url); navigationAudioRef.current = null; resolve(false); };
        void audio.play();
      });
    } catch {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(prompt));
      }
      return true;
    }
  }, []);

  /** 开始/重启顺序导航：遍历 route.steps，逐一播报 */
  const startSequentialNav = useCallback(async (spot: MapSpot, route: MapRoute, startIndex = 0) => {
    navAbortRef.current = false;
    setNavRoute(route);
    setNavTargetSpot(spot);
    setNavStepIndex(startIndex);

    const steps = route.steps;
    if (!steps.length) {
      setNavigationNotice(`已为您规划前往${spot.name}的路线，请按地图指引前进。`);
      setNavStepIndex(-1);
      return;
    }

    for (let i = startIndex; i < steps.length; i++) {
      if (navAbortRef.current) break;
      setNavStepIndex(i);
      await speakStep(steps[i], spot.name, i, steps.length);
    }
    if (!navAbortRef.current) {
      setNavigationNotice(`🎉 您已到达${spot.name}，导航结束。`);
      setNavStepIndex(-1);
      setNavRoute(null);
      setNavTargetSpot(null);
    }
  }, [speakStep]);

  /** 手动跳下一段 */
  const handleNextStep = useCallback(() => {
    if (!navRoute || navStepIndex < 0) return;
    const next = navStepIndex + 1;
    const steps = navRoute.steps;
    if (next >= steps.length) {
      setNavigationNotice(`🎉 您已到达${navTargetSpot?.name ?? '目的地'}，导航结束。`);
      setNavStepIndex(-1);
      setNavRoute(null);
      setNavTargetSpot(null);
      navAbortRef.current = true;
      navigationAudioRef.current?.pause();
      return;
    }
    // 跳到下一段，但在 startSequentialNav 里会覆盖，所以直接调
    navAbortRef.current = true;
    if (navTargetSpot) void startSequentialNav(navTargetSpot, navRoute, next);
  }, [navRoute, navStepIndex, navTargetSpot, startSequentialNav]);

  /** 取消导航 */
  const handleCancelNav = useCallback(() => {
    navAbortRef.current = true;
    navigationAudioRef.current?.pause();
    navigationAudioRef.current = null;
    setNavStepIndex(-1);
    setNavRoute(null);
    setNavTargetSpot(null);
    setNavigationNotice('');
  }, []);

  /** 地图上点选景点 → 触发导航起点 */
  const speakNavigation = useCallback(async (spot: MapSpot, route: MapRoute) => {
    handleCancelNav();
    await new Promise((r) => setTimeout(r, 200));
    navAbortRef.current = false;
    void startSequentialNav(spot, route, 0);
  }, [handleCancelNav, startSequentialNav]);

  /** 拖拽模拟位置 → 只更新路线，不触发语音导航 */
  const handleNavigationUpdate = useCallback((_spot: MapSpot, _route: MapRoute, _position: [number, number]) => {
    // 拖拽模拟点位移动时只更新地图路线显示，不自动语音播报
    // 用户需要点击"语音导航"按钮才会开始语音播报
  }, []);

  // Handle spot selection from the real map
  const handleMapSpotSelect = useCallback((spot: MapSpot) => {
    // Keep the complete map object so unknown/supplemental points never fall back to the first preset.
    setSelectedMapSpot(spot);
    setSelectedSpotId(spot.id);
    setSpotDetail({ id: spot.id, name: spot.name, category: spot.category, description: spot.description });
  }, []);

  // Handle route selection from the real map
  const handleMapRouteSelect = useCallback((route: MapRoute) => {
    setActiveRouteId((prev) => prev === route.id ? null : route.id);
  }, []);

  const handleMapRoutesLoaded = useCallback((routes: MapRoute[]) => {
    setMapRoutes(routes);
  }, []);

  const spotName = selectedMapSpot?.name || spotDetail?.name || selectedPreset.nameZh;
  const spotCategory = spotDetail?.category || selectedMapSpot?.category || '';
  const spotDescription = spotDetail?.description || selectedMapSpot?.description || selectedPreset.brief;
  const isFavorited = favoriteIds.has(selectedSpotId);

  /** 点击语音导航按钮：请求实时路线 → 启动顺序导航 */
  const handleVoiceNav = useCallback(async () => {
    const target = selectedMapSpot ?? { id: selectedSpotId, name: spotName, category: spotCategory, description: spotDescription, lat: 0, lng: 0 };
    try {
      let lat = 31.4258, lng = 120.103;
      try {
        const saved = window.localStorage.getItem('lingshanGuideCurrentLocation');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.latitude && parsed.longitude) { lat = parsed.latitude; lng = parsed.longitude; }
        }
      } catch { /* use default */ }
      const resp = await request.post('/api/map/route/live', {
        latitude: lat, longitude: lng, target_spot_id: target.id, target_name: target.name,
      });
      const body = resp.data as Record<string, unknown>;
      const feature = (body.code !== undefined && body.data ? body.data : body) as { properties?: { steps?: MapRoute['steps'] } };
      const props = feature.properties ?? {};
      const route: MapRoute = {
        id: -target.id, name: `前往${target.name}`, duration: '实时导航', difficulty: '实时导航',
        color: '#0ea5e9', coordinates: [], steps: props.steps ?? [],
        total_distance_m: 0, walking_min: 0,
      };
      void speakNavigation(target, route);
    } catch {
      setNavigationNotice('路线请求失败，请先在地图上点击目标景点。');
    }
  }, [selectedMapSpot, selectedSpotId, spotName, spotCategory, spotDescription, speakNavigation]);

  return (
    <div className="guide-page">
      <header className="guide-header">
        <h1>灵山智慧导览</h1>
        <p>{t('guide.pageDesc', locale)}</p>
      </header>

      <div className="guide-tabs" role="tablist">
        <button className={`guide-tab${tab === 'map' ? ' active' : ''}`} onClick={() => setTab('map')} type="button" role="tab" aria-selected={tab === 'map'}>{t('guide.tabMap', locale)}</button>
        <button className={`guide-tab${tab === 'routes' ? ' active' : ''}`} onClick={() => setTab('routes')} type="button" role="tab" aria-selected={tab === 'routes'}>{t('guide.tabRoutes', locale)}</button>
      </div>

      {tab === 'map' ? (
        <div className="guide-tab-content">
          {/* ── 真实地图 ── */}
          <div className="guide-map-area">
            <div className="guide-map-header">
              <h3>景区地图</h3>
              <span className="guide-gps-badge">43 个景点</span>
            </div>
            <div className="guide-map-real" style={{ height: 320, borderRadius: 10, overflow: 'hidden' }}>
              <LeafletMap
                selectedSpotId={selectedSpotId}
                onSpotSelect={handleMapSpotSelect}
                onRouteSelect={handleMapRouteSelect}
                onNavigationStart={(spot, route) => void speakNavigation(spot, route)}
                onNavigationUpdate={handleNavigationUpdate}
                onRoutesLoaded={handleMapRoutesLoaded}
                activeRouteId={activeRouteId}
              />
            </div>
            <p className="guide-map-hint">点击地图上的景点标记查看详情，下方路线可点击高亮</p>
          </div>

          {/* ── 路线图例（地图外）── */}
          {mapRoutes.length > 0 && (
            <div className="guide-route-legend">
              {mapRoutes.map((r, i) => (
                <div
                  key={r.id}
                  className={`guide-route-legend-item${activeRouteId === r.id ? ' active' : ''}`}
                  onClick={() => handleMapRouteSelect(r)}
                >
                  <span className="guide-route-legend-color" style={{ background: r.color || ['#3385ff','#f76b1c','#10b563','#9b59b6'][i % 4] }} />
                  <span className="guide-route-legend-name">{r.name}</span>
                  <span className="guide-route-legend-dur">{r.duration}</span>
                </div>
              ))}
            </div>
          )}

          {/* ── 景点详情 ── */}
          <div className="guide-spot-detail">
            <div className="guide-spot-detail-header">
              <h4>{spotName}</h4>
              {(
                <button
                  type="button"
                  className={`guide-fav-btn${isFavorited ? ' favorited' : ''}`}
                  onClick={() => handleToggleFavorite(selectedSpotId)}
                  disabled={favToggling}
                  title={isFavorited ? '取消收藏' : '收藏景点'}
                >
                  {isFavorited ? '★' : '☆'}
                </button>
              )}
            </div>
            <p>{spotDetail?.category ? `${spotDetail.category} · ` : ''}预计游览 {spotDetail?.duration || '20-30'} 分钟</p>
            <p style={{ marginBottom: 12 }}>{spotDescription}</p>
            {spotLoading ? <div className="hint">正在加载景点详情...</div> : null}
            {spotError ? <div className="hint hint-error">{spotError}</div> : null}
            {spotDetail?.open_time ? <p><strong>开放时间：</strong>{spotDetail.open_time}</p> : null}
            {spotDetail?.tips ? <p><strong>游览贴士：</strong>{spotDetail.tips}</p> : null}
            {navigationNotice ? (
              <div className="guide-navigation-notice">
                {navRoute && navStepIndex >= 0 ? (
                  <div className="guide-nav-progress">
                    <span className="guide-nav-step-badge">{navStepIndex + 1}/{navRoute.steps.length}</span>
                    <span>{navRoute.steps[navStepIndex]?.instruction || navigationNotice}</span>
                  </div>
                ) : (
                  <span>{navigationNotice}</span>
                )}
                <div className="guide-nav-controls">
                  {navRoute && navStepIndex >= 0 ? (
                    <>
                      <button type="button" className="guide-nav-btn" onClick={handleNextStep}>
                        {navStepIndex + 1 < navRoute.steps.length ? '▶ 下一段' : '✅ 完成'}
                      </button>
                      <button type="button" className="guide-nav-btn cancel" onClick={handleCancelNav}>✕ 取消</button>
                    </>
                  ) : null}
                </div>
              </div>
            ) : null}            <div className="guide-spot-actions">
              <button type="button" className="guide-spot-btn" onClick={handleVoiceNav}>语音导航</button>
              <button type="button" className="guide-spot-btn primary" onClick={() => askDigitalHuman(selectedMapSpot ? `请介绍${selectedMapSpot.name}的历史和看点` : selectedPreset.askPrompt)}>AI 讲解</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="guide-tab-content">
          <div className="guide-routes-intro">
            <h3>{t('guide.routeSmartTitle', locale)}</h3>
            <p>{t('guide.routeSmartDesc', locale)}</p>
            {routeLoading ? <div className="hint">正在加载路线推荐...</div> : null}
            {routeError ? <div className="hint hint-error">{routeError}</div> : null}
          </div>
          {routeCards.map((route) => (
            <div key={`${route.title}-${route.tag}`} className="guide-route-card">
              <div className="guide-route-card-top">
                <span className="guide-route-icon">{route.icon}</span>
                <div className="guide-route-info">
                  <h4>{route.title}</h4>
                  <span className="guide-route-tag">{route.tag}</span>
                </div>
                {route.id !== undefined && (
                  <button
                    type="button"
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      fontSize: 20, color: routeFavoriteIds.has(route.id) ? '#f59e0b' : '#ccc',
                      padding: '0 8px', marginLeft: 'auto',
                    }}
                    onClick={(e) => { e.stopPropagation(); handleToggleRouteFavorite(route.id!); }}
                    title={routeFavoriteIds.has(route.id) ? '取消收藏路线' : '收藏路线'}
                  >
                    {routeFavoriteIds.has(route.id) ? '★' : '☆'}
                  </button>
                )}
              </div>
              <p>{route.description}</p>
              <button type="button" className="guide-route-detail-btn" onClick={() => askDigitalHuman(route.askPrompt)}>查看详情并让数字人讲解</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

