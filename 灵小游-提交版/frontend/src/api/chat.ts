import request, { unwrapApiData } from './request';

export interface ChatSession {
  session_id: string;
  title: string;
  preview?: string;
  time?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SessionMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

export async function getRecentSessions(): Promise<ChatSession[]> {
  const res = await request.get('/api/user/history');
  const histories = unwrapApiData<{ histories?: ChatSession[] }>(res.data)?.histories ?? [];
  return histories.map(({ time, ...rest }) => ({
    ...rest,
    preview: rest.preview ?? rest.title ?? '',
    created_at: rest.created_at ?? time,
    updated_at: rest.updated_at ?? time,
  }));
}

export async function sendChatMessage(
  sessionId: string,
  question: string,
): Promise<{ answer: string; session_id?: string }> {
  const res = await request.post('/api/user/chat', {
    question,
    session_id: sessionId || '',
  });
  const data = unwrapApiData<{ answer?: string; session_id?: string }>(res.data);
  return {
    answer: data?.answer ?? (data as { reply?: string } | null)?.reply ?? '',
    session_id: data?.session_id,
  };
}

export async function getSessionDetail(sessionId: string): Promise<SessionMessage[]> {
  const res = await request.get('/api/user/chat/detail', { params: { session_id: sessionId } });
  return unwrapApiData<{ messages?: SessionMessage[] }>(res.data)?.messages ?? [];
}

export async function deleteSession(sessionId: string): Promise<void> {
  await request.delete(`/api/user/chat/session/${sessionId}`);
}
