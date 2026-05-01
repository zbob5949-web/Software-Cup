import { describe, expect, it } from 'vitest';
import { getStatusMessage } from '../toast';

describe('toast message mapping', () => {
  it('maps known backend status codes to localized messages', () => {
    expect(getStatusMessage(200, 'zh-CN')).toBe('注册成功');
    expect(getStatusMessage(400, 'zh-CN')).toBe('提交参数有误，请检查输入内容');
    expect(getStatusMessage(409, 'zh-CN')).toBe('用户名已存在，请更换后重试');
    expect(getStatusMessage(500, 'zh-CN')).toBe('服务器异常，请稍后再试');
  });

  it('falls back to network or unknown messages', () => {
    expect(getStatusMessage(0, 'zh-CN')).toBe('网络请求失败，请检查网络连接');
    expect(getStatusMessage(-1, 'zh-CN')).toBe('网络请求失败，请检查网络连接');
    expect(getStatusMessage(418, 'zh-CN')).toBe('发生未知错误，请稍后重试');
  });
});
