import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/request';
import { registerUser, sendRegisterCode } from '../api/auth';
import { getLocale, t } from '../lib/i18n';
import { getPasswordStrength } from '../lib/validation';

const phonePattern = /^1\d{10}$/;

export function RegisterPage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const phoneRef = useRef<HTMLInputElement>(null);

  const [phone, setPhone] = useState('');
  const [smsCode, setSmsCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ message: string; tone: 'success' | 'error' } | null>(null);
  const [smsCountdown, setSmsCountdown] = useState(0);

  const strength = useMemo(() => getPasswordStrength(password), [password]);
  const passwordsMatch = confirmPassword === '' || password === confirmPassword;

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

  const passwordFilled = password.trim() !== '';
  const formValid = phone.trim() !== '' && passwordFilled && passwordsMatch && agreed;

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
      const response = await sendRegisterCode(trimmedPhone);
      setSmsCountdown(60);
      window.alert(`验证码：${response.data?.code ?? ''}`);
      setFeedback({ message: response.msg, tone: 'success' });
    } catch (error) {
      setFeedback({
        message: error instanceof ApiError ? error.message : t('toast.serverError', locale),
        tone: 'error',
      });
    }
  }, [phone, smsCountdown, locale]);

  const handleThirdParty = useCallback((platform: 'wechat' | 'qq') => {
    const key = platform === 'wechat' ? 'register.thirdPartyWechatHint' : 'register.thirdPartyQQHint';
    setFeedback({ message: t(key, locale), tone: 'error' });
  }, [locale]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!phone.trim()) {
      setFeedback({ message: t('login.phoneRequired', locale), tone: 'error' });
      phoneRef.current?.focus();
      return;
    }

    if (!smsCode.trim()) {
      setFeedback({ message: t('login.smsCodeLabel', locale) + '不能为空', tone: 'error' });
      return;
    }

    if (!passwordFilled) {
      setFeedback({ message: t('password.required', locale), tone: 'error' });
      return;
    }

    if (password !== confirmPassword) {
      setFeedback({ message: t('register.passwordMismatch', locale), tone: 'error' });
      return;
    }

    if (!agreed) {
      setFeedback({ message: t('register.agreementRequired', locale), tone: 'error' });
      return;
    }

    setSubmitting(true);

    try {
      await registerUser({
        username: phone.trim(),
        password,
        code: smsCode.trim(),
        confirm_password: confirmPassword,
      });
      navigate('/login', {
        state: { username: phone.trim(), successMessage: t('success.redirect', locale) },
      });
    } catch (error) {
      setFeedback({
        message: error instanceof ApiError ? error.message : t('toast.serverError', locale),
        tone: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mobile-auth-page">
      <div className="mobile-auth-card">
        {/* Welcome */}
        <div className="mobile-welcome">
          <h1>{t('register.welcomeTitle', locale)}</h1>
          <p>{t('register.welcomeSubtitle2', locale)}</p>
        </div>

        {/* Feedback */}
        {feedback ? (
          <div className={`mobile-feedback mobile-feedback-${feedback.tone}`} role="status">
            {feedback.message}
          </div>
        ) : null}

        <form noValidate onSubmit={handleSubmit}>
          {/* Phone */}
          <label className="mobile-field">
            <span className="mobile-label">{t('register.phoneLabel', locale)}</span>
            <input
              ref={phoneRef}
              className="mobile-input"
              type="text"
              inputMode="numeric"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t('register.phonePlaceholder', locale)}
            />
          </label>

          {/* SMS Code */}
          <label className="mobile-field">
            <span className="mobile-label">{t('register.smsCodeLabel', locale)}</span>
            <div className="mobile-sms-row">
              <input
                className="mobile-input"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={smsCode}
                onChange={(e) => setSmsCode(e.target.value)}
                placeholder={t('register.smsCodePlaceholder', locale)}
              />
              <button
                type="button"
                className="mobile-sms-btn"
                disabled={smsCountdown > 0}
                onClick={handleGetSmsCode}
              >
                {smsCountdown > 0
                  ? `${smsCountdown}s`
                  : t('register.getSmsCode', locale)}
              </button>
            </div>
          </label>

          {/* Password */}
          <label className="mobile-field">
            <span className="mobile-label">{t('password.label', locale)}</span>
            <div className="mobile-password-row">
              <input
                className="mobile-input"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('password.placeholder', locale)}
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

          {/* Password Strength */}
          {password ? (
            <div className="mobile-pw-strength">
              <span className="mobile-pw-strength-bar">
                <span
                  className="mobile-pw-strength-fill"
                  style={{
                    width: strength === 'weak' ? '33%' : strength === 'medium' ? '66%' : '100%',
                    background: strength === 'weak' ? '#F3A6B3' : strength === 'medium' ? '#F0C48A' : 'var(--green)',
                  }}
                />
              </span>
              <span>
                {strength === 'weak' && t('password.strength.weak', locale)}
                {strength === 'medium' && t('password.strength.medium', locale)}
                {strength === 'strong' && t('password.strength.strong', locale)}
              </span>
            </div>
          ) : null}

          {/* Confirm Password */}
          <label className="mobile-field">
            <span className="mobile-label">{t('register.confirmPasswordLabel', locale)}</span>
            <div className="mobile-password-row">
              <input
                className={`mobile-input${!passwordsMatch ? ' mobile-input-error' : ''}`}
                type={showConfirm ? 'text' : 'password'}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t('register.confirmPasswordPlaceholder', locale)}
              />
              <button
                type="button"
                className="mobile-toggle-btn"
                aria-label={showConfirm ? t('password.hide', locale) : t('password.show', locale)}
                onClick={() => setShowConfirm((v) => !v)}
              >
                <svg className="mobile-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M2.2 12s3.4-6 9.8-6 9.8 6 9.8 6-3.4 6-9.8 6-9.8-6-9.8-6Z"
                    fill="none" stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round"
                  />
                  <circle cx="12" cy="12" r={showConfirm ? '2.8' : '3.2'}
                    fill={showConfirm ? 'currentColor' : 'none'}
                    stroke="currentColor" strokeWidth="1.8"
                  />
                </svg>
              </button>
            </div>
            {!passwordsMatch ? (
              <p className="mobile-input-hint">{t('register.passwordMismatch', locale)}</p>
            ) : null}
          </label>

          {/* Agreement */}
          <label className="mobile-agreement">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />
            <span>
              {t('register.agreePrefix', locale)}
              <a href="#" onClick={(e) => e.preventDefault()}>{t('register.terms', locale)}</a>
              {t('register.and', locale)}
              <a href="#" onClick={(e) => e.preventDefault()}>{t('register.privacy', locale)}</a>
            </span>
          </label>

          {/* Submit */}
          <button type="submit" className="mobile-submit-btn" disabled={!formValid || submitting}>
            {submitting ? (
              <span className="mobile-btn-content">
                <span className="mobile-btn-spinner" />
                {t('register.loading', locale)}
              </span>
            ) : (
              t('register.button', locale)
            )}
          </button>

          {/* Login Link */}
          <p className="mobile-bottom-link">
            <span>{t('register.loginHint', locale)}</span>
            <Link to="/login">{t('register.loginLink', locale)}</Link>
          </p>
        </form>

        {/* Third-Party Login */}
        <div className="mobile-divider">
          <span>{t('register.otherLoginMethods', locale)}</span>
        </div>
        <div className="mobile-third-party">
          {/* WeChat */}
          <button
            type="button"
            className="mobile-third-btn"
            aria-label={t('register.wechat', locale)}
            title={t('register.wechat', locale)}
            onClick={() => handleThirdParty('wechat')}
          >
            <svg className="mobile-third-icon" viewBox="0 0 24 24" fill="none">
              <path d="M8.5 11a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" fill="#07C160" />
              <path d="M15.5 11a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" fill="#07C160" />
              <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12c0 1.95.56 3.77 1.53 5.32L2 21l4.05-1.2A9.958 9.958 0 0 0 12 22Z" fill="#07C160" stroke="#07C160" strokeWidth="0.5" />
              <path d="M10.5 14.5c-2.5 0-4.5-1.8-4.5-4s2-4 4.5-4 4.5 1.8 4.5 4-2 4-4.5 4Z" fill="#fff" />
              <path d="M14.5 15.5c1.2 0 2.3-.4 3.2-1.2.8-.7 1.3-1.7 1.3-2.8 0-2.2-1.8-4-4-4-.3 0-.6 0-.9.1 1.1 1.3 1.7 3 1.7 4.9 0 .8-.2 1.6-.6 2.3.3.1.7.2 1.1.2Z" fill="#fff" />
            </svg>
          </button>

          {/* QQ */}
          <button
            type="button"
            className="mobile-third-btn"
            aria-label={t('register.qq', locale)}
            title={t('register.qq', locale)}
            onClick={() => handleThirdParty('qq')}
          >
            <svg className="mobile-third-icon" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="#12B7F5" />
              <path d="M18.5 14.5c-.3-2.5-1.8-4-2.5-4.5 0 0 .5-2.5 0-3.5s-1.5-2-4-2-4 1-4 2 0 3.5 0 3.5c-.7.5-2.2 2-2.5 4.5-.2 1.5.5 2.5 2 2.5.8 0 1.5-.5 2-1 .5.5 1.5 1 2.5 1s2-.5 2.5-1c.5.5 1.2 1 2 1 1.5 0 2.2-1 2-2.5Z" fill="#fff" />
            </svg>
          </button>
        </div>
      </div>
    </main>
  );
}
