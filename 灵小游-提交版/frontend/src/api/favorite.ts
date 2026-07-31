/**
 * 收藏 API
 * =========
 * 收藏/取消收藏景点、路线、票种
 * 所有接口必须登录
 */

import request from './request';

export interface FavoriteItem {
  id: number;
  name?: string;
  category?: string;
  description?: string;
  image_url?: string;
  // route
  duration?: string;
  difficulty?: string;
  // ticket
  ticket_type?: string;
  price?: number;
  // 通用
  favorited_at?: string;
  [key: string]: unknown;
}

/** 获取景点收藏列表 */
export async function getFavorites(): Promise<FavoriteItem[]> {
  const res = await request.get('/api/favorites');
  const body = res.data as { code: number; data?: { favorites?: FavoriteItem[] } };
  return body.data?.favorites ?? [];
}

/** 获取路线收藏列表 */
export async function getRouteFavorites(): Promise<FavoriteItem[]> {
  const res = await request.get('/api/favorites/route');
  const body = res.data as { code: number; data?: { favorites?: FavoriteItem[] } };
  return body.data?.favorites ?? [];
}

/** 获取票种收藏列表 */
export async function getTicketFavorites(): Promise<FavoriteItem[]> {
  const res = await request.get('/api/favorites/ticket');
  const body = res.data as { code: number; data?: { favorites?: FavoriteItem[] } };
  return body.data?.favorites ?? [];
}

/** 收藏景点 */
export async function addFavorite(spotId: number | string): Promise<void> {
  await request.post(`/api/favorites/${spotId}`);
}

/** 取消收藏景点 */
export async function removeFavorite(spotId: number | string): Promise<void> {
  await request.delete(`/api/favorites/${spotId}`);
}

/** 收藏路线 */
export async function addRouteFavorite(routeId: number | string): Promise<void> {
  await request.post(`/api/favorites/route/${routeId}`);
}

/** 取消收藏路线 */
export async function removeRouteFavorite(routeId: number | string): Promise<void> {
  await request.delete(`/api/favorites/route/${routeId}`);
}

/** 收藏票种 */
export async function addTicketFavorite(ticketId: number | string): Promise<void> {
  await request.post(`/api/favorites/ticket/${ticketId}`);
}

/** 取消收藏票种 */
export async function removeTicketFavorite(ticketId: number | string): Promise<void> {
  await request.delete(`/api/favorites/ticket/${ticketId}`);
}