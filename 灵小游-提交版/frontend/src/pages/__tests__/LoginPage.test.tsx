import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../api/request';
import { AuthProvider } from '../../lib/auth';
import { LoginPage } from '../LoginPage';

const mocks = vi.hoisted(() => ({
  loginUser: vi.fn(),
  sendLoginCode: vi.fn(),
  guestLogin: vi.fn(),
}));

vi.mock('../../api/auth', () => ({
  loginUser: mocks.loginUser,
  sendLoginCode: mocks.sendLoginCode,
  guestLogin: mocks.guestLogin,
}));

vi.mock('../../lib/i18n', () => ({
  getLocale: () => 'en-US',
  t: (key: string) => {
    const messages: Record<string, string> = {
      'login.phoneLabel': 'Phone',
      'login.phonePlaceholder': 'Enter phone',
      'login.phoneRequired': 'Phone is required',
      'login.phoneInvalid': 'Phone is invalid',
      'login.forgotPassword': 'Forgot password',
      'login.smsLoginTab': 'SMS Login',
      'login.passwordLoginTab': 'Password Login',
      'login.smsCodeLabel': 'SMS Code',
      'login.smsCodePlaceholder': 'Enter code',
      'login.getSmsCode': 'Get Code',
      'login.button': 'Login',
      'login.loading': 'Logging in...',
      'login.welcomeBack': 'Welcome back',
      'login.welcomeBackSub': 'Continue',
      'password.label': 'Password',
      'password.required': 'Password required',
      'password.show': 'Show password',
      'password.hide': 'Hide password',
      'login.serverError': 'Server error',
      'login.success': 'Login success',
      'login.registerHint': 'Need account?',
      'login.registerLink': 'Register',
      'login.guestEntry': 'Guest',
    };
    return messages[key] ?? key;
  },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  function renderPage() {
    return render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/home" element={<div>Home Page</div>} />
            <Route path="/admin" element={<div>Admin Page</div>} />
            <Route path="/forgot-password" element={<div>Forgot Password</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );
  }

  it('logs in successfully and persists auth state before redirecting home', async () => {
    const user = userEvent.setup();
    mocks.loginUser.mockResolvedValue({
      username: '13800138000',
      token: 'token-1',
      userInfo: { username: '13800138000' },
    });
    renderPage();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.type(screen.getByLabelText('Password'), '123456');
    await user.click(screen.getByRole('button', { name: 'Login' }));

    expect(mocks.loginUser).toHaveBeenCalledWith({
      username: '13800138000',
      password: '123456',
    });

    await waitFor(() => {
      expect(screen.getByText('Home Page')).toBeInTheDocument();
    });

    const stored = window.sessionStorage.getItem('scenic-auth-state') ?? '';
    expect(stored).toContain('13800138000');
    expect(stored).toContain('token-1');
  });

  it('keeps submit disabled until valid input is provided', async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByRole('button', { name: 'Login' })).toBeDisabled();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.type(screen.getByLabelText('Password'), '123456');

    expect(screen.getByRole('button', { name: 'Login' })).toBeEnabled();
  });

  it('requests login sms code and starts countdown', async () => {
    const user = userEvent.setup();
    mocks.sendLoginCode.mockResolvedValue({
      code: 200,
      msg: 'Code sent',
      data: { code: '5678' },
    });
    renderPage();

    await user.click(screen.getByRole('tab', { name: 'SMS Login' }));
    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.click(screen.getByRole('button', { name: 'Get Code' }));

    expect(mocks.sendLoginCode).toHaveBeenCalledWith('13800138000');
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '60s' })).toBeDisabled();
    });
  });

  it('shows backend error feedback when login fails', async () => {
    const user = userEvent.setup();
    mocks.loginUser.mockRejectedValue(new ApiError(40101, 'Bad credentials'));
    renderPage();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.type(screen.getByLabelText('Password'), 'wrong-pass');
    expect(screen.getByRole('button', { name: 'Login' })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: 'Login' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Bad credentials');
  });

  it('disables submit and shows loading state while request is pending', async () => {
    const user = userEvent.setup();
    let resolveLogin: ((value: { username: string; userInfo: { username: string } }) => void) | undefined;
    mocks.loginUser.mockImplementation(() => new Promise((resolve) => { resolveLogin = resolve; }));
    renderPage();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.type(screen.getByLabelText('Password'), '123456');
    await user.click(screen.getByRole('button', { name: 'Login' }));

    expect(screen.getByRole('button', { name: 'Logging in...' })).toBeDisabled();

    resolveLogin?.({
      username: '13800138000',
      userInfo: { username: '13800138000' },
    });

    await waitFor(() => {
      expect(screen.getByText('Home Page')).toBeInTheDocument();
    });
  });

  it('routes an administrator to admin only from the admin login tab', async () => {
    const user = userEvent.setup();
    mocks.loginUser.mockResolvedValue({
      username: 'admin',
      token: 'admin-token',
      userInfo: { username: 'admin', role: 'admin' },
    });
    renderPage();

    await user.click(screen.getByRole('tab', { name: '管理员登录' }));
    await user.type(screen.getByLabelText('Phone'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'admin123');
    await user.click(screen.getByRole('button', { name: 'Login' }));

    await waitFor(() => expect(screen.getByText('Admin Page')).toBeInTheDocument());
    expect(window.localStorage.getItem('lingshanAdminToken')).toBe('admin-token');
    expect(window.sessionStorage.getItem('scenic-auth-state')).toBeNull();
  });

  it('does not redirect an administrator to admin from the user login tab', async () => {
    const user = userEvent.setup();
    mocks.loginUser.mockResolvedValue({
      username: 'admin',
      token: 'admin-token',
      userInfo: { username: 'admin', role: 'admin' },
    });
    renderPage();

    await user.type(screen.getByLabelText('Phone'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'admin123');
    await user.click(screen.getByRole('button', { name: 'Login' }));

    expect(await screen.findByRole('status')).toHaveTextContent('当前账号是管理员账号，请切换到管理员登录');
    expect(screen.queryByText('Admin Page')).not.toBeInTheDocument();
  });
});
