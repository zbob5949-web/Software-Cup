import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ApiError, chatWithAI } from '../lib/api';
import { useAuth } from '../lib/auth';
import { getLocale, t } from '../lib/i18n';

type ChatMessage = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
};

type LocationState = {
  successMessage?: string;
};

type ToastState = {
  message: string;
  tone: 'success' | 'error';
};

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: Date.now() + Math.random(),
    role,
    content,
  };
}

export function ChatPage() {
  const locale = getLocale();
  const location = useLocation();
  const { isAuthenticated, username, logout, markUnauthorized } = useAuth();
  const locationState = (location.state ?? {}) as LocationState;
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(
    locationState.successMessage
      ? { message: locationState.successMessage, tone: 'success' }
      : null,
  );
  const controllerRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const quickQuestions = useMemo(
    () => [
      t('chat.quick.open', locale),
      t('chat.quick.route', locale),
      t('chat.quick.spots', locale),
      t('chat.quick.ticket', locale),
    ],
    [locale],
  );

  useEffect(() => {
    if (!toast) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, isLoading]);

  async function sendQuestion(value?: string) {
    if (isLoading) {
      return;
    }

    const trimmedQuestion = (value ?? question).trim();

    if (!trimmedQuestion) {
      setToast({ message: t('chat.error.empty', locale), tone: 'error' });
      textareaRef.current?.focus();
      return;
    }

    const nextUserMessage = createMessage('user', trimmedQuestion);
    const controller = new AbortController();
    controllerRef.current = controller;
    setMessages((current) => [...current, nextUserMessage]);
    setQuestion('');
    setIsLoading(true);

    try {
      const answer = await chatWithAI({ question: trimmedQuestion }, controller.signal);
      setMessages((current) => [
        ...current,
        createMessage('assistant', answer || t('chat.error.failed', locale)),
      ]);
    } catch (error) {
      const status = error instanceof ApiError ? error.status : -1;

      if (status === 401 || status === 403) {
        markUnauthorized();
        setToast({ message: t('chat.error.loginRequired', locale), tone: 'error' });
      } else if (status === 499) {
        setToast({ message: t('chat.stopped', locale), tone: 'success' });
      } else {
        setToast({ message: t('chat.error.failed', locale), tone: 'error' });
      }
    } finally {
      controllerRef.current = null;
      setIsLoading(false);
    }
  }

  function stopQuestion() {
    controllerRef.current?.abort();
  }

  function clearConversation() {
    if (isLoading) {
      controllerRef.current?.abort();
    }

    setMessages([]);
    setQuestion('');
  }

  return (
    <main className="chat-shell">
      <section className="chat-card" aria-labelledby="chat-title">
        <div className="chat-hero">
          <div className="hero-copy">
            <h1 id="chat-title">{t('chat.title', locale)}</h1>
            <p className="subtitle">{t('chat.subtitle', locale)}</p>
          </div>
          <div className="chat-actions-top">
            <span className={isAuthenticated ? 'status-pill is-active' : 'status-pill'}>
              {isAuthenticated
                ? `${t('chat.loggedInAs', locale)} ${username}`
                : t('chat.loginNotice', locale)}
            </span>
            {isAuthenticated ? (
              <button type="button" className="secondary-button" onClick={logout}>
                {t('chat.logout', locale)}
              </button>
            ) : (
              <Link to="/login" className="secondary-link">
                {t('chat.goLogin', locale)}
              </Link>
            )}
          </div>
        </div>

        <div className="quick-questions" aria-label="quick-questions">
          {quickQuestions.map((item) => (
            <button
              key={item}
              type="button"
              className="quick-chip"
              onClick={() => setQuestion(item)}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="chat-history" ref={listRef}>
          {messages.length === 0 && !isLoading ? (
            <div className="chat-empty">{t('chat.empty', locale)}</div>
          ) : null}

          {messages.map((message) => (
            <div
              key={message.id}
              className={
                message.role === 'user'
                  ? 'chat-row chat-row-user'
                  : 'chat-row chat-row-assistant'
              }
            >
              <div
                className={
                  message.role === 'user'
                    ? 'chat-bubble chat-bubble-user'
                    : 'chat-bubble chat-bubble-assistant'
                }
              >
                {message.content}
              </div>
            </div>
          ))}

          {isLoading ? (
            <div className="chat-row chat-row-assistant">
              <div className="chat-bubble chat-bubble-assistant chat-bubble-loading">
                <span className="spinner spinner-soft" aria-hidden="true" />
                {t('chat.loading', locale)}
              </div>
            </div>
          ) : null}
        </div>

        <div className="chat-input-panel">
          <label className="sr-only" htmlFor="chat-question">
            {t('chat.inputPlaceholder', locale)}
          </label>
          <textarea
            ref={textareaRef}
            id="chat-question"
            className="chat-textarea"
            rows={4}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t('chat.inputPlaceholder', locale)}
          />
          <div className="chat-toolbar">
            <button
              type="button"
              className="secondary-button"
              onClick={clearConversation}
              disabled={messages.length === 0 && !question}
            >
              {t('chat.clear', locale)}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={stopQuestion}
              disabled={!isLoading}
            >
              {t('chat.stop', locale)}
            </button>
            <button
              type="button"
              className="submit-button chat-submit"
              onClick={() => void sendQuestion()}
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="button-content">
                  <span className="spinner" aria-hidden="true" />
                  {t('chat.loading', locale)}
                </span>
              ) : (
                t('chat.send', locale)
              )}
            </button>
          </div>
        </div>

        <p className="login-entry chat-reask">
          <span>{t('chat.reask', locale)}</span>
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setQuestion('');
              textareaRef.current?.focus();
            }}
          >
            {t('chat.clear', locale)}
          </button>
        </p>
      </section>

      {toast ? (
        <div className={`toast ${toast.tone === 'success' ? 'toast-success' : 'toast-error'}`} role="alert">
          {toast.message}
        </div>
      ) : null}
    </main>
  );
}
