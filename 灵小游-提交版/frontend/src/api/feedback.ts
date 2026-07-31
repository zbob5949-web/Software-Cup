/**
 * 反馈 API
 * =========
 * 提交反馈（游客可访问）、查看我的反馈（需登录）
 */

import request from './request';

export interface FeedbackPayload {
  type: string;
  rating: number;
  content: string;
}

export interface FeedbackItem {
  id: number;
  type?: string;
  rating?: number;
  content?: string;
  username?: string;
  created_at?: string;
  [key: string]: unknown;
}

/** 提交反馈（游客可不登录） */
export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  await request.post('/api/feedback', payload);
}

/** 获取我的反馈列表（必须登录） */
export async function getMyFeedbacks(): Promise<FeedbackItem[]> {
  const res = await request.get('/api/feedback/mine');
  const data = res.data as { code: number; msg: string; data?: { feedbacks?: FeedbackItem[] } };
  return data.data?.feedbacks ?? [];
}

export interface FeedbackStats { total: number; avg_rating: number; by_type: Array<{ type: string; count: number; avg_rating: number }>; distribution: Array<{ rating: number; count: number }>; conclusions: string[]; }
export async function getFeedbackStats(): Promise<FeedbackStats> { const res = await request.get('/api/feedback/stats'); return (res.data as { data?: FeedbackStats }).data ?? { total: 0, avg_rating: 0, by_type: [], distribution: [], conclusions: [] }; }