import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RegisterPage } from '../RegisterPage';

const registerUserMock = vi.fn();

vi.mock('../../lib/api', () => ({
  RegisterApiError: class RegisterApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  registerUser: (...args: unknown[]) => registerUserMock(...args),
}));

describe('RegisterPage', () => {
  beforeEach(() => {
    registerUserMock.mockReset();
  });

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<div>登录页</div>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it('keeps the submit button disabled until the form becomes valid', async () => {
    const user = userEvent.setup();
    renderPage();

    const submit = screen.getByRole('button', { name: '立即注册' });
    const username = screen.getByLabelText('用户名');
    const password = screen.getByLabelText('密码');

    expect(submit).toBeDisabled();

    await user.type(username, 'tester_01');
    await user.type(password, 'Password1!');

    expect(submit).toBeEnabled();
    expect(screen.getByText('用户名格式正确')).toBeInTheDocument();
    expect(screen.getByText('强')).toBeInTheDocument();
  });

  it('focuses the empty username field and shows required message', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: '立即注册' }));

    const username = screen.getByLabelText('用户名');
    expect(username).toHaveFocus();
    expect(screen.getAllByText('请输入用户名')[0]).toBeInTheDocument();
  });

  it('focuses the password field when username is filled but password is empty', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('用户名'), 'tester_01');
    await user.click(screen.getByRole('button', { name: '立即注册' }));

    expect(screen.getByLabelText('密码')).toHaveFocus();
    expect(screen.getAllByText('请输入密码')[0]).toBeInTheDocument();
  });

  it('submits successfully and navigates to login', async () => {
    const user = userEvent.setup();
    registerUserMock.mockResolvedValue(undefined);
    renderPage();

    await user.type(screen.getByLabelText('用户名'), 'tester_01');
    await user.type(screen.getByLabelText('密码'), 'Password1!');
    await user.click(screen.getByRole('button', { name: '立即注册' }));

    expect(registerUserMock).toHaveBeenCalledWith({
      username: 'tester_01',
      password: 'Password1!',
    });

    await waitFor(() => {
      expect(screen.getByText('登录页')).toBeInTheDocument();
    });
  });
});
