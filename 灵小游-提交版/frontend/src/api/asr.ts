/**
 * ASR 语音识别 API
 * POST /api/asr/transcribe — 上传音频文件并返回识别文本
 */

/** ASR 服务地址（统一走 Vite proxy /api → 后端 8000 端口） */
export const ASR_BASE_URL = import.meta.env.VITE_ASR_BASE_URL ?? '/api/asr';

/** 请求超时时间 */
const TIMEOUT_MS = 30_000;

export type AsrResult = {
  code: number;
  msg: string;
  data: { text: string; language?: string } | null;
};

export async function transcribeAudio(
  audioBlob: Blob,
  language: string = 'zh',
  signal?: AbortSignal,
): Promise<string> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  const url = `${ASR_BASE_URL}/transcribe?language=${encodeURIComponent(language)}`;

  // 超时控制器（与外部 signal 共存）
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const combinedSignal = signal
    ? combineAbortSignals(signal, controller.signal)
    : controller.signal;

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      signal: combinedSignal,
      // 不设置 Content-Type，让浏览器自动设置 multipart/form-data boundary
    });

    if (!response.ok) {
      throw new Error(`ASR 服务响应异常 (${response.status})`);
    }

    const json: AsrResult = await response.json();

    if (json.code !== 200) {
      throw new Error(json.msg || '识别失败');
    }

    return json.data?.text ?? '';
  } finally {
    clearTimeout(timeoutId);
  }
}

/** 合并两个 AbortSignal */
function combineAbortSignals(s1: AbortSignal, s2: AbortSignal): AbortSignal {
  const controller = new AbortController();
  const abort = () => controller.abort();
  s1.addEventListener('abort', abort);
  s2.addEventListener('abort', abort);
  if (s1.aborted || s2.aborted) controller.abort();
  return controller.signal;
}
