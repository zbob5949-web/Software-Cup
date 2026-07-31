import type { ReactNode } from 'react';

export interface EmptyStateProps {
  /** 占位图标（SVG 或 ReactNode） */
  image?: ReactNode;
  /** 主文案 */
  title?: string;
  /** 副文案 */
  subtitle?: string;
  /** 操作按钮文案 */
  actionText?: string;
  /** 操作按钮回调 */
  onAction?: () => void;
  /** 自定义类名 */
  className?: string;
}

const EmptyIcon = () => (
  <svg width="120" height="120" viewBox="0 0 120 120" fill="none" style={{ opacity: 0.35 }}>
    <circle cx="60" cy="60" r="58" stroke="currentColor" strokeWidth="1.5" strokeDasharray="6 4" />
    <rect x="36" y="38" width="48" height="36" rx="6" stroke="currentColor" strokeWidth="1.5" />
    <line x1="44" y1="52" x2="76" y2="52" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="44" y1="58" x2="68" y2="58" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="44" y1="64" x2="60" y2="64" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <circle cx="60" cy="82" r="3" fill="currentColor" />
    <line x1="48" y1="82" x2="72" y2="82" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
  </svg>
);

/** 通用空状态组件：列表无数据、搜索无结果等场景复用 */
export function EmptyState({
  image,
  title = '暂无数据',
  subtitle,
  actionText,
  onAction,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`empty-state ${className}`}>
      <div className="empty-state-icon">{image ?? <EmptyIcon />}</div>
      <h3 className="empty-state-title">{title}</h3>
      {subtitle ? <p className="empty-state-subtitle">{subtitle}</p> : null}
      {actionText && onAction ? (
        <button type="button" className="empty-state-action" onClick={onAction}>
          {actionText}
        </button>
      ) : null}
    </div>
  );
}
