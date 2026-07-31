/**
 * 景点 API
 * =========
 * 景点详情、景点列表
 * 后端返回格式: Result(200, "success", {"spots": [...]}) / Result(200, "success", {"spot": {...}})
 */

import request from './request';

export interface Spot {
  id: number;
  name: string;
  category?: string;
  description?: string;
  open_time?: string;
  duration?: string;
  tips?: string;
  sort_order?: number;
  image_url?: string;
  [key: string]: unknown;
}

/** 获取景点列表 */
export async function getSpotList(): Promise<Spot[]> {
  const res = await request.get('/api/spots');
  const body = res.data as { code: number; data?: { spots?: Spot[] } };
  return body.data?.spots ?? [];
}

/** 获取景点详情 */
export async function getSpotDetail(spotId: number | string): Promise<Spot | null> {
  try {
    const res = await request.get(`/api/spots/${spotId}`);
    const body = res.data as { code: number; data?: { spot?: Spot } };
    return body.data?.spot ?? null;
  } catch (error) {
    // Map presets use sort_order while the detail endpoint normally uses the database id.
    const requested = Number(spotId);
    if (Number.isFinite(requested)) {
      const spots = await getSpotList();
      const bySortOrder = spots.find((spot) => spot.sort_order === requested);
      if (bySortOrder) return bySortOrder;
    }
    throw error;
  }
}
