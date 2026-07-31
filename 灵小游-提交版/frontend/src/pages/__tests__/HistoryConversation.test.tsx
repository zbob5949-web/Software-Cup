import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HistoryConversation } from '../HistoryConversation';

const mocks = vi.hoisted(() => ({
  getRecentSessions: vi.fn(),
  deleteSession: vi.fn(),
}));

vi.mock('../../api/chat', () => ({
  getRecentSessions: mocks.getRecentSessions,
  deleteSession: mocks.deleteSession,
}));

vi.mock('../../components/PageTransition', () => ({
  PageTransition: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe('HistoryConversation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/history']}>
        <Routes>
          <Route path="/history" element={<HistoryConversation />} />
          <Route path="/ai-chat" element={<div>AI Chat Page</div>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it('shows skeleton placeholders on first load', () => {
    mocks.getRecentSessions.mockImplementation(() => new Promise(() => {}));
    const { container } = renderPage();

    expect(container.querySelector('.skeleton-card-row')).toBeTruthy();
  });

  it('shows empty state and navigates to chat', async () => {
    const user = userEvent.setup();
    mocks.getRecentSessions.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText(/暂无历史会话/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /去对话/i }));
    expect(await screen.findByText('AI Chat Page')).toBeInTheDocument();
  });

  it('renders session title, preview, and formatted time', async () => {
    mocks.getRecentSessions.mockResolvedValue([
      {
        session_id: 's1',
        title: '门票咨询',
        preview: '门票几点开售',
        created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      },
    ]);
    renderPage();

    expect(await screen.findByText('门票咨询')).toBeInTheDocument();
    expect(screen.getByText('门票几点开售')).toBeInTheDocument();
    expect(screen.getByText(/小时前|\/\d+/i)).toBeInTheDocument();
  });

  it('triggers refresh on pull-down gesture', async () => {
    mocks.getRecentSessions.mockResolvedValue([]);
    const { container } = renderPage();

    await waitFor(() => {
      expect(mocks.getRecentSessions).toHaveBeenCalledTimes(1);
    });

    const content = container.querySelector('.history-content') as HTMLDivElement;
    Object.defineProperty(content, 'scrollTop', { value: 0, configurable: true });

    fireEvent.touchStart(content, {
      touches: [{ clientY: 0 }],
    });
    fireEvent.touchMove(content, {
      touches: [{ clientY: 200 }],
    });
    fireEvent.touchEnd(content);

    await waitFor(() => {
      expect(mocks.getRecentSessions).toHaveBeenCalledTimes(2);
    });
  });

  it('triggers load more when the list is scrolled to the bottom', async () => {
    mocks.getRecentSessions.mockResolvedValue(new Array(5).fill(null).map((_, index) => ({
      session_id: `s${index}`,
      title: `会话${index}`,
      preview: `预览${index}`,
      created_at: new Date().toISOString(),
    })));
    const { container } = renderPage();

    await waitFor(() => {
      expect(mocks.getRecentSessions).toHaveBeenCalledTimes(1);
    });

    const content = container.querySelector('.history-content') as HTMLDivElement;
    Object.defineProperty(content, 'scrollHeight', { value: 1000, configurable: true });
    Object.defineProperty(content, 'scrollTop', { value: 950, configurable: true });
    Object.defineProperty(content, 'clientHeight', { value: 100, configurable: true });

    fireEvent.scroll(content);

    await userEvent.setup().click(screen.getByText(/加载更多/i));

    await waitFor(() => {
      expect(mocks.getRecentSessions).toHaveBeenCalledTimes(2);
    });
  });

  it('removes an item locally when delete is clicked', async () => {
    mocks.getRecentSessions.mockResolvedValue([
      {
        session_id: 's1',
        title: '会话1',
        preview: '预览1',
        created_at: new Date().toISOString(),
      },
      {
        session_id: 's2',
        title: '会话2',
        preview: '预览2',
        created_at: new Date().toISOString(),
      },
    ]);
    const { container } = renderPage();

    expect(await screen.findByText('会话1')).toBeInTheDocument();

    const deleteButtons = container.querySelectorAll('.history-item-delete');
    expect(deleteButtons).toHaveLength(2);

    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText('会话1')).not.toBeInTheDocument();
    });
    expect(screen.getByText('会话2')).toBeInTheDocument();
    expect(mocks.getRecentSessions).toHaveBeenCalledTimes(1);
  });
});
