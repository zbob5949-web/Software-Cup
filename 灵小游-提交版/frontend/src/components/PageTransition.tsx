import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

// ====================== 导航方向追踪 ======================
type NavContextValue = {
  direction: 'forward' | 'backward';
  historyStack: string[];
};

const NavContext = createContext<NavContextValue>({ direction: 'forward', historyStack: [] });

export function NavProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [stack, setStack] = useState<string[]>([location.pathname]);
  const directionRef = useRef<'forward' | 'backward'>('forward');
  const prevLen = useRef(1);

  useEffect(() => {
    const current = location.pathname;
    setStack((prev) => {
      const idx = prev.lastIndexOf(current);
      if (idx >= 0 && idx < prev.length - 1) {
        // 后退：当前路径在栈中找到
        directionRef.current = 'backward';
        return prev.slice(0, idx + 1);
      }
      // 前进：新路径
      directionRef.current = 'forward';
      return [...prev, current];
    });
  }, [location.pathname]);

  // 页面跳转时立即停止所有正在播放的音频
  useEffect(() => {
    // 杀死所有 Audio 元素
    document.querySelectorAll('audio').forEach((el) => {
      el.pause();
      el.removeAttribute('src');
      el.load();
    });
    // 杀死 SpeechSynthesis
    window.speechSynthesis?.cancel();
    // 通知所有 Live2D iframe 停止
    document.querySelectorAll('iframe').forEach((frame) => {
      try { frame.contentWindow?.postMessage({ type: 'digital-human-stop' }, '*'); } catch { /* ignore */ }
      try { frame.contentWindow?.postMessage({ type: 'digital-human-mute' }, '*'); } catch { /* ignore */ }
    });
  }, [location.pathname]);

  // 监听浏览器前进/后退
  useEffect(() => {
    const handlePop = () => {
      directionRef.current = 'backward';
    };
    window.addEventListener('popstate', handlePop);
    return () => window.removeEventListener('popstate', handlePop);
  }, []);

  const value: NavContextValue = {
    direction: directionRef.current,
    historyStack: stack,
  };

  return <NavContext.Provider value={value}>{children}</NavContext.Provider>;
}

export function useNavDirection() {
  return useContext(NavContext).direction;
}

// ====================== 页面转场容器 ======================
interface PageTransitionProps {
  children: ReactNode;
  /** 动画类型：slide(左右滑动) | fade(淡入) | modal(从下向上) */
  type?: 'slide' | 'fade' | 'modal';
  className?: string;
}

export function PageTransition({ children, type = 'slide', className = '' }: PageTransitionProps) {
  const direction = useNavDirection();
  const [animating, setAnimating] = useState(true);

  useEffect(() => {
    setAnimating(true);
    const id = setTimeout(() => setAnimating(false), 350);
    return () => clearTimeout(id);
  }, [direction]);

  const animClass = type === 'slide'
    ? (direction === 'forward' ? 'page-slide-in-right' : 'page-slide-in-left')
    : type === 'modal'
      ? 'page-modal-in'
      : 'page-fade-in';

  return (
    <div className={`page-transition ${animClass} ${animating ? 'animating' : ''} ${className}`}>
      {children}
    </div>
  );
}
