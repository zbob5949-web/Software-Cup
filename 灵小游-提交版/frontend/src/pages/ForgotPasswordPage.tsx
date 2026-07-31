import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getLocale, t } from '../lib/i18n';

export function ForgotPasswordPage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const phoneRef = useRef<HTMLInputElement>(null);

  const [phone, setPhone] = useState('');
  const [smsCode, setSmsCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ message: string; tone: 'success' | 'error' } | null>(null);
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

  const passwordsMatch = confirmPassword === '' || newPassword === confirmPassword;
  const formValid = phone.trim() !== '' && newPassword.length >= 8 && passwordsMatch;

  const handleGetSmsCode = useCallback(() => {
    if (smsCountdown > 0) return;
    if (!phone.trim()) {
      setFeedback({ message: t('login.phoneRequired', locale), tone: 'error' });
      return;
    }
    setSmsCountdown(60);
    setFeedback({ message: t('forgot.smsNotAvailable', locale), tone: 'error' });
  }, [phone, smsCountdown, locale]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!phone.trim()) {
      setFeedback({ message: t('login.phoneRequired', locale), tone: 'error' });
      phoneRef.current?.focus();
      return;
    }

    if (newPassword.length < 8) {
      setFeedback({ message: t('password.invalid', locale), tone: 'error' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setFeedback({ message: t('forgot.passwordMismatch', locale), tone: 'error' });
      return;
    }

    setSubmitting(true);

    // Simulate API call — replace with real reset password API when available
    await new Promise((resolve) => window.setTimeout(resolve, 1000));

    setSubmitting(false);
    setFeedback({ message: t('forgot.success', locale), tone: 'success' });

    window.setTimeout(() => {
      navigate('/login', { state: { successMessage: t('forgot.success', locale) } });
    }, 1500);
  }

  return (
    <main className="mobile-auth-page">
      <div className="mobile-auth-card">
        {/* Header */}
        <div className="mobile-welcome">
          <h1>{t('forgot.title', locale)}</h1>
          <p>{t('forgot.subtitle', locale)}</p>
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
            <span className="mobile-label">{t('forgot.phoneLabel', locale)}</span>
            <input
              ref={phoneRef}
              className="mobile-input"
              type="text"
              inputMode="numeric"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t('forgot.phonePlaceholder', locale)}
            />
          </label>

          {/* SMS Code */}
          <label className="mobile-field">
            <span className="mobile-label">{t('forgot.smsCodeLabel', locale)}</span>
            <div className="mobile-sms-row">
              <input
                className="mobile-input"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={smsCode}
                onChange={(e) => setSmsCode(e.target.value)}
                placeholder={t('forgot.smsCodePlaceholder', locale)}
              />
              <button
                type="button"
                className="mobile-sms-btn"
                disabled={smsCountdown > 0}
                onClick={handleGetSmsCode}
              >
                {smsCountdown > 0
                  ? `${smsCountdown}s`
                  : t('forgot.getSmsCode', locale)}
              </button>
            </div>
          </label>

          {/* New Password */}
          <label className="mobile-field">
            <span className="mobile-label">{t('forgot.newPasswordLabel', locale)}</span>
            <div className="mobile-password-row">
              <input
                className="mobile-input"
                type={showNewPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder={t('forgot.newPasswordPlaceholder', locale)}
              />
              <button
                type="button"
                className="mobile-toggle-btn"
                aria-label={showNewPassword ? t('password.hide', locale) : t('password.show', locale)}
                onClick={() => setShowNewPassword((v) => !v)}
              >
                <svg className="mobile-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M2.2 12s3.4-6 9.8-6 9.8 6 9.8 6-3.4 6-9.8 6-9.8-6-9.8-6Z"
                    fill="none" stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round"
                  />
                  <circle cx="12" cy="12" r={showNewPassword ? '2.8' : '3.2'}
                    fill={showNewPassword ? 'currentColor' : 'none'}
                    stroke="currentColor" strokeWidth="1.8"
                  />
                </svg>
              </button>
            </div>
          </label>

          {/* Confirm Password */}
          <label className="mobile-field">
            <span className="mobile-label">{t('forgot.confirmPasswordLabel', locale)}</span>
            <div className="mobile-password-row">
              <input
                className={`mobile-input${!passwordsMatch ? ' mobile-input-error' : ''}`}
                type={showConfirm ? 'text' : 'password'}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t('forgot.confirmPasswordPlaceholder', locale)}
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
              <p className="mobile-input-hint">{t('forgot.passwordMismatch', locale)}</p>
            ) : null}
          </label>

          {/* Submit */}
          <button type="submit" className="mobile-submit-btn" disabled={!formValid || submitting}>
            {submitting ? (
              <span className="mobile-btn-content">
                <span className="mobile-btn-spinner" />
                {t('forgot.loading', locale)}
              </span>
            ) : (
              t('forgot.button', locale)
            )}
          </button>

          {/* Back to Login */}
          <p className="mobile-bottom-link">
            <Link to="/login">{t('forgot.backToLogin', locale)}</Link>
          </p>
        </form>
      </div>
    </main>
  );
}
