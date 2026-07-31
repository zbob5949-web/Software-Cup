import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { deleteSession, getRecentSessions, type ChatSession } from '../api/chat';
import { EmptyState } from '../components/EmptyState';
import { PageTransition } from '../components/PageTransition';
import { SkeletonPlaceholder } from '../components/SkeletonPlaceholder';

/** 格式化时间显示 */
function formatTime(ts?: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60_000) return '刚刚';
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}分钟前`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}小时前`;
    const m = d.getMonth() + 1;
    const day = d.getDate();
    return `${m}/${day}`;
  } catch {
    return '';
  }
}

export function HistoryConversation() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [swipedId, setSwipedId] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  // ---------- 数据加载 ----------
  const fetchSessions = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await getRecentSessions();
      const enriched = data.map((s) => ({
        ...s,
        preview: s.preview ?? s.title,
        time: s.time ?? s.created_at ?? s.updated_at,
      }));
      setSessions(enriched);
    } catch {
      // 静默处理，保留已有数据
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void fetchSessions();
  }, [fetchSessions]);

  // ---------- 下拉刷新 ----------
  const touchStartY = useRef(0);
  const [pullDistance, setPullDistance] = useState(0);
  const PULL_THRESHOLD = 64;

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (containerRef.current && containerRef.current.scrollTop <= 0) {
      const dy = e.touches[0].clientY - touchStartY.current;
      setPullDistance(Math.max(0, dy * 0.5));
    }
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (pullDistance >= PULL_THRESHOLD && !refreshing) {
      void fetchSessions();
    }
    setPullDistance(0);
  }, [pullDistance, refreshing, fetchSessions]);

  // ---------- 上拉加载更多 ----------
  // ---------- 侧滑删除 ----------
  const touchItemX = useRef(0);
  const handleItemTouchStart = useCallback((id: string, e: React.TouchEvent) => {
    if (batchMode) return;
    touchItemX.current = e.touches[0].clientX;
  }, [batchMode]);

  const handleItemTouchEnd = useCallback((id: string, e: React.TouchEvent) => {
    if (batchMode) return;
    const dx = e.changedTouches[0].clientX - touchItemX.current;
    if (dx < -80) {
      setSwipedId(id);
    } else {
      setSwipedId(null);
    }
  }, [batchMode]);

  const removeSession = useCallback(async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.session_id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch {
      // Keep the item visible when the server rejects the deletion.
    } finally {
      setSwipedId(null);
    }
  }, []);

  // ---------- 长按批量操作 ----------
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleItemTouchStartLong = useCallback((id: string) => {
    longPressTimer.current = setTimeout(() => {
      setBatchMode(true);
      setSelected(new Set([id]));
    }, 600);
  }, []);

  const handleItemTouchEndLong = useCallback(() => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const batchDelete = useCallback(async () => {
    const ids = [...selected];
    const results = await Promise.allSettled(ids.map((id) => deleteSession(id)));
    const deletedIds = new Set(ids.filter((_, index) => results[index].status === 'fulfilled'));
    setSessions((prev) => prev.filter((s) => !deletedIds.has(s.session_id)));
    setSelected(new Set());
    setBatchMode(false);
  }, [selected]);

  const exitBatchMode = useCallback(() => {
    setBatchMode(false);
    setSelected(new Set());
  }, []);

  // ---------- 渲染 ----------
  return (
    <PageTransition type="slide" className="history-page-wrapper">
    <div className="mobile-page history-page">
      {/* 顶栏 */}
      <div className="history-topbar">
        {batchMode ? (
          <>
            <button type="button" className="history-back-btn" onClick={exitBatchMode}>取消</button>
            <span className="history-topbar-title">已选 {selected.size} 项</span>
            <button type="button" className="history-delete-btn" onClick={batchDelete}
              disabled={selected.size === 0}>删除</button>
          </>
        ) : (
          <>
            <button type="button" className="history-back-btn" onClick={() => navigate(-1)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
            </button>
            <h2 className="history-topbar-title">历史会话</h2>
            <span style={{ width: 40 }} />
          </>
        )}
      </div>

      {/* 内容区 */}
      <div
        className="history-content"
        ref={containerRef}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* 下拉刷新指示器 */}
        {pullDistance > 0 ? (
          <div className="history-pull-indicator" style={{ height: pullDistance }}>
            <span className={`history-pull-spinner ${pullDistance >= PULL_THRESHOLD ? 'ready' : ''}`}>
              {pullDistance >= PULL_THRESHOLD ? '释放刷新' : '下拉刷新'}
            </span>
          </div>
        ) : null}

        {/* 加载中骨架屏 */}
        {loading ? <SkeletonPlaceholder shape="card" rows={5} /> : null}

        {/* 空状态 */}
        {!loading && sessions.length === 0 ? (
          <EmptyState
            title="暂无历史会话"
            subtitle="登录后与AI导游的对话将保存在这里"
            actionText="去对话"
            onAction={() => navigate('/ai-chat')}
          />
        ) : null}

        {/* 会话列表 */}
        {!loading && sessions.length > 0 ? (
          <div className="history-list">
            {sessions.map((session) => {
              const isSelected = selected.has(session.session_id);
              const isSwiped = swipedId === session.session_id;

              return (
                <div
                  key={session.session_id}
                  className={`history-item ${isSelected ? 'selected' : ''} ${isSwiped ? 'swiped' : ''}`}
                  onTouchStart={(e) => {
                    handleItemTouchStart(session.session_id, e);
                    handleItemTouchStartLong(session.session_id);
                  }}
                  onTouchEnd={(e) => {
                    handleItemTouchEnd(session.session_id, e);
                    handleItemTouchEndLong();
                  }}
                  onTouchMove={() => handleItemTouchEndLong()}
                  onClick={() => {
                    if (batchMode) {
                      toggleSelect(session.session_id);
                    } else if (swipedId) {
                      setSwipedId(null);
                    } else {
                      navigate(`/ai-chat?session=${session.session_id}`);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') navigate(`/ai-chat?session=${session.session_id}`);
                  }}
                >
                  {/* 批量选择框 */}
                  {batchMode ? (
                    <span className={`history-checkbox ${isSelected ? 'checked' : ''}`}>
                      {isSelected ? (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                      ) : null}
                    </span>
                  ) : null}

                  {/* 内容 */}
                  <div className="history-item-body">
                    <div className="history-item-top">
                      <span className="history-item-title">{session.title || '新对话'}</span>
                      <span className="history-item-time">{formatTime(session.time ?? session.created_at ?? session.updated_at)}</span>
                    </div>
                    <p className="history-item-preview">{session.preview || '暂无消息'}</p>
                  </div>

                  {/* 侧滑删除按钮 */}
                  {!batchMode ? (
                    <button
                      type="button"
                      className="history-item-delete"
                      onClick={(e) => { e.stopPropagation(); void removeSession(session.session_id); }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  ) : null}
                </div>
              );
            })}

            {/* 加载更多 */}
            {hasMore ? (
              <div className="history-load-more" onClick={() => fetchSessions()}>
                <span>{loading ? '加载中...' : '加载更多'}</span>
              </div>
            ) : (
              <p className="history-list-end">— 已展示全部会话 —</p>
            )}
          </div>
        ) : null}
      </div>
    </div>
    </PageTransition>
  );
}
