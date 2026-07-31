import type { Locale } from './i18n';
import { t } from './i18n';

export type ToastTone = 'success' | 'error';

export type ToastState = {
  id: number;
  message: string;
  tone: ToastTone;
};

export function getStatusMessage(status: number, locale: Locale): string {
  switch (status) {
    case 200:
      return t('toast.success', locale);
    case 400:
      return t('toast.badRequest', locale);
    case 409:
      return t('toast.conflict', locale);
    case 500:
      return t('toast.serverError', locale);
    case 0:
    case -1:
      return t('toast.networkError', locale);
    default:
      return t('toast.unknown', locale);
  }
}
