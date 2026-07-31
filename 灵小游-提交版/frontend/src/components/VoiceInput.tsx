import { useCallback, useEffect, useRef, useState } from 'react';
import { transcribeAudio } from '../api/asr';
import { getLocale, t } from '../lib/i18n';

/** 录音最短时长（秒），不足视为误触 */
const MIN_DURATION = 0.5;
/** 录音最长时长（秒），到时自动停止并上传 */
const MAX_DURATION = 60;
/** 上滑取消距离阈值（px） */
const CANCEL_SWIPE = 70;

type Phase = 'idle' | 'recording' | 'cancelling' | 'loading' | 'error';

export type VoiceInputProps = {
  onResult: (text: string) => void;
  onClose: () => void;
};

export function VoiceInput({ onResult, onClose }: VoiceInputProps) {
  const locale = getLocale();
  const [phase, setPhase] = useState<Phase>('idle');
  const [panelVisible, setPanelVisible] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  /** 上滑进度 0~1，用于驱动取消区域的视觉过渡 */
  const [cancelProgress, setCancelProgress] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startYRef = useRef(0);
  const startTimeRef = useRef(0);
  const streamRef = useRef<MediaStream | null>(null);
  const cancelledRef = useRef(false);
  const autoStopRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mimeTypeRef = useRef('audio/webm');
  const lastVibrateRef = useRef(0);

  /** 面板滑入动画：组件挂载后下一帧触发 */
  useEffect(() => {
    const raf = requestAnimationFrame(() => setPanelVisible(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  /** 面板打开时阻止页面滚动，卸载时恢复 */
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  /** Toast 自动消失 */
  useEffect(() => {
    if (!toastMsg) return;
    const id = window.setTimeout(() => setToastMsg(''), 2200);
    return () => window.clearTimeout(id);
  }, [toastMsg]);

  /** 释放麦克风流 */
  function releaseStream() {
    if (autoStopRef.current) {
      clearTimeout(autoStopRef.current);
      autoStopRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }

  /** 识别完成或关闭 */
  const finish = useCallback(
    (text: string) => {
      releaseStream();
      if (text.trim()) {
        onResult(text.trim());
      }
      onClose();
    },
    [onResult, onClose],
  );

  /** 开始录音 */
  const beginRecord = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      mimeTypeRef.current = mimeType;

      const recorder = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 64000 });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      cancelledRef.current = false;
      startTimeRef.current = Date.now();

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        if (cancelledRef.current) return;

        const duration = (Date.now() - startTimeRef.current) / 1000;
        if (duration < MIN_DURATION) {
          setPhase('idle');
          setCancelProgress(0);
          return;
        }

        setPhase('loading');
        setCancelProgress(0);

        const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current });

        try {
          const text = await transcribeAudio(blob, 'zh');
          finish(text);
        } catch {
          setPhase('error');
          setToastMsg(t('voice.error', locale));
          setTimeout(() => {
            setPhase('idle');
          }, 1600);
        }
      };

      recorder.start();
      setPhase('recording');
      setCancelProgress(0);

      // 最长录制自动停止
      autoStopRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }, MAX_DURATION * 1000);
    } catch (err: unknown) {
      const msg =
        err instanceof DOMException && err.name === 'NotAllowedError'
          ? t('voice.permissionDenied', locale)
          : err instanceof DOMException && err.name === 'NotReadableError'
            ? t('voice.micBusy', locale)
            : t('voice.micUnavailable', locale);
      setToastMsg(msg);
      setPhase('error');
      setTimeout(() => setPhase('idle'), 2000);
    }
  }, [finish, locale]);

  /* ========== Touch 事件（上滑取消） ========== */

  const onTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      if (phase === 'loading') return;
      const touch = e.touches[0];
      startYRef.current = touch.clientY;
      setCancelProgress(0);
      void beginRecord();
      navigator.vibrate?.(15);
    },
    [beginRecord, phase],
  );

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    if (phase !== 'recording' && phase !== 'cancelling') return;

    // 上滑距离（正数 = 手指向上移动）
    const delta = startYRef.current - e.touches[0].clientY;
    const progress = Math.min(1, Math.max(0, delta / CANCEL_SWIPE));
    setCancelProgress(progress);

    if (delta > CANCEL_SWIPE) {
      cancelledRef.current = true;
      setPhase('cancelling');
      // 进入取消区时震动一次
      if (Date.now() - lastVibrateRef.current > 300) {
        navigator.vibrate?.(20);
        lastVibrateRef.current = Date.now();
      }
    } else {
      cancelledRef.current = false;
      setPhase('recording');
    }
  }, [phase]);

  const onTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      if (cancelledRef.current) {
        // 上滑取消：释放所有资源，直接回到 idle
        releaseStream();
        setPhase('idle');
        setCancelProgress(0);
      } else if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      navigator.vibrate?.(15);
    },
    [],
  );

  /* ========== Mouse 事件（桌面调试用） ========== */

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      if (phase === 'loading') return;
      void beginRecord();
    },
    [beginRecord, phase],
  );

  const onMouseUp = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  /* ========== 面板关闭 ========== */

  const handleOverlayClick = useCallback(() => {
    if (phase === 'loading') return;
    releaseStream();
    onClose();
  }, [phase, onClose]);

  /* ========== 渲染 ========== */

  const isCancelling = phase === 'cancelling';

  return (
    <div
      className={`voice-panel-overlay ${panelVisible ? 'voice-panel--open' : ''}`}
      onClick={handleOverlayClick}
    >
      {/* Toast 提示 */}
      {toastMsg ? (
        <div className="voice-toast" onClick={(e) => e.stopPropagation()}>
          {toastMsg}
        </div>
      ) : null}

      <div className="voice-panel" onClick={(e) => e.stopPropagation()}>
        {/* ---- 上滑取消区域（顶部） ---- */}
        <div
          className={`voice-cancel-zone ${isCancelling ? 'voice-cancel-zone--active' : ''}`}
          style={{
            '--cancel-progress': cancelProgress,
          } as React.CSSProperties}
        >
          {/* 取消箭头 + 文字 */}
          <div className="voice-cancel-hint">
            {/* 上滑箭头图标 */}
            <svg
              className={`voice-cancel-arrow ${isCancelling ? 'voice-cancel-arrow--active' : ''}`}
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
            <span className="voice-cancel-label">
              {isCancelling ? t('voice.releaseCancel', locale) : t('voice.slideUpCancel', locale)}
            </span>
          </div>

          {/* 取消圆环（到达阈值时显示） */}
          <div className={`voice-cancel-ring-wrap ${isCancelling ? 'show' : ''}`}>
            <svg width="72" height="72" viewBox="0 0 72 72">
              <circle
                cx="36" cy="36" r="30"
                fill="none"
                stroke="#FF4D4F"
                strokeWidth="2.5"
                strokeDasharray="6 4"
                opacity="0.6"
              />
              <circle
                cx="36" cy="36" r="30"
                fill="none"
                stroke="#FF4D4F"
                strokeWidth="2.5"
                strokeDasharray="6 4"
                className="voice-cancel-ring-rotate"
              />
              <line x1="26" y1="26" x2="46" y2="46" stroke="#FF4D4F" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
        </div>

        {/* ---- 波形动画条 ---- */}
        <div className="voice-panel-bars">
          {Array.from({ length: 7 }).map((_, i) => (
            <span
              key={i}
              className={`voice-panel-bar ${phase === 'recording' ? 'animate' : ''} ${isCancelling ? 'cancel' : ''}`}
            />
          ))}
        </div>

        {/* ---- 状态提示文字 ---- */}
        <p className="voice-panel-hint">
          {phase === 'idle' && t('voice.holdToSpeak', locale)}
          {phase === 'recording' && t('voice.releaseToSend', locale)}
          {phase === 'cancelling' && t('voice.releaseCancel', locale)}
          {phase === 'loading' && t('voice.recognizing', locale)}
          {phase === 'error' && t('voice.error', locale)}
        </p>

        {/* ---- 录音按钮区域 ---- */}
        <div className={`voice-panel-hold-area ${isCancelling ? 'cancel' : ''}`}>
          <button
            type="button"
            className={`voice-panel-record-btn ${phase}`}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
            onMouseDown={onMouseDown}
            onMouseUp={onMouseUp}
            disabled={phase === 'loading'}
            aria-label={
              phase === 'recording'
                ? t('voice.releaseToSend', locale)
                : t('voice.holdToSpeak', locale)
            }
          >
            {phase === 'loading' ? (
              <span className="voice-panel-spinner" />
            ) : (
              <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
