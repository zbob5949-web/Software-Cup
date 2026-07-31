import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../api/request';
import { RegisterPage } from '../RegisterPage';

const mocks = vi.hoisted(() => ({
  registerUser: vi.fn(),
  sendRegisterCode: vi.fn(),
}));

vi.mock('../../api/auth', () => ({
  registerUser: mocks.registerUser,
  sendRegisterCode: mocks.sendRegisterCode,
}));

vi.mock('../../lib/i18n', () => ({
  getLocale: () => 'en-US',
  t: (key: string) => {
    const messages: Record<string, string> = {
      'register.welcomeTitle': 'Create account',
      'register.welcomeSubtitle2': 'Join now',
      'register.phoneLabel': 'Phone',
      'register.phonePlaceholder': 'Enter phone',
      'register.smsCodeLabel': 'SMS Code',
      'register.smsCodePlaceholder': 'Enter code',
      'register.getSmsCode': 'Get Code',
      'password.label': 'Password',
      'password.placeholder': 'Enter password',
      'password.show': 'Show password',
      'password.hide': 'Hide password',
      'password.strength.weak': 'Weak',
      'password.strength.medium': 'Medium',
      'password.strength.strong': 'Strong',
      'register.confirmPasswordLabel': 'Confirm Password',
      'register.confirmPasswordPlaceholder': 'Confirm password',
      'register.passwordMismatch': 'Passwords do not match',
      'register.agreePrefix': 'I agree to ',
      'register.terms': 'Terms',
      'register.and': ' and ',
      'register.privacy': 'Privacy',
      'register.button': 'Register',
      'register.loading': 'Registering...',
      'register.loginHint': 'Already have an account?',
      'register.loginLink': 'Login',
      'register.otherLoginMethods': 'Other methods',
      'register.wechat': 'WeChat',
      'register.qq': 'QQ',
      'register.thirdPartyWechatHint': 'WeChat not ready',
      'register.thirdPartyQQHint': 'QQ not ready',
      'login.phoneRequired': 'Phone is required',
      'login.phoneInvalid': 'Phone is invalid',
      'password.required': 'Password required',
      'register.agreementRequired': 'Agreement required',
      'toast.serverError': 'Server error',
      'success.redirect': 'Redirecting to login',
    };
    return messages[key] ?? key;
  },
}));

describe('RegisterPage', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it('keeps the submit button disabled until required fields are valid', async () => {
    const user = userEvent.setup();
    renderPage();

    const submit = screen.getByRole('button', { name: 'Register' });
    const phone = screen.getByLabelText('Phone');
    const smsCode = screen.getByLabelText('SMS Code');
    const password = screen.getByLabelText('Password');
    const confirmPassword = screen.getByLabelText('Confirm Password');
    const agreement = screen.getByRole('checkbox');

    expect(submit).toBeDisabled();

    await user.type(phone, '13800138000');
    await user.type(smsCode, '1234');
    await user.type(password, '123456');
    await user.type(confirmPassword, '123456');
    await user.click(agreement);

    expect(submit).toBeEnabled();
  });

  it('shows password mismatch hint', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Password'), '123456');
    await user.type(screen.getByLabelText('Confirm Password'), '654321');

    expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
  });

  it('requests sms code and starts countdown on success', async () => {
    const user = userEvent.setup();
    mocks.sendRegisterCode.mockResolvedValue({
      code: 200,
      msg: 'Code sent',
      data: { code: '1234' },
    });
    renderPage();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.click(screen.getByRole('button', { name: 'Get Code' }));

    expect(mocks.sendRegisterCode).toHaveBeenCalledWith('13800138000');
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '60s' })).toBeDisabled();
    });
  });

  it('submits successfully and navigates to login', async () => {
    const user = userEvent.setup();
    mocks.registerUser.mockResolvedValue({
      username: '13800138000',
      userInfo: { username: '13800138000' },
    });
    renderPage();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.type(screen.getByLabelText('SMS Code'), '1234');
    await user.type(screen.getByLabelText('Password'), '123456');
    await user.type(screen.getByLabelText('Confirm Password'), '123456');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(mocks.registerUser).toHaveBeenCalledWith({
      username: '13800138000',
      password: '123456',
      code: '1234',
      confirm_password: '123456',
    });

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
  });

  it('renders backend error feedback when register fails', async () => {
    const user = userEvent.setup();
    mocks.registerUser.mockRejectedValue(new ApiError(40033, 'Invalid code'));
    renderPage();

    await user.type(screen.getByLabelText('Phone'), '13800138000');
    await user.type(screen.getByLabelText('SMS Code'), '0000');
    await user.type(screen.getByLabelText('Password'), '123456');
    await user.type(screen.getByLabelText('Confirm Password'), '123456');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Invalid code');
  });
});
