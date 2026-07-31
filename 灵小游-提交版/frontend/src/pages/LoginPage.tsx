import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/request';
import { guestLogin, loginUser, sendLoginCode } from '../api/auth';
import { useAuth } from '../lib/auth';
import { setAdminToken } from '../lib/adminAuth';
import { getLocale, t } from '../lib/i18n';

type LocationState = { username?: string; successMessage?: string };
type LoginMode = 'password' | 'sms';
const phonePattern = /^1\d{10}$/;

export function LoginPage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const location = useLocation();
  const { login, logout } = useAuth();
  const [loginRole, setLoginRole] = useState<'user' | 'admin'>('user');
  const [showWelcome, setShowWelcome] = useState(true);
  const phoneRef = useRef<HTMLInputElement>(null);
  const state = (location.state ?? {}) as LocationState;

  const [mode, setMode] = useState<LoginMode>('password');
  const [phone, setPhone] = useState(state.username ?? '');
  const [password, setPassword] = useState('');
  const [smsCode, setSmsCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ message: string; tone: 'success' | 'error' } | null>(
    state.successMessage ? { message: state.successMessage, tone: 'success' } : null,
  );
  const [smsCountdown, setSmsCountdown] = useState(0);

  useEffect(() => {
    if (!feedback) return undefined;
    const id = window.setTimeout(() => setFeedback(null), 3000);
    return () => window.clearTimeout(id);
  }, [feedback]);

  useEffect(() => {
    if (smsCountdown <= 0) return undefined;
    const id = window.setTimeout(() => setSmsCountdown((c) => c - 1), 1000);
    return () => window.clearTimeout(id);
  }, [smsCountdown]);

  const formValid = mode === 'password'
    ? phone.trim() !== '' && password !== ''
    : phone.trim() !== '' && smsCode.trim() !== '';

  const handleGetSmsCode = useCallback(async () => {
    if (smsCountdown > 0) return;
    const trimmedPhone = phone.trim();

    if (!trimmedPhone) {
      setFeedback({ message: t('login.phoneRequired', locale), tone: 'error' });
      return;
    }

    if (!phonePattern.test(trimmedPhone)) {
      setFeedback({ message: t('login.phoneInvalid', locale), tone: 'error' });
      return;
    }

    try {
      const response = await sendLoginCode(trimmedPhone);
      setSmsCountdown(60);
      window.alert(`验证码：${response.data?.code ?? ''}`);
      setFeedback({ message: response.msg, tone: 'success' });
    } catch (error) {
      setFeedback({
        message: error instanceof ApiError || error instanceof Error ? error.message : t('login.serverError', locale),
        tone: 'error',
      });
    }
  }, [phone, smsCountdown, locale]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!phone.trim()) {
      setFeedback({ message: t('login.phoneRequired', locale), tone: 'error' });
      phoneRef.current?.focus();
      return;
    }

    if (mode === 'password' && !password) {
      setFeedback({ message: t('password.required', locale), tone: 'error' });
      return;
    }

    if (mode === 'sms') {
      if (!smsCode.trim()) {
        setFeedback({ message: t('login.smsCodeLabel', locale) + t('login.phoneRequired', locale), tone: 'error' });
        return;
      }
    }

    setSubmitting(true);

    try {
      const auth = mode === 'password'
        ? await loginUser({ username: phone.trim(), password })
        : await loginUser({ username: phone.trim(), code: smsCode.trim() });
      const accountRole = auth.userInfo?.role;

      if (loginRole === 'admin') {
        if (accountRole !== 'admin' || !auth.token) {
          throw new Error('当前账号不是管理员账号，请切换到用户登录');
        }
        logout();
        setAdminToken(auth.token);
        navigate('/admin');
        return;
      }

      if (accountRole === 'admin') {
        throw new Error('当前账号是管理员账号，请切换到管理员登录');
      }

      login(auth);
      navigate('/home', { state: { successMessage: t('login.success', locale) } });
    } catch (error) {
      setFeedback({
        message: error instanceof ApiError || error instanceof Error ? error.message : t('login.serverError', locale),
        tone: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGuestEntry() {
    try {
      const result = await guestLogin();
      login({ username: `游客_${result.guest_id}`, token: result.token, identityType: 'guest' });
    } catch {
      // fallback: just go to home without auth
    }
    navigate('/home');
  }

  return (
    <main className="mobile-auth-page">
      <div className="mobile-auth-card">
        {/* Welcome */}
        {showWelcome ? <div className="mobile-welcome">
          <h1>{t('login.welcomeBack', locale)}</h1>
          <p>{t('login.welcomeBackSub', locale)}</p>
        </div> : null}

        {/* Unified role entry: user and administrator share the same login form. */}
        <div className="mobile-tabs mobile-role-tabs" role="tablist">
          <button type="button" role="tab" className={`mobile-tab${loginRole === 'user' ? ' active' : ''}`} onClick={() => setLoginRole('user')}>用户登录</button>
          <button type="button" role="tab" className={`mobile-tab${loginRole === 'admin' ? ' active' : ''}`} onClick={() => { setLoginRole('admin'); setMode('password'); }}>管理员登录</button>
        </div>
        {/* Tab Switcher */}
        <div className="mobile-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            className={`mobile-tab${mode === 'password' ? ' active' : ''}`}
            aria-selected={mode === 'password'}
            onClick={() => setMode('password')}
          >
            {t('login.passwordLoginTab', locale)}
          </button>
          <button
            type="button"
            role="tab"
            className={`mobile-tab${mode === 'sms' ? ' active' : ''}`}
            aria-selected={mode === 'sms'}
            onClick={() => setMode('sms')}
          >
            {t('login.smsLoginTab', locale)}
          </button>
        </div>

        {/* Feedback */}
        {feedback ? (
          <div className={`mobile-feedback mobile-feedback-${feedback.tone}`} role="status">
            {feedback.message}
          </div>
        ) : null}

        <form noValidate onSubmit={handleSubmit}>
          {/* Phone / Account */}
          <label className="mobile-field">
            <span className="mobile-label">{t('login.phoneLabel', locale)}</span>
            <input
              ref={phoneRef}
              className="mobile-input"
              type="text"
              autoComplete="username"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t('login.phonePlaceholder', locale)}
            />
          </label>

          {/* Password mode */}
          {mode === 'password' ? (
            <label className="mobile-field">
              <span className="mobile-label">{t('password.label', locale)}</span>
              <div className="mobile-password-row">
                <input
                  className="mobile-input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t('login.passwordPlaceholder', locale)}
                />
                <button
                  type="button"
                  className="mobile-toggle-btn"
                  aria-label={showPassword ? t('password.hide', locale) : t('password.show', locale)}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  <svg className="mobile-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M2.2 12s3.4-6 9.8-6 9.8 6 9.8 6-3.4 6-9.8 6-9.8-6-9.8-6Z"
                      fill="none" stroke="currentColor" strokeWidth="1.8"
                      strokeLinecap="round" strokeLinejoin="round"
                    />
                    <circle cx="12" cy="12" r={showPassword ? '2.8' : '3.2'}
                      fill={showPassword ? 'currentColor' : 'none'}
                      stroke="currentColor" strokeWidth="1.8"
                    />
                  </svg>
                </button>
              </div>
            </label>
          ) : (
            /* SMS Code mode */
            <label className="mobile-field">
              <span className="mobile-label">{t('login.smsCodeLabel', locale)}</span>
              <div className="mobile-sms-row">
                <input
                  className="mobile-input"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={smsCode}
                  onChange={(e) => setSmsCode(e.target.value)}
                  placeholder={t('login.smsCodePlaceholder', locale)}
                />
                <button
                  type="button"
                  className="mobile-sms-btn"
                  disabled={smsCountdown > 0}
                  onClick={handleGetSmsCode}
                >
                  {smsCountdown > 0 ? `${smsCountdown}s` : t('login.getSmsCode', locale)}
                </button>
              </div>
            </label>
          )}

          {/* Forgot Password */}
          {mode === 'password' ? (
            <div className="mobile-forgot-row">
              <Link to="/forgot-password" className="mobile-forgot-link">
                {t('login.forgotPassword', locale)}
              </Link>
            </div>
          ) : null}

          {/* Submit */}
          <button type="submit" className="mobile-submit-btn" disabled={!formValid || submitting}>
            {submitting ? (
              <span className="mobile-btn-content">
                <span className="mobile-btn-spinner" />
                {t('login.loading', locale)}
              </span>
            ) : (
              t('login.button', locale)
            )}
          </button>

          {/* Register Link */}
          <p className="mobile-bottom-link">
            <span>{t('login.registerHint', locale)}</span>
            <Link to="/register">{t('login.registerLink', locale)}</Link>
          </p>

          {/* Guest Entry */}
          <button type="button" className="mobile-guest-btn" onClick={handleGuestEntry}>
            {t('login.guestEntry', locale)}
          </button>
        </form>
      </div>
    </main>
  );
}
