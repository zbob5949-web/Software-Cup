/**
 * FAQ API
 * ========
 * FAQ 列表、按分类查询、智能匹配
 * 后端返回格式:
 *   Result(200, "success", {"faqs": [...]})  (列表)
 *   Result(200, "success", {"matched": true, "faq": {...}}) (匹配)
 */

import request from './request';

export interface FaqItem {
  id: number;
  question: string;
  answer: string;
  category?: string;
  [key: string]: unknown;
}

export interface FaqMatchResult {
  matched: boolean;
  score: number;
  faq: FaqItem | null;
}

/** 获取 FAQ 列表（可选按分类筛选） */
export async function getFaqs(category?: string | null): Promise<FaqItem[]> {
  const params: Record<string, string> = {};
  if (category) params.category = category;
  const res = await request.get('/api/faqs', { params });
  const body = res.data as { code: number; data?: { faqs?: FaqItem[] } };
  return body.data?.faqs ?? [];
}

/** FAQ 智能匹配 */
export async function matchFaq(query: string): Promise<FaqMatchResult> {
  const res = await request.get('/api/faqs/match', { params: { q: query } });
  const body = res.data as { code: number; data?: FaqMatchResult };
  return body.data ?? { matched: false, score: 0, faq: null };
}
