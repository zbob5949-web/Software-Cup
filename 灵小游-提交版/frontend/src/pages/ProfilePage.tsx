import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { logoutUser } from '../api/auth';
import { submitFeedback } from '../api/feedback';
import { Button } from '../components/ui/Button';
import { useAuth } from '../lib/auth';
import { getLocale, t } from '../lib/i18n';

/* ===== Icon primitives ===== */
const icons = {
  star: (
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </>
  ),
  message: (
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  ),
  edit: (
    <>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </>
  ),
  settings: (
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </>
  ),
  helpCircle: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </>
  ),
  receipt: (
    <>
      <path d="M4 3h16v18l-3-2-3 2-3-2-3 2-4-2V3z" />
      <line x1="8" y1="8" x2="16" y2="8" />
      <line x1="8" y1="12" x2="16" y2="12" />
    </>
  ),
} as const;

function MenuIcon({ name }: { name: keyof typeof icons }) {
  const path = icons[name];
  if (!path) return null;
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {path}
    </svg>
  );
}

/* ===== Menu items config ===== */
const menuItems = [
  { key: 'favorites' as const, icon: 'star' as const, route: '/favorites' },
  { key: 'orders' as const, icon: 'receipt' as const, route: '/orders' },
  { key: 'faq' as const, icon: 'helpCircle' as const, route: '/faq' },
  { key: 'history' as const, icon: 'clock' as const, route: '/history' },
  { key: 'qa' as const, icon: 'info' as const, route: '/ai-chat' },
  { key: 'feedback' as const, icon: 'edit' as const, route: null },
  { key: 'about' as const, icon: 'message' as const, route: null },
];

const menuLabelKeys: Record<string, Parameters<typeof t>[0]> = {
  favorites: 'profile.favorites',
  orders: 'profile.orders',
  faq: 'profile.faq',
  history: 'profile.history',
  qa: 'profile.qa',
  feedback: 'profile.feedback',
  about: 'profile.about',
};

/* ===== Bottom Sheet Modal ===== */
function SheetModal({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="voice-panel-overlay voice-panel--open" onClick={onClose}>
      <div
        className="voice-panel"
        style={{ maxWidth: 360, padding: 24 }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

/* ===== Feedback Modal ===== */
function FeedbackModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [type, setType] = useState('其他');
  const [rating, setRating] = useState(5);
  const [content, setContent] = useState('');
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit() {
    if (!content.trim()) return;
    setSending(true);
    try {
      await submitFeedback({ type, rating, content: content.trim() });
      setDone(true);
      setTimeout(() => {
        onClose();
        setDone(false);
        setContent('');
        setRating(5);
        setType('其他');
      }, 1500);
    } catch {
      // ignore
    } finally {
      setSending(false);
    }
  }

  return (
    <SheetModal open={open} onClose={onClose}>
      <h3 className="profile-modal-title">提交反馈</h3>
      {done ? (
        <p className="profile-modal-success">感谢您的反馈！</p>
      ) : (
        <>
          <div className="profile-modal-label">评分</div>
          <div className="profile-star-row">
            {[1, 2, 3, 4, 5].map((n) => (
              <span
                key={n}
                className={`profile-star${n <= rating ? ' active' : ''}`}
                onClick={() => setRating(n)}
              >
                ★
              </span>
            ))}
          </div>

          <select
            className="profile-modal-select"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {['景点讲解', '路线推荐', '语音交互', '服务体验', '其他'].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>

          <textarea
            className="profile-modal-textarea"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="请输入您的反馈内容..."
            rows={3}
          />

          <div className="profile-modal-actions">
            <Button variant="secondary" onClick={onClose} disabled={sending}>取消</Button>
            <Button variant="primary" onClick={handleSubmit} disabled={sending || !content.trim()} isLoading={sending}>
              提交反馈
            </Button>
          </div>
        </>
      )}
    </SheetModal>
  );
}

/* ===== About Modal ===== */
function AboutModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <SheetModal open={open} onClose={onClose}>
      <h3 className="profile-modal-title">关于</h3>
      <p className="profile-modal-about-text">
        灵山智游 · AI 智能导览系统
        <br />
        版本 1.0.0
        <br />
        中国软件杯 A5 赛题
      </p>
      <div className="profile-modal-actions" style={{ marginTop: 16 }}>
        <Button variant="ghost" onClick={onClose}>关闭</Button>
      </div>
    </SheetModal>
  );
}

/* ===== Page ===== */
export function ProfilePage() {
  const locale = getLocale();
  const navigate = useNavigate();
  const { isAuthenticated, username, logout } = useAuth();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);

  function handleLogout() {
    logoutUser().finally(() => { logout(); navigate('/login'); });
  }

  function handleMenuClick(key: string, item: (typeof menuItems)[number]) {
    if (item.route) { navigate(item.route); return; }
    if (key === 'feedback') setFeedbackOpen(true);
    if (key === 'about') setAboutOpen(true);
  }

  return (
    <div className="profile-page">
      {/* Header */}
      <section className="profile-header">
        <div className="profile-avatar">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
        <h2>{isAuthenticated ? username : t('profile.guestTitle', locale)}</h2>
        <p>{isAuthenticated ? t('profile.memberDesc', locale) : t('profile.guestSub', locale)}</p>
      </section>

      {/* Login CTA for guests */}
      {!isAuthenticated && (
        <Button
          variant="secondary"
          size="lg"
          className="profile-login-btn"
          onClick={() => navigate('/login')}
        >
          {t('profile.loginPrompt', locale)}
        </Button>
      )}

      {/* Service Menu */}
      <section className="profile-menu-section">
        <div className="profile-menu-header">
          <h3>{t('profile.serviceTitle', locale)}</h3>
          <p>{t('profile.serviceDesc', locale)}</p>
        </div>
        <div className="profile-menu">
          {menuItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className="profile-menu-item"
              onClick={() => handleMenuClick(item.key, item)}
            >
              <span className="profile-menu-icon"><MenuIcon name={item.icon} /></span>
              <span className="profile-menu-label">{t(menuLabelKeys[item.key], locale)}</span>
              <svg className="profile-menu-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          ))}
        </div>
      </section>

      {/* Logout */}
      {isAuthenticated && (
        <Button variant="danger" size="lg" className="profile-logout-btn" onClick={handleLogout}>
          {t('profile.logout', locale)}
        </Button>
      )}

      {/* Modals */}
      <FeedbackModal open={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
      <AboutModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </div>
  );
}
