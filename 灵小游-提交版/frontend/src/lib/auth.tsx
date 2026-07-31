import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { refreshAccessToken } from '../api/auth';

type AuthState = {
  isAuthenticated: boolean;
  username: string;
  token?: string;
  refreshToken?: string;
  identityType?: 'user' | 'guest' | 'anonymous';
  userInfo?: {
    username: string;
    [key: string]: unknown;
  };
};

type AuthContextValue = AuthState & {
  login: (auth: { username: string; token?: string; refreshToken?: string; identityType?: AuthState['identityType']; userInfo?: AuthState['userInfo'] }) => void;
  logout: () => void;
  markUnauthorized: () => void;
};

const STORAGE_KEY = 'scenic-auth-state';

const defaultState: AuthState = {
  isAuthenticated: false,
  username: '',
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredAuth(): AuthState {
  const raw = window.sessionStorage.getItem(STORAGE_KEY);

  if (!raw) {
    return defaultState;
  }

  try {
    return JSON.parse(raw) as AuthState;
  } catch {
    return defaultState;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>(readStoredAuth);

  useEffect(() => {
    if (authState.isAuthenticated) window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(authState));
    else window.sessionStorage.removeItem(STORAGE_KEY);
  }, [authState]);

  useEffect(() => {
    if (!authState.isAuthenticated || !authState.refreshToken || authState.identityType === 'guest') return undefined;
    const refresh = async () => {
      try {
        const token = await refreshAccessToken(authState.refreshToken!);
        setAuthState((current) => ({ ...current, token }));
      } catch { setAuthState(defaultState); }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 20 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, [authState.isAuthenticated, authState.refreshToken, authState.identityType]);



  // 监听 401 未授权事件（由 request.ts 响应拦截器触发）
  useEffect(() => {
    const handler = () => {
      setAuthState(defaultState);
    };
    window.addEventListener('auth:unauthorized', handler);
    return () => window.removeEventListener('auth:unauthorized', handler);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...authState,
      login: (auth) =>
        setAuthState({
          isAuthenticated: true,
          username: auth.username,
          token: auth.token,
          refreshToken: auth.refreshToken,
          identityType: auth.identityType ?? 'user',
          userInfo: auth.userInfo ?? { username: auth.username },
        }),
      logout: () => setAuthState(defaultState),
      markUnauthorized: () => setAuthState(defaultState),
    }),
    [authState],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
}
