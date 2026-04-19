/**
 * Generate a unique ID that works in all browsers.
 * Uses crypto.randomUUID() when available, falls back to timestamp + random.
 *
 * This is safe for UI component IDs (not for cryptographic purposes).
 */
export function generateId(): string {
  // Try native crypto.randomUUID first (modern browsers, HTTPS)
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch {
      // Fall through to fallback
    }
  }

  // Fallback: timestamp + random string
  // Format: 1234567890123-abc123def
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Generate a UUID v4 compatible string without crypto API.
 * Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
 *
 * Use this when you need RFC4122 UUID format.
 */
export function generateUUID(): string {
  // Try native crypto.randomUUID first
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch {
      // Fall through to fallback
    }
  }

  // Fallback: UUID v4 format using Math.random()
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
