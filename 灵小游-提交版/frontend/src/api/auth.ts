/**
 * 认证 API
 * =========
 * 登录、注册、验证码、登出
 */

import request from './request';

// ==================== 类型定义 ====================

export interface LoginPayload {
  username: string;
  password?: string;
  code?: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  code?: string;
  confirm_password?: string;
}

export interface AuthResult {
  username: string;
  token?: string;
  refreshToken?: string;
  userInfo: { username: string; [key: string]: unknown };
}

// ==================== API 函数 ====================

/** 登录（密码或验证码） */
export async function loginUser(payload: LoginPayload): Promise<AuthResult> {
  const res = await request.post('/api/user/login', {
    phone: payload.username,
    password: payload.password || '',
    code: payload.code || '',
  });

  const data = res.data as {
    code: number;
    msg: string;
    data?: {
      username?: string;
      token?: string;
      access_token?: string;
      refresh_token?: string;
      user?: { username: string; [key: string]: unknown };
      userInfo?: { username: string; [key: string]: unknown };
      phone?: string;
      role?: 'user' | 'admin';
    };
  };

  const d = data.data || {};
  const username = d.username ?? d.phone ?? payload.username;
  const userInfo = d.userInfo ?? d.user ?? { username };

  return {
    username,
    token: d.token ?? d.access_token,
    refreshToken: d.refresh_token,
    userInfo: { ...userInfo, username, role: d.role },
  };
}

/** 注册 */
export async function registerUser(payload: RegisterPayload): Promise<AuthResult> {
  const res = await request.post('/api/user/register', {
    phone: payload.username,
    password: payload.password,
    code: payload.code || '',
    confirm_password: payload.confirm_password || '',
  });

  const data = res.data as {
    code: number;
    msg: string;
    data?: { username?: string; token?: string; refresh_token?: string; [key: string]: unknown };
  };

  const d = data.data || {};
  const username = d.username ?? payload.username;

  return {
    username,
    token: d.token,
    refreshToken: d.refresh_token as string | undefined,
    userInfo: { username },
  };
}

/** 发送验证码 */
export async function sendVerificationCode(phone: string, codeType: 'register' | 'login') {
  const res = await request.post('/api/user/getcode', { phone, code_type: codeType });
  return res.data as { code: number; msg: string; data?: { code?: string; phone?: string } };
}

/** 注册验证码 */
export function sendRegisterCode(phone: string) {
  return sendVerificationCode(phone, 'register');
}

/** 登录验证码 */
export function sendLoginCode(phone: string) {
  return sendVerificationCode(phone, 'login');
}

/** 登出 */
export async function logoutUser(): Promise<void> {
  try {
    await request.post('/api/user/logout');
  } catch {
    // 后端无 logout 端点时忽略（JWT 无状态，删除前端 token 即可）
  }
}

/** 游客登录 */
export async function guestLogin(): Promise<{ token: string; guest_id: string }> {
  const res = await request.post('/api/user/guest');
  const body = res.data as { code: number; data?: { token: string; guest_id: string } };
  if (body.code !== 200 || !body.data?.token) {
    throw new Error('游客模式启动失败');
  }
  return body.data;
}

/** 查询用户身份 */
export async function getUserIdentity(): Promise<{ type: 'user' | 'guest' | 'anonymous'; id: string | null }> {
  const res = await request.get('/api/user/identity');
  const body = res.data as { code: number; data?: { type: 'user' | 'guest' | 'anonymous'; id: string | null } };
  return body.data ?? { type: 'anonymous', id: null };
}

export async function refreshAccessToken(refreshToken: string): Promise<string> {
  const res = await request.post('/api/user/refresh', { refresh_token: refreshToken });
  const token = (res.data as { data?: { token?: string } }).data?.token;
  if (!token) throw new Error('token refresh failed');
  return token;
}