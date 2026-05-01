import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ApiError, loginUser } from '../lib/api';
import { useAuth } from '../lib/auth';
import { getLocale, t } from '../lib/i18n';

type LocationState = {
  username?: string;
  successMessage?: string;
};

type FeedbackState = {
  message: string;
  tone: 'success' | 'error';
};

export function LoginPage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, login } = useAuth();
  const state = (location.state ?? {}) as LocationState;
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(
    state.successMessage
      ? { message: state.successMessage, tone: 'success' }
      : null,
  );
  const [username, setUsername] = useState(state.username ?? '');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (!feedback) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setFeedback(null), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [feedback]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!username.trim()) {
      setFeedback({ message: t('username.required', locale), tone: 'error' });
      usernameRef.current?.focus();
      return;
    }

    if (!password) {
      setFeedback({ message: t('password.required', locale), tone: 'error' });
      passwordRef.current?.focus();
      return;
    }

    setSubmitting(true);

    try {
      await loginUser({
        username: username.trim(),
        password,
      });
      login(username.trim());
      navigate('/chat', {
        state: {
          successMessage: t('login.success', locale),
        },
      });
    } catch (error) {
      const status = error instanceof ApiError ? error.status : -1;

      if (status === 400 || status === 401 || status === 403) {
        setFeedback({ message: t('login.invalid', locale), tone: 'error' });
      } else {
        setFeedback({ message: t('login.serverError', locale), tone: 'error' });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="hero-copy">
          <h1 id="login-title">{t('login.title', locale)}</h1>
          <p className="subtitle">{t('login.subtitle', locale)}</p>
        </div>
        {feedback ? (
          <div
            className={feedback.tone === 'success' ? 'inline-success' : 'inline-error'}
            role="status"
            aria-live="polite"
          >
            {feedback.message}
          </div>
        ) : null}
        <form noValidate onSubmit={handleSubmit}>
          <label className="field" htmlFor="login-username">
            <span>{t('username.label', locale)}</span>
          </label>
          <input
            ref={usernameRef}
            id="login-username"
            className="input"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder={t('login.usernamePlaceholder', locale)}
            aria-label={t('username.label', locale)}
          />

          <label className="field" htmlFor="login-password">
            <span>{t('password.label', locale)}</span>
          </label>
          <div className="password-row">
            <input
              ref={passwordRef}
              id="login-password"
              className="input input-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('login.passwordPlaceholder', locale)}
              aria-label={t('password.label', locale)}
            />
            <button
              type="button"
              className="toggle-button"
              aria-label={showPassword ? t('password.hide', locale) : t('password.show', locale)}
              aria-pressed={showPassword}
              onClick={() => setShowPassword((value) => !value)}
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
                focusable="false"
                className="toggle-icon"
              >
                <path
                  d="M2.2 12s3.4-6 9.8-6 9.8 6 9.8 6-3.4 6-9.8 6-9.8-6-9.8-6Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle
                  cx="12"
                  cy="12"
                  r={showPassword ? '2.8' : '3.2'}
                  fill={showPassword ? 'currentColor' : 'none'}
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
              </svg>
            </button>
          </div>

          <button type="submit" className="submit-button" disabled={submitting}>
            {submitting ? (
              <span className="button-content">
                <span className="spinner" aria-hidden="true" />
                {t('login.loading', locale)}
              </span>
            ) : (
              t('login.button', locale)
            )}
          </button>

          <p className="login-entry">
            <span>{t('login.registerHint', locale)}</span>
            <Link to="/register" className="login-link">
              {t('login.registerLink', locale)}
            </Link>
          </p>

          {isAuthenticated ? (
            <p className="login-entry">
              <Link to="/chat" className="login-link">
                {t('login.chatLink', locale)}
              </Link>
            </p>
          ) : null}
        </form>
      </section>
    </main>
  );
}
