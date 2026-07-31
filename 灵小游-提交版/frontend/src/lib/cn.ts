/**
 * cn() — Conditional class name utility
 *
 * Accepts strings, objects (key=class, value=boolean), and arrays,
 * filters falsy values, and joins with space.
 *
 * Examples:
 *   cn('btn', { active: true, disabled: false })  → 'btn active'
 *   cn('a', false && 'b', 'c')                     → 'a c'
 */

type ClassValue = string | number | null | undefined | false | ClassValue[] | { [key: string]: unknown };

export function cn(...inputs: ClassValue[]): string {
  const classes: string[] = [];

  for (const input of inputs) {
    if (!input) continue;

    if (typeof input === 'string' || typeof input === 'number') {
      classes.push(String(input));
    } else if (Array.isArray(input)) {
      const nested = cn(...input);
      if (nested) classes.push(nested);
    } else if (typeof input === 'object') {
      for (const [key, value] of Object.entries(input)) {
        if (value) classes.push(key);
      }
    }
  }

  return classes.join(' ');
}
