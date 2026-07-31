import request from './request';

export interface DigitalHumanConfig {
  id?: number;
  name: string;
  model_key: string;
  model_dir: string;
  display_mode: 'live2d' | string;
  voice_name?: string;
  voice_style?: string | null;
  appearance?: string | null;
  clothing?: string | null;
  cultural_style?: string | null;
  keywords?: string | null;
  is_active?: boolean;
  welcomeMessage?: string;
  introduction?: string;
  videoUrl?: string;
  voiceType?: string;
  speed?: number;
  volume?: number;
}

export interface DigitalHumanChatResult {
  reply: string;
  emotion: string;
  gesture: string;
  session_id: string;
}

const fallbackConfig: DigitalHumanConfig = {
  name: 'Haru 灵小游',
  model_key: 'live2d_haru',
  model_dir: 'Haru',
  display_mode: 'live2d',
  voice_name: 'zh-CN-XiaoyiNeural',
  welcomeMessage: '你好，我是灵山景区 AI 数字人导览助手，很高兴为你服务。',
  introduction: '灵山景区官方 AI 数字人，可提供景点讲解、游览建议与常见问题解答。',
  videoUrl: '/videos/digital-human.mp4',
  voiceType: '清亮活泼',
  speed: 1,
  volume: 0.8,
};

export async function getDigitalHumanConfig(): Promise<DigitalHumanConfig> {
  const res = await request.get('/api/digital-human/current');
  const data = res.data as { code: number; msg: string; data?: Partial<DigitalHumanConfig> };
  const current = data.data ?? {};
  return {
    ...fallbackConfig,
    ...current,
    name: current.name || fallbackConfig.name,
    model_key: current.model_key || fallbackConfig.model_key,
    model_dir: current.model_dir || fallbackConfig.model_dir,
    display_mode: current.display_mode || fallbackConfig.display_mode,
  };
}

export async function sendDigitalHumanChat(
  sessionId: string,
  question: string,
  location?: { latitude?: number; longitude?: number; accuracy?: number; source?: string },
  userInterests?: string[],
): Promise<DigitalHumanChatResult> {
  const res = await request.post('/api/digital-human/chat', {
    question,
    session_id: sessionId || '',
    ...(location ? { location } : {}),
    ...(userInterests && userInterests.length > 0 ? { user_interests: userInterests } : {}),
  }, { timeout: 15000 });
  const data = res.data as {
    code: number;
    msg: string;
    data?: {
      reply?: string;
      emotion?: string;
      gesture?: string;
      session_id?: string;
    };
  };
  const d = data.data ?? {};
  return {
    reply: d.reply ?? '',
    emotion: d.emotion ?? 'neutral',
    gesture: d.gesture ?? 'soft',
    session_id: d.session_id ?? '',
  };
}
