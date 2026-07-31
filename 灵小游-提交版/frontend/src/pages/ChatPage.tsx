import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  getRecentSessions,
  getSessionDetail,
  deleteSession,
  type ChatSession,
} from '../api/chat';
import { sendDigitalHumanChat } from '../api/digitalHuman';
import { ApiError } from '../api/request';
import { textToSpeech, revokeAudioUrl } from '../api/tts';
import { getLingshanWeather, type LingshanWeather } from '../api/weather';
import { getDigitalHumanConfig, type DigitalHumanConfig } from '../api/digitalHuman';
import { VoiceInput } from '../components/VoiceInput';
import { useAuth } from '../lib/auth';

type ChatMessage = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  voiceRequested?: boolean;
  emotion?: string;
  gesture?: string;
  responseMs?: number;
};

function createMsg(role: ChatMessage['role'], content: string, voiceRequested = false, details?: Pick<ChatMessage, 'emotion' | 'gesture' | 'responseMs'>): ChatMessage {
  return { id: Date.now() + Math.random(), role, content, voiceRequested, ...details };
}

type DhStatus = 'idle' | 'thinking' | 'speaking' | 'listening';

const CHAT_SESSION_KEY = 'scenic-current-chat-session';
const CHAT_MESSAGES_KEY = 'scenic-current-chat-messages';

function readStoredChatMessages(): ChatMessage[] {
  try {
    const raw = window.sessionStorage.getItem(CHAT_MESSAGES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return Array.isArray(parsed) ? parsed.filter((item) => item?.role && item?.content) : [];
  } catch {
    return [];
  }
}

function readStoredChatSession(): string {
  return window.sessionStorage.getItem(CHAT_SESSION_KEY) || '';
}

export function ChatPage() {
  const locale = 'zh-CN';
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, identityType } = useAuth();
  const canUseHistory = isAuthenticated && identityType !== 'guest';

  const [messages, setMessages] = useState<ChatMessage[]>(readStoredChatMessages);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState(readStoredChatSession);
  const [showSidebar, setShowSidebar] = useState(false);
  const [historyNotice, setHistoryNotice] = useState('');
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [showVoicePanel, setShowVoicePanel] = useState(false);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);
  const [frameError, setFrameError] = useState(false);
  const [weather, setWeather] = useState<LingshanWeather | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [dhConfig, setDhConfig] = useState<DigitalHumanConfig | null>(null);
  const [dhStatus, setDhStatus] = useState<DhStatus>('idle');

  const listRef = useRef<HTMLDivElement>(null);
  const dhFrameRef = useRef<HTMLIFrameElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const autoAskRef = useRef(false);
  const lastAutoPlayedIdRef = useRef<number | null>(null);
  const msgEndRef = useRef<HTMLDivElement>(null);
  const ttsAbortRef = useRef<AbortController | null>(null);
  const pageVisibleRef = useRef(true);

  const hasMessages = messages.length > 0;

  // Status label and emoji for DH
  const dhStatusInfo = useMemo(() => {
    if (dhStatus === 'thinking') return { label: '正在查询灵山资料...', emoji: '🧠' };
    if (dhStatus === 'speaking') return { label: '正在语音讲解...', emoji: '🎤' };
    if (dhStatus === 'listening') return { label: '正在聆听...', emoji: '👂' };
    return { label: '很高兴为你服务 ✨', emoji: '🌸' };
  }, [dhStatus]);

  const [userInterests, setUserInterests] = useState<string[]>([]);
  const [showInterestTags, setShowInterestTags] = useState(false);

  const quickQuestions = useMemo(() => [
    '今天灵山的开放时间', '推荐一条亲子游览路线',
    '请介绍灵山大佛的看点', '门票价格是多少',
    '请介绍梵宫的参观重点', '适合老人和孩子的路线',
  ], []);

  const interestTags = [
    { key: '历史', icon: '📜', label: '历史文化' },
    { key: '自然', icon: '🏔', label: '自然风光' },
    { key: '亲子', icon: '👨‍👩‍👧', label: '亲子家庭' },
    { key: '祈福', icon: '🙏', label: '祈福礼佛' },
    { key: '摄影', icon: '📷', label: '摄影打卡' },
    { key: '美食', icon: '🍜', label: '美食素斋' },
  ];

  function toggleInterest(key: string) {
    setUserInterests(prev => {
      if (prev.includes(key)) return prev.filter(k => k !== key);
      return [...prev, key];
    });
  }

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Keep the current conversation available when the user visits another page and returns.
  useEffect(() => {
    if (currentSessionId && currentSessionId !== 'new') window.sessionStorage.setItem(CHAT_SESSION_KEY, currentSessionId);
    else window.sessionStorage.removeItem(CHAT_SESSION_KEY);
    if (messages.length > 0) window.sessionStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(messages));
    else window.sessionStorage.removeItem(CHAT_MESSAGES_KEY);
  }, [currentSessionId, messages]);

  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (
      lastMsg?.role === 'assistant' &&
      lastMsg.content &&
      lastMsg.voiceRequested &&  // 只有用户明确请求语音时才自动播放
      !muted &&
      lastMsg.id !== lastAutoPlayedIdRef.current &&
      pageVisibleRef.current
    ) {
      lastAutoPlayedIdRef.current = lastMsg.id;
      handlePlay(lastMsg.id, lastMsg.content, lastMsg.emotion, lastMsg.gesture);
    }
  }, [messages.length]);

  async function handlePlay(messageId: number, text: string, emotion = 'happy', gesture = 'explain') {
    if (muted || mutedRef.current) return;
    if (playingId === messageId) {
      // 停止：取消语音并通知 Live2D iframe 重置
      if (audioRef.current) {
        audioRef.current.pause();
        if (audioRef.current.src) revokeAudioUrl(audioRef.current.src);
        audioRef.current = null;
      }
      // 向 Live2D iframe 发送停止信号，立即中断正在播放的音频
      const frame = dhFrameRef.current?.contentWindow;
      if (frame) {
        frame.postMessage({ type: 'digital-human-mute' }, '*');
        frame.postMessage({ type: 'digital-human-stop' }, '*');
      }
      setPlayingId(null);
      setDhStatus('idle');
      return;
    }

    // 1. 中断上一次 TTS 请求（防止旧请求返回后和新请求同时播放）
    if (ttsAbortRef.current) {
      ttsAbortRef.current.abort();
      ttsAbortRef.current = null;
    }

    // 2. 停止当前正在播放的音频
    if (audioRef.current) {
      audioRef.current.pause();
      if (audioRef.current.src) revokeAudioUrl(audioRef.current.src);
      audioRef.current = null;
    }

    // 3. 通知 Live2D 停止当前语音
    const frame = dhFrameRef.current?.contentWindow;
    if (frame) {
      frame.postMessage({ type: 'digital-human-mute' }, '*');
      frame.postMessage({ type: 'digital-human-stop' }, '*');
    }
    setPlayingId(null);

    const abortController = new AbortController();
    ttsAbortRef.current = abortController;

    try {
      setPlayingId(messageId);
      setDhStatus('speaking');
      const tts = await textToSpeech(text);

      // 请求已被取消（新的 TTS 请求到达）
      if (abortController.signal.aborted) return;
      if (mutedRef.current) {
        setPlayingId(null);
        setDhStatus('idle');
        return;
      }

      const currentFrame = dhFrameRef.current?.contentWindow;
      if (currentFrame) {
        // ── 走 Live2D 口型同步路径 ──
        let settled = false;
        const finish = () => {
          if (settled) return;
          settled = true;
          if (audioRef.current) {
            audioRef.current.pause();
            if (audioRef.current.src) revokeAudioUrl(audioRef.current.src);
            audioRef.current = null;
          }
          setPlayingId(null);
          setDhStatus('idle');
        };

        currentFrame.postMessage({
          type: 'digital-human-speak',
          text: text,
          emotion,
          gesture,
          audio: tts.audio,
          audio_mime: tts.audio_mime,
          pinyin: tts.pinyin,
          duration: tts.duration
        }, '*');

        const onMsg = (e: MessageEvent) => {
          if (e.source !== currentFrame) return;
          if (e.data?.type === 'digital-human-speech-ended') finish();
          if (e.data?.type === 'digital-human-speech-error') finish();
        };
        window.addEventListener('message', onMsg);
        // 超时保护
        setTimeout(() => { window.removeEventListener('message', onMsg); finish(); }, (tts.duration || 10000) + 5000);
      } else {
        // ── 降级：iframe 不可用时直接播放音频 ──
        const audio = new Audio(tts.url);
        audioRef.current = audio;
        audio.onended = () => { revokeAudioUrl(tts.url); audioRef.current = null; setPlayingId(null); setDhStatus('idle'); };
        audio.onerror = () => { audioRef.current = null; setPlayingId(null); setDhStatus('idle'); };
        await audio.play();
      }
    } catch {
      if (!abortController.signal.aborted) {
        setPlayingId(null);
        setDhStatus('idle');
      }
    } finally {
      if (ttsAbortRef.current === abortController) {
        ttsAbortRef.current = null;
      }
    }
  }

  async function refreshSessions() {
    if (!canUseHistory) return;
    try { const items = await getRecentSessions(); setSessions(items.slice(0, 5)); }
    catch { setSessions([]); }
  }

  async function sendQuestion(value?: string) {
    const trimmed = (value ?? question).trim();
    if (!trimmed || isLoading) return;
    const isVoiceRequest = /语音|讲解/.test(trimmed);

    // 个性化：将用户兴趣偏好作为上下文附加到问题中
    const contextQuestion = userInterests.length > 0
      ? `[我的兴趣偏好：${userInterests.join('、')}] ${trimmed}`
      : trimmed;

    setMessages((prev) => [...prev, createMsg('user', trimmed)]);
    setQuestion('');
    setIsLoading(true);
    setDhStatus('thinking');
    try {
      const startedAt = performance.now();
      const location = (() => {
        try {
          const value = JSON.parse(window.localStorage.getItem('lingshanGuideCurrentLocation') || 'null') as { latitude?: number; longitude?: number; accuracy?: number; source?: string } | null;
          return value && Number.isFinite(value.latitude) && Number.isFinite(value.longitude) ? value : undefined;
        } catch { return undefined; }
      })();
      const result = await sendDigitalHumanChat(isAuthenticated ? currentSessionId : '', contextQuestion, location, userInterests);
      const responseMs = Math.round(performance.now() - startedAt);
      if (result.session_id) setCurrentSessionId(result.session_id);
      setMessages((prev) => [...prev, createMsg('assistant', result.reply || '服务暂不可用', isVoiceRequest, { emotion: result.emotion, gesture: result.gesture, responseMs })]);
      if (/门票|票价|多少钱|购票|价格/.test(trimmed) && !result.reply?.includes('购票')) {
        setMessages((prev) => [...prev, createMsg('assistant', '需要购票吗？可以点击下方"快捷操作"中的"购票"按钮，或直接点击这里👉', false, {})]);
      }
      setDhStatus('speaking');
      void refreshSessions();
    } catch (error) {
      const status = error instanceof ApiError ? error.status : -1;
      if (status === 401 || status === 403) setDhStatus('idle');
      else setDhStatus('idle');
      setMessages((prev) => [...prev, createMsg('assistant', status === 401 || status === 403 ? '请先登录后使用' : '服务暂不可用，请稍后重试')]);
    } finally { setIsLoading(false); }
  }

  async function handleOpenSession(sessionId: string) {
    if (!canUseHistory) { setHistoryNotice('登录后可保存并查看历史对话'); return; }
    try {
      const history = await getSessionDetail(sessionId);
      const restored = history.map((item) => createMsg(item.role, item.content));
      setCurrentSessionId(sessionId);
      setMessages(restored);
      setHistoryNotice(''); setShowSidebar(false);
      // 标记最后一条助手消息为已播放，防止恢复历史时自动重新播报
      const lastAsst = [...restored].reverse().find(m => m.role === 'assistant');
      if (lastAsst) lastAutoPlayedIdRef.current = lastAsst.id;
    } catch (error) {
      setHistoryNotice(error instanceof ApiError ? error.message : '获取会话消息失败');
    }
  }

  async function handleNewSession() {
    if (!canUseHistory) { setHistoryNotice('登录后可保存并查看历史对话'); return; }
    setCurrentSessionId(''); setMessages([]); setShowSidebar(false);
    lastAutoPlayedIdRef.current = null;
    await refreshSessions();
  }

  async function handleDeleteSession(sessionId: string) {
    if (!window.confirm('确定删除此会话？删除后不可恢复。')) return;
    try {
      await deleteSession(sessionId);
      if (sessionId === currentSessionId) { setCurrentSessionId(''); setMessages([]); }
      await refreshSessions();
    } catch {
      setHistoryNotice('删除失败，请稍后重试');
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendQuestion(); }
  }

  useEffect(() => {
    if (!canUseHistory) {
      setSessions([]);
      if (!isAuthenticated || identityType === 'guest') setHistoryNotice('登录后可保存并查看历史对话');
      return;
    }
    void refreshSessions();
    if (messages.length === 0) {
      const storedSession = readStoredChatSession();
      if (storedSession) void handleOpenSession(storedSession);
    }
  }, [canUseHistory]);

  useEffect(() => {
    const requestedSession = searchParams.get('session');
    if (!requestedSession || !canUseHistory) return;
    if (requestedSession === currentSessionId && messages.length > 0) return;
    void handleOpenSession(requestedSession);
  }, [searchParams, canUseHistory]);

  useEffect(() => {
    getLingshanWeather().then(setWeather).catch(() => setWeather({
      location: '无锡灵山', weather: '天气暂不可用', temp: '--', suggestion: '',
    }));
  }, []);

  useEffect(() => {
    getDigitalHumanConfig().then(setDhConfig).catch(() => setDhConfig(null));
  }, []);

  useEffect(() => {
    const ask = searchParams.get('ask');
    if (!ask || autoAskRef.current) return;
    autoAskRef.current = true;
    setQuestion(ask);
    void sendQuestion(ask);
  }, [searchParams]);

  useEffect(() => {
    // 每次进入对话页，标记页面可见（用于控制自动 TTS）
    pageVisibleRef.current = true;
    // 清理上一次的 TTS 请求
    if (ttsAbortRef.current) {
      ttsAbortRef.current.abort();
      ttsAbortRef.current = null;
    }
    return () => {
      // 离开页面立即停止所有音频
      pageVisibleRef.current = false;
      // 取消正在进行的 TTS 请求
      if (ttsAbortRef.current) {
        ttsAbortRef.current.abort();
        ttsAbortRef.current = null;
      }
      if (audioRef.current) {
        audioRef.current.pause();
        if (audioRef.current.src) revokeAudioUrl(audioRef.current.src);
        audioRef.current = null;
      }
      window.speechSynthesis?.cancel();
      setPlayingId(null);
      setDhStatus('idle');
    };
  }, []);

  const weatherText = weather
    ? `${weather.city || weather.location || '无锡灵山'} ${weather.weather || ''} ${weather.temperature ?? weather.temp ?? '--'}`
    : '天气加载中';

  const digitalHumanFrameSrc = `/live2d/index.html?hideUI=1&model=${encodeURIComponent(dhConfig?.model_dir || 'Haru')}&api=${encodeURIComponent(window.location.origin)}`;

  return (
    <div className="ai-chat-page">
      {/* ── Session drawer ── */}
      {showSidebar && <div className="ai-chat-drawer-overlay" onClick={() => setShowSidebar(false)} />}
      <aside className={`ai-chat-drawer ${showSidebar ? 'open' : ''}`}>
        <div className="ai-chat-drawer-head">
          <div><h3>历史会话</h3><p>{isAuthenticated ? '最近 5 条会话' : '登录后可保存历史'}</p></div>
          <button type="button" onClick={() => setShowSidebar(false)} aria-label="关闭">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="ai-chat-drawer-body">
          <button type="button" className="ai-chat-drawer-new" onClick={handleNewSession}>新建对话</button>
          {historyNotice ? <p className="ai-chat-drawer-notice">{historyNotice}</p> : null}
          {sessions.map((s) => (
            <div key={s.session_id} className={`ai-chat-drawer-item-row ${s.session_id === currentSessionId ? 'active' : ''}`}>
              <button type="button" className="ai-chat-drawer-item" onClick={() => handleOpenSession(s.session_id)} style={{ flex: 1 }}>
                <span>{s.title || '未命名会话'}</span>
                <small>{s.preview || ''}</small>
              </button>
              <button type="button" className="ai-chat-drawer-delete" onClick={() => handleDeleteSession(s.session_id)} title="删除会话">✕</button>
            </div>
          ))}
          {isAuthenticated && sessions.length === 0 && !historyNotice && <p className="ai-chat-drawer-notice">暂无历史会话</p>}
        </div>
      </aside>

      {/* ── Top bar ── */}
      <header className="ai-chat-topbar">
        <button className="ai-chat-topbar-back" onClick={() => navigate(-1)} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <div className="ai-chat-topbar-info">
          <h1>AI 数字人导游</h1>
          <span className="ai-chat-topbar-status">{dhConfig?.name || '灵小游'} · 灵山景区</span>
        </div>
        <div className="ai-chat-topbar-actions">
          <button className={`ai-chat-mute-btn ${muted ? 'muted' : ''}`} onClick={() => {
            const next = !muted;
            mutedRef.current = next;
            setMuted(next);
            if (next) {
              // 立即停止当前播放的音频
              if (audioRef.current) {
                audioRef.current.pause();
                if (audioRef.current.src) revokeAudioUrl(audioRef.current.src);
                audioRef.current = null;
              }
              window.speechSynthesis?.cancel();
              dhFrameRef.current?.contentWindow?.postMessage({ type: 'digital-human-mute' }, '*');
              setPlayingId(null);
              setDhStatus('idle');
            }
          }} title={muted ? '取消静音' : '一键静音'}>
            {muted ? '🔇' : '🔊'}
          </button>
          <button className="ai-chat-topbar-history" onClick={() => setShowSidebar(true)} aria-label="历史会话">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v5h5" /><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" /><path d="M12 7v5l3 2" /></svg>
          </button>
        </div>
      </header>

      {/* ── Hero area ── */}
      <section className="ai-chat-hero">
        {/* Scenic background layers */}
        <div className="ai-chat-hero-scene">
          <div className="ai-chat-hero-sky" />
          <div className="ai-chat-hero-mountains" />
          <div className="ai-chat-hero-buddha" />
          <div className="ai-chat-hero-lake" />
          <div className="ai-chat-hero-overlay" />
        </div>

        <div className="ai-chat-hero-content">
          <div className="ai-chat-hero-text">
            <div className="ai-chat-hero-badge">
              <span className="ai-chat-hero-badge-dot" />
              AI 数字人导游
            </div>
            <h2 className="ai-chat-hero-title">
              你好，我是<br />
              <strong>{dhConfig?.name || '灵小游'}</strong>
            </h2>
            <p className="ai-chat-hero-sub">灵山胜境 · 山水导览 · 文化讲解</p>
            <div className="ai-chat-hero-state">
              <span className={`ai-chat-hero-state-dot ${dhStatus}`} />
              <span>{dhStatusInfo.emoji} {dhStatusInfo.label}</span>
            </div>
          </div>
          <div className="ai-chat-hero-avatar">
            <div className="ai-chat-avatar-glow" />
            {frameError ? (
              <div className="ai-chat-hero-avatar-fb"><span>灵</span></div>
            ) : (
              <div className="ai-chat-hero-frame-shell" aria-label="数字人讲解舞台">
                <iframe
                  ref={dhFrameRef}
                  title={dhConfig?.name || '数字人'}
                  src={digitalHumanFrameSrc}
                  className={`ai-chat-hero-frame ${dhStatus}`}
                  allow="autoplay; microphone"
                  onError={() => setFrameError(true)}
                />
              </div>
            )}
            <div className={`ai-chat-avatar-status ${dhStatus}`}>
              <span className="ai-chat-avatar-status-dot" />
              <span>{dhStatus === 'speaking' ? '数字人讲解中' : dhStatus === 'thinking' ? '正在检索资料' : dhStatus === 'listening' ? '正在聆听提问' : '数字人待命'}</span>{dhStatus === 'speaking' && <span className="ai-chat-avatar-sync">口型同步</span>}
            </div>
          </div>
        </div>
      </section>

      {/* ── Weather card ── */}
      <div className="ai-chat-weather">
        <div className="ai-chat-weather-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#056B5B" strokeWidth="1.5"><path d="M17.5 19H9a7 7 0 1 1 6.7-9h.3a5 5 0 0 1 1.5 9Z" /></svg>
        </div>
        <div className="ai-chat-weather-info">
          <span className="ai-chat-weather-loc">{weatherText}</span>
          {weather?.advice && <span className="ai-chat-weather-advice">{weather.advice}</span>}
        </div>
      </div>

      {/* ── Interest tags ── */}
      <section className="ai-chat-interest-panel">
        <button type="button" className="ai-chat-interest-toggle" onClick={() => setShowInterestTags((open) => !open)} aria-expanded={showInterestTags}>
          <span><strong>个性化偏好</strong></span><span>{showInterestTags ? '收起 ▲' : '展开 ▼'}</span>
        </button>
        {showInterestTags ? <div className="ai-chat-interest-tags">
          {interestTags.map(tag => <button key={tag.key} className={`ai-chat-interest-tag ${userInterests.includes(tag.key) ? 'ai-cs-active' : ''}`} onClick={() => toggleInterest(tag.key)}><span className="ai-chat-shortcut-icon">{tag.icon}</span><span className="ai-chat-shortcut-label">{tag.label}</span></button>)}
          {userInterests.length > 0 ? <span className="ai-chat-interest-confirm">✓ 已选择 {userInterests.length} 项偏好</span> : null}
        </div> : null}
      </section>

      {/* ── Floating shortcuts ── */}
      <div className="ai-chat-shortcuts">
        <button className="ai-chat-shortcut" onClick={() => void sendQuestion('请介绍灵山主要景点')}>
          <span className="ai-chat-shortcut-icon ai-cs-spots">🏛</span>
          <span className="ai-chat-shortcut-label">景点</span>
        </button>
        <button className="ai-chat-shortcut" onClick={() => void sendQuestion('推荐一条灵山游览路线')}>
          <span className="ai-chat-shortcut-icon ai-cs-routes">🗺</span>
          <span className="ai-chat-shortcut-label">路线</span>
        </button>
        <button className="ai-chat-shortcut" onClick={() => navigate('/guide?tab=map')}>
          <span className="ai-chat-shortcut-icon ai-cs-guide">🧭</span>
          <span className="ai-chat-shortcut-label">导览</span>
        </button>
        <button className="ai-chat-shortcut" onClick={() => navigate('/tickets')}>
          <span className="ai-chat-shortcut-icon ai-cs-ticket">🎫</span>
          <span className="ai-chat-shortcut-label">购票</span>
        </button>
      </div>

      {/* ── Chat messages ── */}
      <div className="ai-chat-msgs" ref={listRef}>
        {hasMessages ? (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={`ai-chat-row ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div className="ai-chat-av ai-chat-av-dh">
                    <span>{dhConfig?.name?.charAt(0) || '灵'}</span>
                  </div>
                )}
                <div className={`ai-chat-bubble ${msg.role}`}>
                  <p>{msg.content}</p>{msg.role === 'assistant' && msg.responseMs ? <span className="ai-chat-response-meta">响应 {msg.responseMs}ms · {msg.emotion || 'neutral'} · 口型同步</span> : null}{(msg.role === 'assistant' && (/购票/.test(msg.content) || /需要我带你/.test(msg.content))) && <button type="button" className="ai-chat-ticket-link" onClick={() => navigate('/tickets')}>🎫 前往购票</button>}
                  {msg.role === 'assistant' && (
                    <button className={`ai-chat-tts ${playingId === msg.id ? 'playing' : ''}`}
                      onClick={() => void handlePlay(msg.id, msg.content, msg.emotion, msg.gesture)} title={playingId === msg.id ? '停止' : '朗读'}>
                      {playingId === msg.id ? (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></svg>
                      ) : (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path d="M19.07 4.93a10 10 0 0 1 0 14.14" /><path d="M15.54 8.46a5 5 0 0 1 0 7.07" /></svg>
                      )}
                    </button>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="ai-chat-av ai-chat-av-user">
                    <span>我</span>
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="ai-chat-row assistant">
                <div className="ai-chat-av ai-chat-av-dh"><span>{dhConfig?.name?.charAt(0) || '灵'}</span></div>
                <div className="ai-chat-bubble assistant">
                  <span className="ai-chat-dots"><span /><span /><span /></span>
                </div>
              </div>
            )}
            <div ref={msgEndRef} />
          </>
        ) : (
          <div className="ai-chat-empty">
            <div className="ai-chat-empty-icon">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#056B5B" strokeWidth="1" opacity="0.25"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
            </div>
            <p className="ai-chat-empty-title">有什么可以帮您？</p>
            <p className="ai-chat-empty-sub">试试点击上方快捷入口，或直接输入问题</p>
          </div>
        )}
      </div>

      {/* ── Input bar ── */}
      <div className="ai-chat-bar">
        <div className="ai-chat-bar-inner">
          <button className={`ai-chat-bar-mic ${isListening ? 'active' : ''}`} onClick={() => { setShowVoicePanel(true); setDhStatus('listening'); }} aria-label="语音">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" /></svg>
          </button>
          <input className="ai-chat-bar-input" type="text" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={handleKeyDown} placeholder="输入问题..." disabled={isLoading} />
          <button className="ai-chat-bar-send" disabled={!question.trim() || isLoading} onClick={() => void sendQuestion()} aria-label="发送">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
          </button>
        </div>
      </div>

      {showVoicePanel && (
        <VoiceInput onResult={(text) => { setQuestion(text); setIsListening(true); }} onClose={() => { setShowVoicePanel(false); setIsListening(false); setDhStatus('idle'); }} />
      )}
    </div>
  );
}
