/**
 * TTS (文本转语音) API
 * =====================
 * 后端返回格式: { audio: "base64...", audio_mime: "audio/mpeg", pinyin: [...], text: "..." }
 */

const TTS_BASE = import.meta.env.VITE_TTS_BASE_URL ?? '';

export interface TTSResponse {
  url: string;
  audio: string;          // base64 音频
  audio_mime: string;     // "audio/mpeg"
  pinyin: Array<{ c: string; py: string; rest: boolean }>;
  duration: number;       // 音频真实时长(ms)
}

/** 文本转语音，返回完整数据供 Live2D 口型同步 */
export async function textToSpeech(text: string): Promise<TTSResponse> {
  const trimmed = text.trim();
  if (!trimmed) throw new Error('文本不能为空');

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(`${TTS_BASE}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: trimmed.slice(0, 500) }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(`TTS 服务异常: ${(errData as Record<string, unknown>).detail || response.statusText}`);
    }

    const data = await response.json();
    const base64 = data.audio;
    const mime = data.audio_mime || 'audio/mpeg';

    if (!base64) throw new Error('TTS 返回为空');

    // base64 → binary → blob → objectURL (用于降级直接播放)
    const binaryStr = atob(base64);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);

    return {
      url,
      audio: base64,
      audio_mime: mime,
      pinyin: Array.isArray(data.pinyin) ? data.pinyin : [],
      duration: typeof data.duration === 'number' ? data.duration : 0,
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('TTS 请求超时');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/** 释放临时音频 URL */
export function revokeAudioUrl(url: string): void {
  if (url && url.startsWith('blob:')) URL.revokeObjectURL(url);
}
