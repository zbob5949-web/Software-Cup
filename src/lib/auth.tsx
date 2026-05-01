import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

type AuthState = {
  isAuthenticated: boolean;
  username: string;
};

type AuthContextValue = AuthState & {
  login: (username: string) => void;
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
  const [authState, setAuthState] = useState<AuthState>(defaultState);

  useEffect(() => {
    setAuthState(readStoredAuth());
  }, []);

  useEffect(() => {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(authState));
  }, [authState]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...authState,
      login: (username: string) =>
        setAuthState({
          isAuthenticated: true,
          username,
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
