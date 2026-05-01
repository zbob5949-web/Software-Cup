import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { RegisterApiError, registerUser } from '../lib/api';
import { getLocale, t } from '../lib/i18n';
import { getStatusMessage, type ToastState } from '../lib/toast';
import {
  getPasswordStrength,
  validatePassword,
  validateUsername,
} from '../lib/validation';

function createToast(message: string, tone: ToastState['tone']): ToastState {
  return {
    id: Date.now(),
    message,
    tone,
  };
}

export function RegisterPage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [usernameTouched, setUsernameTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const usernameValid = validateUsername(username);
  const passwordValid = validatePassword(password);
  const formValid = usernameValid && passwordValid;
  const strength = useMemo(() => getPasswordStrength(password), [password]);
  const passwordRules = useMemo(
    () => [
      { key: 'length', label: t('password.rule.length', locale), passed: password.length >= 8 },
      {
        key: 'uppercase',
        label: t('password.rule.uppercase', locale),
        passed: /[A-Z]/.test(password),
      },
      { key: 'number', label: t('password.rule.number', locale), passed: /\d/.test(password) },
      {
        key: 'special',
        label: t('password.rule.special', locale),
        passed: /[^A-Za-z\d]/.test(password),
      },
    ],
    [locale, password],
  );

  useEffect(() => {
    if (!toast) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUsernameTouched(true);
    setPasswordTouched(true);

    if (!username.trim()) {
      usernameRef.current?.focus();
      setToast(createToast(t('username.required', locale), 'error'));
      return;
    }

    if (!password) {
      passwordRef.current?.focus();
      setToast(createToast(t('password.required', locale), 'error'));
      return;
    }

    if (!formValid) {
      const invalidTarget = !usernameValid ? usernameRef.current : passwordRef.current;
      invalidTarget?.focus();
      setToast(
        createToast(
          !usernameValid ? t('username.invalid', locale) : t('password.invalid', locale),
          'error',
        ),
      );
      return;
    }

    setSubmitting(true);

    try {
      await registerUser({ username, password });
      setToast(createToast(t('toast.success', locale), 'success'));
      window.setTimeout(() => {
        navigate('/login', {
          state: {
            username,
            successMessage: t('success.redirect', locale),
          },
        });
      }, 500);
    } catch (error) {
      const status = error instanceof RegisterApiError ? error.status : -1;
      setToast(createToast(getStatusMessage(status, locale), 'error'));
    } finally {
      setSubmitting(false);
    }
  }

  const usernameHint = !username && !usernameTouched
    ? ''
    : username
      ? usernameValid
        ? t('username.valid', locale)
        : t('username.invalid', locale)
      : t('username.required', locale);

  const passwordHint = !passwordTouched
    ? ''
    : !password
      ? t('password.required', locale)
      : passwordValid
        ? ''
        : t('password.invalid', locale);

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="register-title">
        <div className="hero-copy">
          <h1 id="register-title">{t('register.title', locale)}</h1>
          <p className="subtitle">{t('register.subtitle', locale)}</p>
        </div>

        <form noValidate onSubmit={handleSubmit}>
          <label className="field" htmlFor="username">
            <span>{t('username.label', locale)}</span>
          </label>
          <input
            ref={usernameRef}
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            onBlur={() => setUsernameTouched(true)}
            placeholder={t('username.placeholder', locale)}
            aria-invalid={usernameTouched && !usernameValid}
            aria-describedby="username-hint"
            className={usernameTouched && !usernameValid ? 'input input-error' : 'input'}
          />
          <p
            id="username-hint"
            className={usernameTouched && !usernameValid ? 'hint hint-error' : 'hint'}
            aria-live="polite"
          >
            {usernameHint}
          </p>

          <label className="field" htmlFor="password">
            <span>{t('password.label', locale)}</span>
          </label>
          <div className="password-row">
            <input
              ref={passwordRef}
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onBlur={() => setPasswordTouched(true)}
              placeholder={t('password.placeholder', locale)}
              aria-invalid={passwordTouched && !passwordValid}
              aria-describedby="password-hint password-strength"
              className={passwordTouched && !passwordValid ? 'input input-password input-error' : 'input input-password'}
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
          <p className="password-note">{t('password.ruleSummary', locale)}</p>
          <p
            id="password-hint"
            className={passwordTouched && !passwordValid ? 'hint hint-error' : 'hint'}
            aria-live="polite"
          >
            {passwordHint}
          </p>

          {password ? (
            <ul className="password-rules" aria-label={t('password.ruleSummary', locale)}>
              {passwordRules.map((rule) => (
                <li
                  key={rule.key}
                  className={rule.passed ? 'password-rule is-met' : 'password-rule'}
                >
                  <span className="rule-dot" aria-hidden="true" />
                  <span>{rule.label}</span>
                </li>
              ))}
            </ul>
          ) : null}

          <div className="strength" id="password-strength" aria-live="polite">
            <span className={`strength-bar strength-${strength}`} aria-hidden="true" />
            <span>
              {strength === 'weak' && t('password.strength.weak', locale)}
              {strength === 'medium' && t('password.strength.medium', locale)}
              {strength === 'strong' && t('password.strength.strong', locale)}
            </span>
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={!formValid || submitting}
            aria-disabled={!formValid || submitting}
          >
            {submitting ? (
              <span className="button-content">
                <span className="spinner" aria-hidden="true" />
                {t('register.loading', locale)}
              </span>
            ) : (
              t('register.button', locale)
            )}
          </button>

          <p className="login-entry">
            <span>{t('register.loginHint', locale)}</span>
            <Link to="/login" className="login-link">
              {t('register.loginLink', locale)}
            </Link>
          </p>
        </form>
      </section>

      {toast ? (
        <div
          className={`toast toast-${toast.tone}`}
          role="alert"
          aria-live="assertive"
        >
          {toast.message}
        </div>
      ) : null}
    </main>
  );
}
