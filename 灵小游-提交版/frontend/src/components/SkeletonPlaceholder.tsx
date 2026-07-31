import type { CSSProperties } from 'react';

export interface SkeletonProps {
  /** 行数 */
  rows?: number;
  /** 形状：rectangle | circle | card */
  shape?: 'rectangle' | 'circle' | 'card';
  /** 宽度 */
  width?: string | number;
  /** 高度 */
  height?: string | number;
  /** 是否显示呼吸光效 */
  animated?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 内联样式 */
  style?: CSSProperties;
}

/** 通用骨架屏组件：支持地图加载、AI回复气泡、列表卡片等场景 */
export function SkeletonPlaceholder({
  rows = 3,
  shape = 'rectangle',
  width,
  height,
  animated = true,
  className = '',
  style,
}: SkeletonProps) {
  const baseClass = `skeleton-placeholder ${animated ? 'skeleton-animated' : ''} ${className}`;

  // 单个骨架块
  const renderBlock = (w?: number | string, h?: number | string, extraClass = '') => (
    <div
      className={`skeleton-block skeleton-shimmer ${extraClass}`}
      style={{ width: w ?? '100%', height: h ?? 16 }}
    />
  );

  // 圆形骨架（头像）
  if (shape === 'circle') {
    const size = width ?? height ?? 40;
    return <div className={baseClass} style={{ width: size, height: size, borderRadius: '50%', ...style }} />;
  }

  // 卡片骨架（列表用）
  if (shape === 'card') {
    return (
      <div className={baseClass} style={{ ...style }}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="skeleton-card-row">
            {renderBlock(36, 36, 'skeleton-circle')}
            <div className="skeleton-card-lines">
              {renderBlock(`${60 + Math.random() * 30}%`, 14)}
              {renderBlock(`${40 + Math.random() * 20}%`, 12)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // AI 对话气泡骨架
  if (shape === 'rectangle' && className?.includes('ai-bubble')) {
    return (
      <div className={baseClass} style={{ ...style }}>
        {/* 助手气泡骨架 */}
        <div className="skeleton-ai-row">
          <div className="skeleton-block skeleton-shimmer" style={{ width: 36, height: 36, borderRadius: '50%' }} />
          <div className="skeleton-ai-bubble">
            <div className="skeleton-block skeleton-shimmer" style={{ width: '80%', height: 14, marginBottom: 8 }} />
            <div className="skeleton-block skeleton-shimmer" style={{ width: '60%', height: 14, marginBottom: 8 }} />
            <div className="skeleton-block skeleton-shimmer" style={{ width: '40%', height: 14 }} />
          </div>
        </div>
        {/* 用户气泡骨架 */}
        <div className="skeleton-ai-row skeleton-ai-row-right">
          <div className="skeleton-ai-bubble skeleton-ai-bubble-user">
            <div className="skeleton-block skeleton-shimmer" style={{ width: 120, height: 14 }} />
          </div>
        </div>
      </div>
    );
  }

  // 地图骨架屏
  if (className?.includes('map')) {
    return (
      <div className={baseClass} style={{ ...style, height: height ?? 240, position: 'relative' }}>
        <div className="skeleton-map-radar" />
      </div>
    );
  }

  // 默认：矩形行骨架
  return (
    <div className={baseClass} style={{ ...style }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="skeleton-block skeleton-shimmer"
          style={{
            width: i === rows - 1 ? (width ?? '60%') : (width ?? '100%'),
            height: height ?? 14,
            marginBottom: i < rows - 1 ? 10 : 0,
          }}
        />
      ))}
    </div>
  );
}
