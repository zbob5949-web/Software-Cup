import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

const baseInput =
  'w-full border border-solid border-[#DDE5EF] rounded-[12px] px-[14px] py-[10px] ' +
  'bg-[#FAFBFC] text-[#1F2937] text-[0.88rem] ' +
  'transition-all duration-200 ease-out outline-none ' +
  'placeholder:text-[#B0BCC8] ' +
  'focus:border-[#18A999] focus:bg-[#fff] focus:shadow-[0_0_0_4px_rgba(24,169,153,0.07)] ' +
  'disabled:cursor-not-allowed disabled:opacity-50';

const errorInput = '!border-[#DC2626] !bg-[#FFF5F5]';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ hasError, className, ...rest }, ref) => (
    <input
      ref={ref}
      className={cn(baseInput, hasError && errorInput, className)}
      {...rest}
    />
  ),
);

Input.displayName = 'Input';
