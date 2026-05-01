import '@testing-library/jest-dom';
import { beforeEach } from 'vitest';

Object.defineProperty(window.navigator, 'language', {
  configurable: true,
  value: 'zh-CN',
});

beforeEach(() => {
  window.sessionStorage.clear();
});
