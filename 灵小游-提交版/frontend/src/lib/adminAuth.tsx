import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';

const ADMIN_TOKEN_KEY = 'lingshanAdminToken';

/** Check if an admin token exists and is valid (not expired JWT) */
function hasValidAdminToken(): boolean {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  if (!token) return false;
  try {
    // JWT: check if expired
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      localStorage.removeItem(ADMIN_TOKEN_KEY);
      return false;
    }
    return true;
  } catch {
    // Not a valid JWT, still check if it works
    return !!token;
  }
}

export function getAdminToken(): string {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || '';
}

export function setAdminToken(token: string): void {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}

/** Auth guard: redirect to /admin login page if no admin token */
export function RequireAdminAuth({ children }: { children: ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [valid, setValid] = useState(false);

  useEffect(() => {
    // Quick verification by calling a lightweight admin endpoint
    const token = getAdminToken();
    if (!token) {
      setValid(false);
      setChecking(false);
      return;
    }

    fetch('/api/admin/settings', {
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(r => {
        if (r.ok) {
          setValid(true);
        } else {
          clearAdminToken();
          setValid(false);
        }
      })
      .catch(() => setValid(false))
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#666' }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>🔐</div>
          <div>验证管理员身份...</div>
        </div>
      </div>
    );
  }

  if (!valid) {
    // Force full page reload to server-rendered HTML login page
    // (avoids React Router loop since /admin is also a React route)
    window.location.replace('/admin');
    return null;
  }

  return <>{children}</>;
}
