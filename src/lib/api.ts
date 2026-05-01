export type LoginPayload = {
  username: string;
  password: string;
};

export type ChatPayload = {
  question: string;
};

export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export { ApiError as RegisterApiError };

export type ApiResponse<T> = {
  code: number;
  msg: string;
  data: T | null;
};

async function parseResponse<T>(response: Response): Promise<T | null> {
  const contentType = response.headers.get('content-type') ?? '';

  if (!contentType.includes('application/json')) {
    return null;
  }

  return (await response.json()) as T;
}

async function requestJson<TResponse>(
  url: string,
  body?: object,
  signal?: AbortSignal,
): Promise<ApiResponse<TResponse>> {
  const controller = new AbortController();
  let didTimeout = false;
  const abortFromSignal = () => controller.abort();

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener('abort', abortFromSignal, { once: true });
    }
  }

  const timeoutId = window.setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, 10000);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const data = await parseResponse<ApiResponse<TResponse>>(response);

    if (!response.ok) {
      throw new ApiError(
        data?.code ?? response.status,
        data?.msg ?? `Request failed with ${response.status}`,
        data?.data,
      );
    }

    if (!data) {
      throw new ApiError(response.status, '请求失败，请检查后端服务是否启动');
    }

    if (data.code !== 200) {
      throw new ApiError(data.code, data.msg, data.data);
    }

    return data;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(didTimeout ? 0 : 499, didTimeout ? '请求超时' : '请求已取消');
    }

    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(-1, '请求失败，请检查后端服务是否启动');
  } finally {
    window.clearTimeout(timeoutId);
    if (signal) {
      signal.removeEventListener('abort', abortFromSignal);
    }
  }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export type RegisterPayload = {
  username: string;
  password: string;
};

export async function registerUser(payload: RegisterPayload): Promise<void> {
  await requestJson('/register', payload);
}

export async function loginUser(payload: LoginPayload): Promise<void> {
  await requestJson('/login', payload);
}

type ChatResponse = {
  question: string;
  answer: string;
};

export async function chatWithAI(
  payload: ChatPayload,
  signal?: AbortSignal,
): Promise<string> {
  const response = await requestJson<ChatResponse>('/chat', payload, signal);
  const answer = response.data?.answer ?? '';

  return answer;
}

export async function logoutUser(): Promise<void> {
  await requestJson<null>('/logout');
}
