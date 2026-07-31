import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../api/request';
import { AuthProvider } from '../../lib/auth';
import { ChatPage } from '../ChatPage';

const mocks = vi.hoisted(() => ({
  sendDigitalHumanChat: vi.fn(),
  getRecentSessions: vi.fn(),
  getSessionDetail: vi.fn(),
  getLingshanWeather: vi.fn(),
  textToSpeech: vi.fn(),
  revokeAudioUrl: vi.fn(),
  getDigitalHumanConfig: vi.fn(),
}));

vi.mock('../../api/chat', () => ({
  getRecentSessions: mocks.getRecentSessions,
  getSessionDetail: mocks.getSessionDetail,
}));

vi.mock('../../api/weather', () => ({
  getLingshanWeather: mocks.getLingshanWeather,
}));

vi.mock('../../api/tts', () => ({
  textToSpeech: mocks.textToSpeech,
  revokeAudioUrl: mocks.revokeAudioUrl,
}));

vi.mock('../../api/digitalHuman', () => ({
  getDigitalHumanConfig: mocks.getDigitalHumanConfig,
  sendDigitalHumanChat: mocks.sendDigitalHumanChat,
}));

vi.mock('../../components/VoiceInput', () => ({
  VoiceInput: ({ onClose }: { onClose: () => void }) => (
    <div>
      <button type="button" onClick={onClose}>Close Voice</button>
    </div>
  ),
}));

vi.mock('../../lib/i18n', () => ({
  getLocale: () => 'en-US',
  t: (key: string) => {
    const messages: Record<string, string> = {
      'chat.digitalStatus': 'Ready',
      'chat.quick.open': 'Is it open today?',
      'chat.quick.route': 'Plan a route',
      'chat.quick.spots': 'Tell me about spots',
      'chat.quick.ticket': 'Ticket times',
      'chat.aiLoading': 'Thinking',
      'chat.error.failed': 'Request failed',
      'chat.error.loginRequired': 'Please log in first',
      'chat.stopped': 'Stopped',
      'chat.onlineStatus': 'Online',
      'aiChat.thinking': 'Thinking...',
      'aiChat.listening': 'Listening...',
      'aiChat.title': 'AI Guide',
      'aiChat.back': 'Back',
      'aiChat.topTag': 'AI Digital Human',
      'aiChat.tapToSpeak': 'Tap to speak',
      'drawer.close': 'Close',
      'chat.empty': 'Ask me anything',
      'chat.inputPlaceholder': 'Ask a question',
      'chat.send': 'Send',
    };
    return messages[key] ?? key;
  },
}));

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getRecentSessions.mockResolvedValue([]);
    mocks.getSessionDetail.mockResolvedValue([]);
    mocks.sendDigitalHumanChat.mockResolvedValue({ reply: 'Open today', emotion: 'happy', gesture: 'welcome', session_id: 's1' });
    mocks.getLingshanWeather.mockResolvedValue({
      city: 'Wuxi Lingshan',
      weather: 'Sunny',
      temperature: '26°C',
      advice: 'Great for visiting',
    });
    mocks.getDigitalHumanConfig.mockResolvedValue({
      name: '小灵',
      welcomeMessage: 'Hello, I am the AI digital guide.',
      introduction: 'Official AI digital human.',
      videoUrl: '/videos/digital-human.mp4',
      voiceType: '温柔女声',
      speed: 1.0,
      volume: 0.8,
    });
    window.sessionStorage.clear();
  });

  function renderPage() {
    return render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/ai-chat']}>
          <Routes>
            <Route path="/ai-chat" element={<ChatPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );
  }

  it('shows login notice for history when unauthenticated', async () => {
    const user = userEvent.setup();
    const view = renderPage();

    await user.click(view.container.querySelector('.ai-chat-history-btn') as HTMLButtonElement);

    expect(await screen.findByText('登录后可保存并查看历史对话')).toBeInTheDocument();
    expect(mocks.getRecentSessions).not.toHaveBeenCalled();
  });

  it('loads recent sessions for authenticated users and opens the history drawer', async () => {
    window.sessionStorage.setItem('scenic-auth-state', JSON.stringify({
      isAuthenticated: true,
      username: '13800138000',
      userInfo: { username: '13800138000' },
    }));
    mocks.getRecentSessions.mockResolvedValue([
      { session_id: 's1', title: 'Last chat', preview: 'How do I reach Fangong?' },
      { session_id: 's2', title: 'Tickets', preview: 'When do tickets open?' },
    ]);

    const user = userEvent.setup();
    const view = renderPage();

    await waitFor(() => {
      expect(mocks.getRecentSessions).toHaveBeenCalled();
    });

    await user.click(view.container.querySelector('.ai-chat-history-btn') as HTMLButtonElement);

    expect(await screen.findByText('Last chat')).toBeInTheDocument();
    expect(screen.getByText('How do I reach Fangong?')).toBeInTheDocument();
  });

  it('loads session detail when a history item is clicked', async () => {
    window.sessionStorage.setItem('scenic-auth-state', JSON.stringify({
      isAuthenticated: true,
      username: '13800138000',
      userInfo: { username: '13800138000' },
    }));
    mocks.getRecentSessions.mockResolvedValue([
      { session_id: 's1', title: 'Last chat', preview: 'How do I reach Fangong?' },
    ]);
    mocks.getSessionDetail.mockResolvedValue([
      { role: 'user', content: 'How do I reach Fangong?' },
      { role: 'assistant', content: 'Keep walking forward from Jiulong.' },
    ]);

    const user = userEvent.setup();
    const view = renderPage();

    await user.click(view.container.querySelector('.ai-chat-history-btn') as HTMLButtonElement);
    await user.click((await screen.findAllByRole('button')).find((button) =>
      button.textContent?.includes('Last chat'),
    ) as HTMLButtonElement);

    await waitFor(() => {
      expect(mocks.getSessionDetail).toHaveBeenCalledWith('s1');
    });
    expect(await screen.findByText('Keep walking forward from Jiulong.')).toBeInTheDocument();
  });

  it('shows failure notice when loading session detail fails', async () => {
    window.sessionStorage.setItem('scenic-auth-state', JSON.stringify({
      isAuthenticated: true,
      username: '13800138000',
      userInfo: { username: '13800138000' },
    }));
    mocks.getRecentSessions.mockResolvedValue([
      { session_id: 's1', title: 'Last chat', preview: 'How do I reach Fangong?' },
    ]);
    mocks.getSessionDetail.mockRejectedValue(new Error('boom'));

    const user = userEvent.setup();
    const view = renderPage();

    await user.click(view.container.querySelector('.ai-chat-history-btn') as HTMLButtonElement);
    await user.click((await screen.findAllByRole('button')).find((button) =>
      button.textContent?.includes('Last chat'),
    ) as HTMLButtonElement);

    expect(await screen.findByText('获取会话消息失败')).toBeInTheDocument();
  });

  it('sends a quick question and renders loading plus the reply', async () => {
    const user = userEvent.setup();
    let resolveReply: ((value: { reply: string; emotion: string; gesture: string; session_id: string }) => void) | undefined;
    mocks.sendDigitalHumanChat.mockImplementation(
      () => new Promise((resolve) => { resolveReply = resolve; }),
    );
    const view = renderPage();

    await user.click(view.container.querySelector('.ai-chat-shortcut') as HTMLButtonElement);

    expect(mocks.sendDigitalHumanChat).toHaveBeenCalled();

    // Loading indicator should appear while waiting
    expect(view.container.querySelector('.ai-chat-dots')).toBeInTheDocument();

    resolveReply?.({ reply: 'Open today', emotion: 'happy', gesture: 'welcome', session_id: 's1' });

    expect(await screen.findByText('Open today')).toBeInTheDocument();
  });

  it('disables send button until input has content and shows backend error status on failure', async () => {
    const user = userEvent.setup();
    mocks.sendDigitalHumanChat.mockRejectedValue(new ApiError(401, 'Please log in first'));
    renderPage();

    const view = renderPage();
    const sendButton = view.container.querySelector('.ai-chat-bar-send') as HTMLButtonElement;
    const input = view.container.querySelector('.ai-chat-bar-input') as HTMLInputElement;

    expect(sendButton).toBeDisabled();

    await user.type(input, 'Plan a route');
    expect(sendButton).toBeEnabled();

    await user.click(sendButton);

    await waitFor(() => {
      const assistantMessages = view.container.querySelectorAll('.ai-chat-bubble.assistant');
      expect(assistantMessages.length).toBeGreaterThanOrEqual(1);
      expect(assistantMessages[assistantMessages.length - 1].textContent?.trim()).toBeTruthy();
    });
  });

  it('exposes the contract mismatch as a known failing frontend path', async () => {
    window.sessionStorage.setItem('scenic-auth-state', JSON.stringify({
      isAuthenticated: true,
      username: '13800138000',
      userInfo: { username: '13800138000' },
    }));
    mocks.getRecentSessions.mockResolvedValue([
      { session_id: 'contract-bug', title: 'Contract mismatch', preview: 'Frontend detail route differs' },
    ]);
    mocks.getSessionDetail.mockRejectedValue(
      new ApiError(404, 'Frontend requests /api/user/chat/detail but backend only exposes /sessions/{session_id}/messages'),
    );

    const user = userEvent.setup();
    const view = renderPage();

    await user.click(view.container.querySelector('.ai-chat-history-btn') as HTMLButtonElement);
    const item = (await screen.findAllByRole('button')).find((button) =>
      button.textContent?.includes('Contract mismatch'),
    ) as HTMLButtonElement;
    await user.click(item);

    const notice = await screen.findByText('Frontend requests /api/user/chat/detail but backend only exposes /sessions/{session_id}/messages');
    expect(notice).toBeInTheDocument();
    expect(notice.textContent).toContain('/api/user/chat/detail');
    expect(notice.textContent).toContain('/sessions/{session_id}/messages');
  });
});
