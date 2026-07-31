import axios from 'axios';
import type { AxiosResponse } from 'axios';

export interface ApiResponse<T = unknown> {
  code: number;
  msg: string;
  data: T | null;
}

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

export function unwrapApiData<T>(value: unknown): T | null {
  if (!value || typeof value !== 'object') return null;

  const body = value as Record<string, unknown>;
  if ('data' in body && ('code' in body || 'msg' in body)) {
    return (body.data as T | null | undefined) ?? null;
  }

  return value as T;
}

function isAdminRequest(url?: string): boolean { return Boolean(url && (url.startsWith('/api/admin') || url.startsWith('/admin'))); }


const request = axios.create({
  baseURL: '',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

request.interceptors.request.use(
  (config) => {
    // 管理员 token 只用于管理员接口，避免普通导览请求被过期 admin token 劫持。
    const adminToken = window.localStorage.getItem('lingshanAdminToken');
    if (adminToken && isAdminRequest(config.url)) {
      config.headers.Authorization = `Bearer ${adminToken}`;
      return config;
    }

    const raw = window.sessionStorage.getItem('scenic-auth-state');
    if (raw) {
      try {
        const state = JSON.parse(raw) as { token?: string };
        if (state.token) {
          config.headers.Authorization = `Bearer ${state.token}`;
        }
      } catch {
        // Ignore broken session payloads and continue unauthenticated.
      }
    }
    return config;
  },
  (error) => Promise.reject(error),
);

request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const body = response.data;

    if (body && body.code !== undefined && body.code !== 200) {
      if (body.code === 401 || body.code === 40100) {
        // 如果是 admin 请求，清除 admin token；否则清除用户 session
        if (isAdminRequest(response.config.url)) {
          window.localStorage.removeItem('lingshanAdminToken');
          window.location.replace('/admin');
        } else {
          window.sessionStorage.removeItem('scenic-auth-state');
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
      }
      throw new ApiError(body.code, body.msg || '请求失败', body.data);
    }

    return response;
  },
  (error) => {
    if (axios.isCancel(error)) {
      throw new ApiError(499, '请求已取消');
    }

    if (error instanceof ApiError) {
      throw error;
    }

    const status = error.response?.status as number | undefined;
    const data = error.response?.data as ApiResponse | undefined;

    if (status === 401) {
      if (isAdminRequest(error.config?.url)) {
        window.localStorage.removeItem('lingshanAdminToken');
        window.location.replace('/admin');
      } else {
        window.sessionStorage.removeItem('scenic-auth-state');
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
    }

    throw new ApiError(
      status ?? -1,
      data?.msg || (status === 401 ? '未登录' : status === 403 ? '无权限' : '网络连接失败，请确认后端服务已启动'),
      data?.data,
    );
  },
);

export default request;
