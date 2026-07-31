import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loginUser, registerUser, sendLoginCode, sendRegisterCode } from '../../api/auth';
import { getRecentSessions, getSessionDetail, sendChatMessage } from '../../api/chat';
import { getLingshanWeather } from '../../api/weather';
import request, { ApiError } from '../../api/request';

vi.mock('../../api/request', () => ({
  ApiError: class ApiError extends Error {
    status: number;
    data?: unknown;

    constructor(status: number, message: string, data?: unknown) {
      super(message);
      this.status = status;
      this.data = data;
    }
  },
  unwrapApiData: <T>(value: unknown): T | null => {
    if (!value || typeof value !== 'object') return null;
    const body = value as Record<string, unknown>;
    if ('data' in body && ('code' in body || 'msg' in body)) {
      return (body.data as T | null | undefined) ?? null;
    }
    return value as T;
  },
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('api helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('maps register payload to the backend shape', async () => {
    vi.mocked(request.post).mockResolvedValue({
      data: { code: 200, msg: 'ok', data: { username: 'tester' } },
    });

    await expect(
      registerUser({
        username: 'tester',
        password: 'Password1!',
        code: '1234',
        confirm_password: 'Password1!',
      }),
    ).resolves.toEqual({
      username: 'tester',
      token: undefined,
      userInfo: { username: 'tester' },
    });

    expect(request.post).toHaveBeenCalledWith('/api/user/register', {
      phone: 'tester',
      password: 'Password1!',
      code: '1234',
      confirm_password: 'Password1!',
    });
  });

  it('maps login payload to the backend shape', async () => {
    vi.mocked(request.post).mockResolvedValue({
      data: { code: 200, msg: 'ok', data: { username: 'tester', token: 'token-1' } },
    });

    await expect(loginUser({ username: 'tester', password: 'Password1!' })).resolves.toEqual({
      username: 'tester',
      token: 'token-1',
      userInfo: { username: 'tester' },
    });

    expect(request.post).toHaveBeenCalledWith('/api/user/login', {
      phone: 'tester',
      password: 'Password1!',
      code: '',
    });
  });

  it('sends register and login code requests', async () => {
    vi.mocked(request.post).mockResolvedValue({
      data: { code: 200, msg: 'sent', data: { code: '1234', phone: '13800138000' } },
    });

    await sendRegisterCode('13800138000');
    await sendLoginCode('13800138000');

    expect(request.post).toHaveBeenNthCalledWith(1, '/api/user/getcode', {
      phone: '13800138000',
      code_type: 'register',
    });
    expect(request.post).toHaveBeenNthCalledWith(2, '/api/user/getcode', {
      phone: '13800138000',
      code_type: 'login',
    });
  });

  it('maps chat response payload', async () => {
    vi.mocked(request.post).mockResolvedValue({
      data: { code: 200, msg: 'ok', data: { answer: 'open today', session_id: 's1' } },
    });

    await expect(sendChatMessage('s1', 'open?')).resolves.toEqual({
      answer: 'open today',
      session_id: 's1',
    });

    expect(request.post).toHaveBeenCalledWith('/api/user/chat', {
      question: 'open?',
      session_id: 's1',
    });
  });

  it('reads the latest direct weather response', async () => {
    vi.mocked(request.get).mockResolvedValue({
      data: {
        city: '无锡灵山',
        temperature: '26°C',
        weather: '晴',
        icon: '100',
        advice: '天气适宜，祝您游玩愉快',
        updated_at: '2026-07-12T12:00:00',
      },
    });

    await expect(getLingshanWeather()).resolves.toMatchObject({
      city: '无锡灵山',
      temperature: '26°C',
      icon: '100',
      updated_at: '2026-07-12T12:00:00',
    });
  });

  it('keeps compatibility with the enveloped weather response', async () => {
    vi.mocked(request.get).mockResolvedValue({
      data: {
        code: 200,
        msg: 'ok',
        data: { city: '无锡灵山', temperature: '24°C', weather: '多云', icon: '101' },
      },
    });

    await expect(getLingshanWeather()).resolves.toEqual({
      city: '无锡灵山',
      temperature: '24°C',
      weather: '多云',
      icon: '101',
    });
  });

  it('maps histories to frontend session objects', async () => {
    vi.mocked(request.get).mockResolvedValue({
      data: {
        code: 200,
        msg: 'ok',
        data: {
          histories: [{ session_id: 's1', title: 'Title', time: '2026-06-16 10:00:00' }],
        },
      },
    });

    await expect(getRecentSessions()).resolves.toEqual([
      {
        session_id: 's1',
        title: 'Title',
        preview: 'Title',
        created_at: '2026-06-16 10:00:00',
        updated_at: '2026-06-16 10:00:00',
      },
    ]);
  });

  it('requests session detail from the current frontend route', async () => {
    vi.mocked(request.get).mockResolvedValue({
      data: { code: 200, msg: 'ok', data: { messages: [{ role: 'assistant', content: 'hello' }] } },
    });

    await expect(getSessionDetail('session-1')).resolves.toEqual([{ role: 'assistant', content: 'hello' }]);

    expect(request.get).toHaveBeenCalledWith('/api/user/chat/detail', {
      params: { session_id: 'session-1' },
    });
  });

  it('propagates request errors unchanged', async () => {
    const error = new ApiError(401, 'Unauthorized');
    vi.mocked(request.post).mockRejectedValue(error);

    await expect(loginUser({ username: 'tester', password: 'x' })).rejects.toBe(error);
  });
});
