import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RegisterApiError, chatWithAI, loginUser, registerUser } from '../api';

describe('api helpers', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    global.fetch = originalFetch;
  });

  it('submits register json to the expected endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => null },
    });
    global.fetch = fetchMock as typeof fetch;

    await registerUser({ username: 'tester', password: 'Password1!' });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/user/register',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: 'tester', password: 'Password1!' }),
      }),
    );
  });

  it('submits login json to the expected endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => null },
    });
    global.fetch = fetchMock as typeof fetch;

    await loginUser({ username: 'tester', password: 'Password1!' });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/user/login',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: 'tester', password: 'Password1!' }),
      }),
    );
  });

  it('submits ai questions and returns the answer payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        get: () => 'application/json',
      },
      json: async () => ({ answer: '景区今天正常开放。' }),
    });
    global.fetch = fetchMock as typeof fetch;

    await expect(chatWithAI({ question: '今天开放吗？' })).resolves.toBe('景区今天正常开放。');

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/ai/chat',
      expect.objectContaining({
        body: JSON.stringify({ question: '今天开放吗？' }),
      }),
    );
  });

  it('throws status-specific errors for non-200 responses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      headers: { get: () => null },
    }) as typeof fetch;

    await expect(registerUser({ username: 'tester', password: 'Password1!' })).rejects.toMatchObject({
      status: 409,
    });
  });

  it.each([400, 409, 500])('preserves backend status code %s', async (statusCode) => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: statusCode,
      headers: { get: () => null },
    }) as typeof fetch;

    await expect(registerUser({ username: 'tester', password: 'Password1!' })).rejects.toMatchObject({
      status: statusCode,
    });
  });

  it('maps network failures to a request error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('offline')) as typeof fetch;

    await expect(registerUser({ username: 'tester', password: 'Password1!' })).rejects.toEqual(
      expect.objectContaining<Partial<RegisterApiError>>({
        status: -1,
      }),
    );
  });

  it('aborts the request after 10 seconds', async () => {
    global.fetch = vi.fn().mockImplementation((_input, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'));
        });
      });
    }) as typeof fetch;

    const request = registerUser({ username: 'tester', password: 'Password1!' });
    await vi.advanceTimersByTimeAsync(10000);

    await expect(request).rejects.toMatchObject({
      status: 0,
    });
  });
});
