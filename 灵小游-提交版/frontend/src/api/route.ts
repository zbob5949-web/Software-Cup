/**
 * 路线 API
 * =========
 * 路线列表、路线推荐
 * 后端返回格式: Result(200, "success", {"routes": [...]}) / {"route": {...}, "hint": "..."}
 */

import request from './request';

export interface RouteSpot {
  id: number;
  name: string;
  duration?: string;
  tips?: string;
}

export interface Route {
  id: number;
  name: string;
  duration?: string;
  difficulty?: string;
  description?: string;
  spot_ids?: string;
  hours_min?: number;
  hours_max?: number;
  spots?: RouteSpot[];
}

export interface RouteRecommendParams {
  interest?: string;
  hours?: number;
  difficulty?: string;
}

/** 获取路线列表 */
export async function getRoutes(): Promise<Route[]> {
  const res = await request.get('/api/routes');
  const body = res.data as { code: number; data?: { routes?: Route[] } };
  return body.data?.routes ?? [];
}

/** 获取推荐路线（支持三选一筛选） */
export async function getRecommendedRoutes(params?: RouteRecommendParams): Promise<Route[]> {
  const res = await request.get('/api/routes/recommend', { params });
  const body = res.data as { code: number; data?: { routes?: Route[]; route?: Route } };
  if (body.data?.route) return [body.data.route];
  return body.data?.routes ?? [];
}
