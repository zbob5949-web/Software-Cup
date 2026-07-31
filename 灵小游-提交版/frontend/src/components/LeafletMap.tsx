import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import request from '../api/request';

export interface MapSpot {
  id: number;
  name: string;
  category: string;
  description: string;
  lat: number;
  lng: number;
}

export interface MapRoute {
  id: number;
  name: string;
  duration: string;
  difficulty: string;
  color: string;
  coordinates: [number, number][];
  steps: { from_name: string; to_name: string; instruction: string; distance_m: number }[];
  total_distance_m: number;
  walking_min: number;
}

const CAT_EMOJI: Record<string, string> = {
  '佛像': '\u{1F547}',
  '建筑': '\u{1F3DB}',
  '演出': '\u{1F3AD}',
  '体验': '\u{1F9D1}',
  '自然': '\u{1F338}',
  '服务': 'ℹ',
};

const CENTER: [number, number] = [31.4258, 120.103];
const DEMO_POSITION: [number, number] = [31.4258, 120.1030];
const ROUTE_COLORS = ['#3385ff', '#f76b1c', '#10b563', '#8b5cf6'];

interface LeafletMapProps {
  selectedSpotId: number | null;
  onSpotSelect: (spot: MapSpot) => void;
  onRouteSelect?: (route: MapRoute) => void;
  onNavigationStart?: (spot: MapSpot, route: MapRoute) => void;
  onNavigationUpdate?: (spot: MapSpot, route: MapRoute, position: [number, number]) => void;
  onRoutesLoaded?: (routes: MapRoute[]) => void;
  activeRouteId?: number | null;
}

function iconHtml(emoji: string, selected = false) {
  return `<div style="font-size:${selected ? 26 : 20}px;cursor:pointer;filter:drop-shadow(0 2px 4px rgba(0,0,0,.3));transition:all .15s">${emoji}</div>`;
}

export function LeafletMap({ selectedSpotId, onSpotSelect, onRouteSelect, onNavigationStart, onNavigationUpdate, onRoutesLoaded, activeRouteId }: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<number, L.Marker>>(new Map());
  const demoMarkerRef = useRef<L.Marker | null>(null);
  const selectedNavigationSpotRef = useRef<MapSpot | null>(null);
  const navigationRequestRef = useRef(0);
  const routeLinesRef = useRef<L.Polyline[]>([]);
  const [spots, setSpots] = useState<MapSpot[]>([]);
  const [routes, setRoutes] = useState<MapRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [spotListOpen, setSpotListOpen] = useState(false);
  const [navigationRoute, setNavigationRoute] = useState<MapRoute | null>(null);
  const [demoPosition, setDemoPosition] = useState<[number, number]>(DEMO_POSITION);
  const [locationMode, setLocationMode] = useState<'gps' | 'manual' | 'demo' | 'unavailable'>('demo');
  const [gpsLoading, setGpsLoading] = useState(false);
  const [locationCollapsed, setLocationCollapsed] = useState(true);
  const navigationLineRef = useRef<L.Polyline[]>([]);

  function requestGpsLocation(mapOverride?: L.Map, markerOverride?: L.Marker) {
    const map = mapOverride ?? mapRef.current;
    const marker = markerOverride ?? demoMarkerRef.current;
    if (!navigator.geolocation || !map || !marker) {
      setLocationMode('unavailable');
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const next: [number, number] = [position.coords.latitude, position.coords.longitude];
        setDemoPosition(next);
        setLocationMode('gps');
        setGpsLoading(false);
        marker.setLatLng(next);
        map.setView(next, 16, { animate: true });
        window.localStorage.setItem('lingshanGuideCurrentLocation', JSON.stringify({
          latitude: next[0], longitude: next[1], accuracy: position.coords.accuracy, source: 'gps',
        }));
      },
      () => {
        setGpsLoading(false);
        setLocationMode('manual');
      },
      { enableHighAccuracy: true, maximumAge: 30000, timeout: 3500 },
    );
  }

  // Initialize map
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return;

    const map = L.map(containerRef.current, {
      center: CENTER,
      zoom: 15,
      zoomControl: true,
      attributionControl: false,
    });

    const demoMarker = L.marker(DEMO_POSITION, {
      draggable: true,
      icon: L.divIcon({ html: '<div class="guide-demo-location">●</div>', iconSize: [28, 28], iconAnchor: [14, 14], className: '' }),
    }).addTo(map).bindPopup('<b>当前位置（模拟）</b><br><small>拖动此点模拟移动，导航会自动更新下一段</small>');
    demoMarker.on('dragend', () => {
      const next = demoMarker.getLatLng();
      const position: [number, number] = [next.lat, next.lng];
      setDemoPosition(position);
      setLocationMode('manual');
      window.localStorage.setItem('lingshanGuideCurrentLocation', JSON.stringify({ latitude: position[0], longitude: position[1], source: 'manual' }));
      const target = selectedNavigationSpotRef.current;
      if (target) void requestNavigationRoute(target, position, false);
    });
    demoMarkerRef.current = demoMarker;

    L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
    }).addTo(map);

    mapRef.current = map;

    // 演示模式：默认使用景区内模拟点位，不自动请求GPS（避免覆盖模拟位置）
    const saved = window.localStorage.getItem('lingshanGuideCurrentLocation');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.latitude && parsed.longitude) {
          const pos: [number, number] = [parsed.latitude, parsed.longitude];
          setDemoPosition(pos);
          setLocationMode(parsed.source === 'gps' ? 'gps' : 'manual');
          demoMarker.setLatLng(pos);
          map.setView(pos, 16);
        }
      } catch { /* keep default demo position */ }
    }
    // 不在景区时不要自动GPS，保留模拟点位用于演示

    return () => {
      map.remove();
      demoMarkerRef.current = null;
      mapRef.current = null;
    };
  }, []);


  async function requestNavigationRoute(spot: MapSpot, position: [number, number], announceStart: boolean) {
    const requestId = ++navigationRequestRef.current;
    try {
      const response = await request.post('/api/map/route/live', {
        latitude: position[0], longitude: position[1], target_spot_id: spot.id, target_name: spot.name,
      });
      const body = response.data as { code?: number; data?: unknown };
      const feature = (body.code !== undefined && body.data ? body.data : body) as { geometry?: { coordinates?: [number, number][] }; properties?: Record<string, unknown> };
      const properties = feature.properties ?? {};
      const coordinates = (feature.geometry?.coordinates ?? []).map(([lng, lat]) => [lat, lng] as [number, number]);
      const route: MapRoute = {
        id: Number(properties.id ?? -spot.id), name: String(properties.name ?? `前往${spot.name}`),
        duration: String(properties.duration ?? '实时导航'), difficulty: String(properties.difficulty ?? '实时导航'),
        color: String(properties.color ?? '#0ea5e9'), coordinates,
        steps: Array.isArray(properties.steps) ? properties.steps as MapRoute['steps'] : [],
        total_distance_m: Number(properties.total_distance_m ?? 0), walking_min: Number(properties.walking_min ?? 0),
      };
      if (requestId !== navigationRequestRef.current) return;
      setNavigationRoute(route);
      if (announceStart) onNavigationStart?.(spot, route);
      else onNavigationUpdate?.(spot, route, position);
    } catch {
      if (requestId === navigationRequestRef.current) setNavigationRoute(null);
    }
  }

  async function selectSpot(spot: MapSpot) {
    selectedNavigationSpotRef.current = spot;
    onSpotSelect(spot);
    mapRef.current?.flyTo([spot.lat, spot.lng], 16, { duration: 0.5 });
    await requestNavigationRoute(spot, demoPosition, false);
  }

  // Load spots and routes
  useEffect(() => {
    let active = true;
    setLoading(true);

    Promise.all([
      request.get('/api/map/spots'),
      request.get('/api/map/routes'),
    ]).then(([spotsRes, routesRes]) => {
      if (!active) return;

      const spotsData = (spotsRes.data as any)?.features ?? [];
      const routesData = (routesRes.data as any)?.features ?? [];

      const parsedSpots: MapSpot[] = spotsData
        .filter((f: any) => f.geometry?.type === 'Point')
        .map((f: any) => {
          const [lng, lat] = f.geometry.coordinates as [number, number];
          const p = f.properties ?? {};
          return { id: p.id, name: p.name, category: p.category ?? '', description: (p.description ?? '').slice(0, 120), lat, lng };
        });

      const parsedRoutes: MapRoute[] = routesData
        .filter((f: any) => f.geometry?.type === 'LineString')
        .map((f: any) => {
          const coords = (f.geometry.coordinates as [number, number][]).map(([lng, lat]) => [lat, lng] as [number, number]);
          const p = f.properties ?? {};
          return {
            id: p.id, name: p.name, duration: p.duration, difficulty: p.difficulty,
            color: p.color ?? '#3385ff', coordinates: coords,
            steps: p.steps ?? [], total_distance_m: p.total_distance_m ?? 0, walking_min: p.walking_min ?? 0,
          };
        });

      setSpots(parsedSpots);
      setRoutes(parsedRoutes);
      onRoutesLoaded?.(parsedRoutes);
      setLoading(false);
    }).catch(() => {
      if (active) setLoading(false);
    });

    return () => { active = false; };
  }, []);

  // Render spots as markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || spots.length === 0) return;

    // Clear old markers
    markersRef.current.forEach((m) => map.removeLayer(m));
    markersRef.current.clear();

    spots.forEach((spot) => {
      const emoji = CAT_EMOJI[spot.category] ?? '\u{1F4CD}';
      const sel = spot.id === selectedSpotId;
      const marker = L.marker([spot.lat, spot.lng], {
        icon: L.divIcon({ html: iconHtml(emoji, sel), iconSize: [32, 32], iconAnchor: [16, 16], className: '' }),
      });

      marker.addTo(map);
      marker.on('click', () => { void selectSpot(spot); });
      markersRef.current.set(spot.id, marker);
    });
  }, [spots, selectedSpotId, onSpotSelect]);

  // Update marker style when selectedSpotId changes
  useEffect(() => {
    markersRef.current.forEach((marker, id) => {
      const spot = spots.find((s) => s.id === id);
      if (!spot) return;
      const emoji = CAT_EMOJI[spot.category] ?? '\u{1F4CD}';
      const sel = id === selectedSpotId;
      marker.setIcon(L.divIcon({ html: iconHtml(emoji, sel), iconSize: [32, 32], iconAnchor: [16, 16], className: '' }));
      if (sel) {
        mapRef.current?.flyTo([spot.lat, spot.lng], 16, { duration: 0.5 });
      }
    });
  }, [selectedSpotId, spots]);

  // Draw the route from the demo location to the selected spot.
  useEffect(() => {
    const map = mapRef.current;
    navigationLineRef.current.forEach((line) => map?.removeLayer(line));
    navigationLineRef.current = [];
    if (!map || !navigationRoute?.coordinates.length) return;
    const halo = L.polyline(navigationRoute.coordinates, { color: '#fff', weight: 8, opacity: 0.9 }).addTo(map);
    const line = L.polyline(navigationRoute.coordinates, { color: navigationRoute.color, weight: 5, opacity: 0.95, dashArray: '10 7' }).addTo(map);
    navigationLineRef.current.push(halo, line);
    map.fitBounds(line.getBounds(), { padding: [48, 48], maxZoom: 16 });
    return () => { navigationLineRef.current.forEach((item) => map.removeLayer(item)); navigationLineRef.current = []; };
  }, [navigationRoute]);

  // Render routes (when external activeRouteId changes)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old route lines
    routeLinesRef.current.forEach((l) => map.removeLayer(l));
    routeLinesRef.current = [];
    if (!activeRouteId) return;

    const matched = routes.filter((route) => route.id === activeRouteId);
    if (!matched.length) return;

    matched.forEach((route, idx) => {
      const color = route.color || ROUTE_COLORS[idx % ROUTE_COLORS.length];

      // Halo
      const halo = L.polyline(route.coordinates, { color: '#fff', weight: 7, opacity: 0.85, interactive: false }).addTo(map);
      // Main line
      const line = L.polyline(route.coordinates, { color, weight: 3.5, opacity: 1 }).addTo(map);

      line.on('click', () => {
        onRouteSelect?.(route);
      });

      // Hover tooltip
      const totalKm = (route.total_distance_m / 1000).toFixed(1);
      line.bindTooltip(`<b>${route.name}</b><br>${route.duration} · ${totalKm}km`, { sticky: true });

      routeLinesRef.current.push(halo, line);

      // Fit bounds to show the selected route
      map.fitBounds(line.getBounds(), { padding: [50, 50], maxZoom: 16 });
    });
  }, [routes, activeRouteId, onRouteSelect]);

  // Fit bounds when data loads
  useEffect(() => {
    const map = mapRef.current;
    if (!map || loading || spots.length === 0) return;
    try {
      const group = L.featureGroup(Array.from(markersRef.current.values()));
      map.fitBounds(group.getBounds().pad(0.15));
    } catch { /* ignore */ }
  }, [loading, spots.length]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 300, borderRadius: 10, overflow: 'hidden' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      {/* 折叠式 GPS 位置状态栏 */}
      <button type="button" className="guide-map-location-toggle" onClick={() => setLocationCollapsed((v) => !v)}>
        {locationCollapsed ? '📍' : '▼'}
      </button>
      {!locationCollapsed && (
        <div className="guide-map-location-status">
          <span className={locationMode === 'demo' || locationMode === 'manual' ? 'guide-demo-badge' : ''}>
            {locationMode === 'demo' || locationMode === 'manual' ? '📍 模拟位置' : locationMode === 'gps' ? '📡 GPS定位' : '⚠ GPS不可用'} · {demoPosition[0].toFixed(5)}, {demoPosition[1].toFixed(5)}
          </span>
          <button type="button" onClick={() => requestGpsLocation()} disabled={gpsLoading}>{gpsLoading ? '定位中' : 'GPS定位'}</button>
          <button type="button" onClick={() => {
            setDemoPosition(DEMO_POSITION);
            setLocationMode('demo');
            demoMarkerRef.current?.setLatLng(DEMO_POSITION);
            mapRef.current?.setView(DEMO_POSITION, 16, { animate: true });
            window.localStorage.setItem('lingshanGuideCurrentLocation', JSON.stringify({ latitude: DEMO_POSITION[0], longitude: DEMO_POSITION[1], source: 'demo' }));
          }} title="重置到景区演示位置">📍 重置</button>
        </div>
      )}
      {loading && (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(255,255,255,.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, fontSize: 14, color: '#666' }}>
          加载地图中...
        </div>
      )}
      <div className={`guide-map-spot-list${spotListOpen ? ' expanded' : ''}`}>
        <button type="button" className="guide-map-spot-list-toggle" onClick={() => setSpotListOpen((open) => !open)}>
          <span>景点列表</span><span>{spotListOpen ? '收起' : `${spots.length || 0} 个景点`}</span>
        </button>
        {spotListOpen && <div className="guide-map-spot-list-body">
          {spots.map((spot) => <button type="button" key={spot.id} className={`guide-map-spot-item${spot.id === selectedSpotId ? ' active' : ''}`} onClick={() => { void selectSpot(spot); }}>
            <span className="guide-map-spot-item-name">{spot.name}</span><span className="guide-map-spot-item-category">{spot.category || '景点'}</span>
          </button>)}
        </div>}
      </div>
    </div>
  );
}
