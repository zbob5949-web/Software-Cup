import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../../lib/auth';
import { ChatPage } from '../ChatPage';

const chatWithAIMock = vi.fn();

class MockApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

vi.mock('../../lib/api', () => ({
  ApiError: MockApiError,
  chatWithAI: (...args: unknown[]) => chatWithAIMock(...args),
}));

describe('ChatPage', () => {
  beforeEach(() => {
    chatWithAIMock.mockReset();
  });

  function renderPage() {
    return render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/chat']}>
          <Routes>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/login" element={<div>登录页</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );
  }

  it('fills a quick question and renders the ai reply', async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem(
      'scenic-auth-state',
      JSON.stringify({ isAuthenticated: true, username: 'tester' }),
    );
    chatWithAIMock.mockResolvedValue('景区今天正常开放。');
    renderPage();

    await user.click(screen.getByRole('button', { name: '今天开放吗？' }));
    expect(screen.getByPlaceholderText('请输入你想咨询的问题')).toHaveValue('今天开放吗？');

    await user.click(screen.getByRole('button', { name: '发送' }));

    expect(chatWithAIMock).toHaveBeenCalledWith(
      { question: '今天开放吗？' },
      expect.any(AbortSignal),
    );

    await waitFor(() => {
      expect(screen.getByText('景区今天正常开放。')).toBeInTheDocument();
    });
  });

  it('shows login guidance when the backend returns unauthorized', async () => {
    const user = userEvent.setup();
    chatWithAIMock.mockRejectedValue(new MockApiError(401, 'Unauthorized'));
    renderPage();

    await user.type(screen.getByPlaceholderText('请输入你想咨询的问题'), '门票怎么预约？');
    await user.click(screen.getByRole('button', { name: '发送' }));

    await waitFor(() => {
      expect(screen.getByText('请先登录')).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: '去登录' })).toBeInTheDocument();
  });
});
