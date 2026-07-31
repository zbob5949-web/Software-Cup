import request from './request';

export interface AdminStatCard {
  title: string;
  value: number | string;
  change: string;
  changeType: 'up' | 'down' | 'flat';
}

export interface HotQuestion {
  rank: number;
  question: string;
  count: number;
}

export interface SatisfactionSummary {
  positive: number;
  neutral: number;
  negative: number;
}

export interface DashboardWeather {
  location: string;
  weather: string;
  temp: string;
  humidity: string;
  feels_like: string;
  advice: string;
}

export interface DashboardPayload {
  stats: AdminStatCard[];
  hotQuestions: HotQuestion[];
  satisfaction: SatisfactionSummary;
  weather: DashboardWeather;
}

export interface KnowledgeItem {
  id: string;
  title: string;
  category: string;
  status: 'published' | 'draft' | 'archived';
  updatedAt: string;
  content: string;
}

export interface KnowledgePayload {
  title: string;
  category: string;
  status: 'published' | 'draft' | 'archived';
  content: string;
}

export interface AvatarConfig {
  name: string;
  welcomeMessage: string;
  introduction: string;
  videoUrl: string;
  voiceType: string;
  speed: number;
  volume: number;
  updatedAt?: string;
}

export interface FeedbackItem {
  id: string;
  username: string;
  date: string;
  rating: number;
  content: string;
  category: string;
}

export interface FeedbackStats {
  total: number;
  positive: number;
  neutral: number;
  negative: number;
  avg_rating: number;
}

export interface FeedbackListPayload {
  items: FeedbackItem[];
  stats: FeedbackStats;
}

export interface StatisticsKpi {
  title: string;
  value: number | string;
  change: string;
  changeType: 'up' | 'down' | 'flat';
}

export interface DailyStat {
  date: string;
  count: number;
}

export interface SourceRatio {
  name: string;
  value: number;
  color: string;
}

export interface SatisfactionPoint {
  date: string;
  satisfaction: number;
  count: number;
}

export interface SentimentPoint {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  avgScore: number;
}

export interface SentimentSummary {
  totalAnalyzed: number;
  positiveRatio: number;
  neutralRatio: number;
  negativeRatio: number;
  avgSentimentScore: number;
  positiveTrend: string;
  trend: 'up' | 'down' | 'flat';
}

export interface StatisticsPayload {
  kpis: StatisticsKpi[];
  trend: DailyStat[];
  hotQuestions: HotQuestion[];
  sourceRatio: SourceRatio[];
  satisfactionTrend: SatisfactionPoint[];
  sentimentTrend: SentimentPoint[];
  sentimentSummary: SentimentSummary;
  sentimentKeywords: {
    positive: string[];
    negative: string[];
  };
}

export interface SystemInfo {
  systemName: string;
  contactPhone: string;
  contactEmail: string;
  copyright: string;
  beian: string;
}

export interface ApiConfig {
  weatherApi: string;
  weatherKey: string;
  llmApi: string;
  llmModel: string;
  dbHost: string;
  dbPort: string;
  dbName: string;
  dbUser: string;
  dbPassword: string;
}

export interface SettingsPayload {
  systemInfo: SystemInfo;
  apiConfig: ApiConfig;
}

function unwrap<T>(value: { code: number; msg: string; data?: T } | undefined | null): T | null {
  if (!value || typeof value !== 'object') return null;
  if ('data' in value) return (value.data as T | undefined) ?? null;
  return null;
}

export async function getAdminDashboard(): Promise<DashboardPayload> {
  const res = await request.get('/api/admin/dashboard');
  return unwrap<DashboardPayload>(res.data) as DashboardPayload;
}

export async function getKnowledgeList(params?: { search?: string; category?: string }): Promise<KnowledgeItem[]> {
  const res = await request.get('/api/admin/knowledge', { params });
  return unwrap<KnowledgeItem[]>(res.data) ?? [];
}

export async function createKnowledgeItem(payload: KnowledgePayload) {
  await request.post('/api/admin/knowledge', payload);
}

export async function updateKnowledgeItem(id: string, payload: KnowledgePayload) {
  await request.put(`/api/admin/knowledge/${id}`, payload);
}

export async function deleteKnowledgeItem(id: string) {
  await request.delete(`/api/admin/knowledge/${id}`);
}

export async function getAvatarConfig(): Promise<AvatarConfig> {
  const res = await request.get('/api/admin/avatar');
  return unwrap<AvatarConfig>(res.data) as AvatarConfig;
}

export async function updateAvatarConfig(payload: {
  name: string;
  welcome_message: string;
  introduction: string;
  video_url: string;
  voice_type: string;
  speed: number;
  volume: number;
}) {
  await request.put('/api/admin/avatar', payload);
}

export async function getAdminFeedbackList(params?: { search?: string; category?: string; rating?: number }): Promise<FeedbackListPayload> {
  const res = await request.get('/api/admin/feedback', { params });
  return unwrap<FeedbackListPayload>(res.data) as FeedbackListPayload;
}

export async function deleteAdminFeedback(id: string) {
  await request.delete(`/api/admin/feedback/${id}`);
}

export async function getStatistics(days: 7 | 30): Promise<StatisticsPayload> {
  const res = await request.get('/api/admin/statistics', { params: { days } });
  return unwrap<StatisticsPayload>(res.data) as StatisticsPayload;
}

export async function getSettings(): Promise<SettingsPayload> {
  const res = await request.get('/api/admin/settings');
  return unwrap<SettingsPayload>(res.data) as SettingsPayload;
}

export async function updateSystemInfo(payload: {
  system_name: string;
  contact_phone: string;
  contact_email: string;
  copyright: string;
  beian: string;
}) {
  await request.put('/api/admin/settings/system', payload);
}

export async function updateApiConfig(payload: {
  weather_api: string;
  weather_key: string;
  llm_api: string;
  llm_model: string;
  db_host: string;
  db_port: string;
  db_name: string;
  db_user: string;
  db_password: string;
}) {
  await request.put('/api/admin/settings/api', payload);
}

export interface AdminFaq { id: number; question: string; answer: string; category?: string; keywords?: string; sort_order: number; is_active: boolean; }
export async function getAdminFaqs(): Promise<AdminFaq[]> { const res = await request.get('/api/admin/faqs', { params: { include_inactive: true, page_size: 100 } }); return unwrap<{ faqs?: AdminFaq[] }>(res.data)?.faqs ?? []; }
export async function createAdminFaq(payload: Omit<AdminFaq, 'id'>) { await request.post('/api/admin/faqs', payload); }
export async function updateAdminFaq(id: number, payload: Partial<AdminFaq>) { await request.put(`/api/admin/faqs/${id}`, payload); }
export async function deleteAdminFaq(id: number) { await request.delete(`/api/admin/faqs/${id}`); }

export interface AdminUser { id: number; phone: string; role: 'user' | 'admin'; is_active: boolean; is_super_admin: boolean; created_at?: string; last_login?: string; last_login_ip?: string; }
export async function getAdminUsers(): Promise<AdminUser[]> { const res = await request.get('/api/admin/users'); return unwrap<{ users?: AdminUser[] }>(res.data)?.users ?? []; }
export async function updateAdminUser(id: number, payload: Partial<Pick<AdminUser, 'role' | 'is_active' | 'is_super_admin'>>) { await request.put(`/api/admin/users/${id}`, payload); }

export interface SentimentReport { period: { start_date: string; end_date: string }; total_messages: number; counts: { positive: number; neutral: number; negative: number }; trend: Array<{ date: string; positive: number; neutral: number; negative: number; total: number }>; examples: Record<string, Array<{ text: string; score: number }>>; summary: string; focus_points: Array<{ word?: string; keyword?: string; count?: number } | string>; suggestions: string[]; analyzer: string; }
export async function getSentimentReport(params?: { start_date?: string; end_date?: string; use_ai?: boolean }): Promise<SentimentReport> { const res = await request.get('/api/admin/reports/sentiment', { params }); return unwrap<SentimentReport>(res.data) as SentimentReport; }
export interface AdminConversation {
  session_id: string;
  phone: string;
  title: string;
  preview: string;
  message_count: number;
  created_at?: string;
  last_message_at?: string;
}

export interface AdminConversationMessage {
  id?: number;
  phone?: string;
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  created_at?: string;
}

export async function getAdminConversations(params?: { keyword?: string; limit?: number; offset?: number }): Promise<{ sessions: AdminConversation[]; total: number }> {
  const res = await request.get('/api/admin/conversations', { params });
  const data = unwrap<{ sessions?: AdminConversation[]; total?: number }>(res.data);
  return { sessions: data?.sessions ?? [], total: data?.total ?? 0 };
}

export async function getAdminConversationDetail(sessionId: string): Promise<AdminConversationMessage[]> {
  const res = await request.get(`/api/admin/conversations/${encodeURIComponent(sessionId)}`);
  return unwrap<{ messages?: AdminConversationMessage[] }>(res.data)?.messages ?? [];
}

export async function deleteAdminConversation(sessionId: string): Promise<void> {
  await request.delete(`/api/admin/conversations/${encodeURIComponent(sessionId)}`);
}
export interface AdminSpot {
  id: number; name: string; category?: string; description?: string; open_time?: string; duration?: string; tips?: string; sort_order: number; image_url?: string; is_active: boolean; created_at?: string;
}
export async function getAdminSpots(): Promise<AdminSpot[]> { const res = await request.get('/api/admin/spots'); return unwrap<{ spots?: AdminSpot[] }>(res.data)?.spots ?? []; }
export async function createAdminSpot(payload: Omit<AdminSpot, 'id' | 'created_at'>): Promise<void> { await request.post('/api/admin/spots', payload); }
export async function updateAdminSpot(id: number, payload: Partial<AdminSpot>): Promise<void> { await request.put(`/api/admin/spots/${id}`, payload); }

export interface AdminTicket { id: number; code: string; name: string; price: number; note?: string; sort_order: number; is_active: boolean; created_at?: string; updated_at?: string; }
export async function getAdminTickets(): Promise<AdminTicket[]> { const res = await request.get('/api/admin/tickets'); return unwrap<{ tickets?: AdminTicket[] }>(res.data)?.tickets ?? []; }
export async function createAdminTicket(payload: Omit<AdminTicket, 'id' | 'created_at' | 'updated_at'>): Promise<void> { await request.post('/api/admin/tickets', payload); }
export async function updateAdminTicket(id: number, payload: Partial<AdminTicket>): Promise<void> { await request.put(`/api/admin/tickets/${id}`, payload); }

export interface AdminFavorite { id: number; phone: string; spot_id: number; spot_name: string; category: string; created_at?: string; }
export async function getAdminFavorites(): Promise<AdminFavorite[]> { const res = await request.get('/api/admin/favorites'); return unwrap<{ favorites?: AdminFavorite[] }>(res.data)?.favorites ?? []; }
export async function deleteAdminFavorite(id: number): Promise<void> { await request.delete(`/api/admin/favorites/${id}`); }
export interface AdminOrder {
  id: number; order_no: string; user_id: number; phone: string; ticket_id: number; ticket_name: string; ticket_type?: string; quantity: number; unit_price: number; total_amount: number; visitor_name: string; visitor_phone: string; order_status: 'pending' | 'paid' | 'cancelled' | 'completed' | 'refunded'; remark?: string; created_at?: string; updated_at?: string;
}
export async function getAdminOrders(params?: { keyword?: string; status?: string }): Promise<AdminOrder[]> { const res = await request.get('/api/admin/orders', { params }); return unwrap<{ orders?: AdminOrder[] }>(res.data)?.orders ?? []; }
export async function getAdminOrderDetail(orderNo: string): Promise<AdminOrder | null> { const res = await request.get(`/api/admin/orders/${encodeURIComponent(orderNo)}`); return unwrap<{ order?: AdminOrder }>(res.data)?.order ?? null; }
export async function updateAdminOrderStatus(orderNo: string, order_status: AdminOrder['order_status']): Promise<void> { await request.put(`/api/admin/orders/${encodeURIComponent(orderNo)}/status`, { order_status }); }

// ===== 用户感受报告 =====
export interface UserSentimentPayload {
  period: { start_date: string; end_date: string };
  overallScore: number;
  overallSummary: string;
  feedback: {
    total: number;
    positive: number;
    neutral: number;
    negative: number;
    avgRating: number;
    satisfactionPct: number;
    categories: Array<{ name: string; total: number; positive: number; negative: number; avgRating: number; satisfactionPct: number }>;
    positiveExamples: Array<{ text: string; rating: number; date: string }>;
    negativeExamples: Array<{ text: string; rating: number; date: string }>;
  };
  chatSentiment: {
    totalMessages: number;
    positiveRatio: number;
    neutralRatio: number;
    negativeRatio: number;
    trend: Array<{ date: string; positive: number; neutral: number; negative: number; total: number }>;
  };
  consumption: {
    available: boolean;
    avgSatisfaction: number | null;
    totalRevenue: number | null;
    avgSpend: number | null;
    recordCount: number | null;
    costBreakdown: Array<{ name: string; amount: number; ratio: number }>;
  };
  painPoints: Array<{ label: string; score: number; keywords: string[] }>;
  suggestions: string[];
  generatedAt: string;
}
export async function getUserSentimentReport(): Promise<UserSentimentPayload> {
  const res = await request.get('/api/admin/reports/user-sentiment');
  return unwrap<UserSentimentPayload>(res.data) as UserSentimentPayload;
}