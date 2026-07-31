import { describe, expect, it } from 'vitest';
import {
  getPasswordStrength,
  validatePassword,
  validateUsername,
} from '../validation';

describe('validation helpers', () => {
  it('accepts valid usernames and rejects invalid ones', () => {
    expect(validateUsername('user_01')).toBe(true);
    expect(validateUsername('ab')).toBe(false);
    expect(validateUsername('this-username-is-way-too-long')).toBe(false);
    expect(validateUsername('invalid name')).toBe(false);
  });

  it('enforces password complexity rules', () => {
    expect(validatePassword('Aa1!aaaa')).toBe(true);
    expect(validatePassword('password')).toBe(false);
    expect(validatePassword('PASSWORD1!')).toBe(false);
    expect(validatePassword('Password!')).toBe(false);
    expect(validatePassword('Password1')).toBe(false);
  });

  it('calculates password strength tiers', () => {
    expect(getPasswordStrength('abc')).toBe('weak');
    expect(getPasswordStrength('Password1')).toBe('medium');
    expect(getPasswordStrength('Password1!X')).toBe('strong');
  });
});
