import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/cn';

const variantStyles = {
  primary:
    'border-0 bg-gradient-to-br from-[#18A999] to-[#0F766E] text-white ' +
    'shadow-[0_6px_16px_rgba(24,169,153,0.30)] ' +
    'hover:translate-y-[-1px] hover:shadow-[0_12px_28px_rgba(24,169,153,0.30)] ' +
    'active:translate-y-0',
  secondary:
    'bg-white text-[#0F766E] border border-solid border-[rgba(24,169,153,0.25)] ' +
    'hover:bg-[rgba(24,169,153,0.06)] hover:border-[#18A999] ' +
    'active:bg-[rgba(24,169,153,0.10)]',
  ghost:
    'bg-transparent text-[#0F766E] border-0 ' +
    'hover:bg-[rgba(24,169,153,0.06)] ' +
    'active:bg-[rgba(24,169,153,0.10)]',
  danger:
    'bg-white text-[#EF4444] border border-solid border-[rgba(239,68,68,0.25)] ' +
    'hover:bg-[#FEF2F2] hover:border-[#EF4444]',
};

const sizeStyles = {
  sm: 'min-h-[36px] px-3 py-[6px] text-[0.82rem] rounded-[10px]',
  md: 'min-h-[44px] px-4 py-[9px] text-[0.88rem] rounded-[10px]',
  lg: 'min-h-[52px] px-5 py-[11px] text-[0.95rem] rounded-[12px]',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: keyof typeof variantStyles;
  size?: keyof typeof sizeStyles;
  isLoading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading,
  disabled,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-[6px] font-semibold',
        'transition-all duration-200 ease-out select-none',
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0',
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      disabled={disabled || isLoading}
      {...rest}
    >
      {isLoading && <span className="spinner" style={{ width: 16, height: 16 }} />}
      {children}
    </button>
  );
}
