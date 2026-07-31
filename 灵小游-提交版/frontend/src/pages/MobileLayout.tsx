import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { PageTransition } from '../components/PageTransition';
import { getLocale, t } from '../lib/i18n';

export function MobileLayout() {
  const locale = getLocale();
  const location = useLocation();
  const hideNav = location.pathname.startsWith('/ai-chat');

  return (
    <div className="mobile-app-shell">
      <div className="mobile-app-content">
        <PageTransition type="slide">
          <Outlet />
        </PageTransition>
      </div>

      {!hideNav ? (
        <nav className="bottom-nav" aria-label="main-navigation">
          <NavLink to="/home" className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>{t('nav.home', locale)}</span>
          </NavLink>

          <NavLink to="/guide" className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
            </svg>
            <span>{t('nav.guide', locale)}</span>
          </NavLink>

          <NavLink to="/ai-chat" className={({ isActive }) => `bottom-nav-item ai${isActive ? ' active' : ''}`}>
            <div className="ai-nav-pill">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <span className="ai-nav-label">{t('nav.aiGuide', locale)}</span>
          </NavLink>

          <NavLink to="/profile" className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>{t('nav.profile', locale)}</span>
          </NavLink>
        </nav>
      ) : null}
    </div>
  );
}
