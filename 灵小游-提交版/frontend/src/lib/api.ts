/**
 * lib/api.ts — 兼容层
 * =====================
 * 保留此文件以防止旧代码导入断裂。
 * 所有新代码应直接导入对应的 api 模块：
 *
 *   import { loginUser } from '../api/auth';
 *   import { sendChatMessage } from '../api/chat';
 *   import { getFaqs } from '../api/faq';
 *   import { getFavorites } from '../api/favorite';
 *   import { submitFeedback } from '../api/feedback';
 *   import { getSpotDetail } from '../api/spot';
 *   import { getRecommendedRoutes } from '../api/route';
 *
 * 此文件导出 ApiError 类供旧代码引用。
 */

export { ApiError } from '../api/request';
export type { ApiResponse } from '../api/request';
