export const USERNAME_REGEX = /^[A-Za-z0-9._-]{3,20}$/;
export const PASSWORD_REGEX =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,}$/;

export function validateUsername(username: string): boolean {
  return USERNAME_REGEX.test(username);
}

export function validatePassword(password: string): boolean {
  return PASSWORD_REGEX.test(password);
}

export type PasswordStrength = 'weak' | 'medium' | 'strong';

export function getPasswordStrength(password: string): PasswordStrength {
  let score = 0;

  if (password.length >= 8) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z\d]/.test(password)) score += 1;
  if (password.length >= 12) score += 1;

  if (score >= 5 && validatePassword(password)) {
    return 'strong';
  }

  if (score >= 3) {
    return 'medium';
  }

  return 'weak';
}
