const STORAGE_KEYS = {
  adminToken: "artio.adminToken",
  apiKey: "artio.apiKey",
} as const;

export const AUTH_EVENTS = {
  changed: "artio:auth-changed",
} as const;

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function dispatchAuthChangedEvent() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(AUTH_EVENTS.changed));
}

export function getAdminToken(): string | null {
  return getStorage()?.getItem(STORAGE_KEYS.adminToken) ?? null;
}

export function setAdminToken(token: string): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(STORAGE_KEYS.adminToken, token.trim());
  dispatchAuthChangedEvent();
}

export function clearAdminToken(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(STORAGE_KEYS.adminToken);
  dispatchAuthChangedEvent();
}

export function getApiKey(): string | null {
  return getStorage()?.getItem(STORAGE_KEYS.apiKey) ?? null;
}

export function setApiKey(key: string): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(STORAGE_KEYS.apiKey, key.trim());
  dispatchAuthChangedEvent();
}

export function clearApiKey(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(STORAGE_KEYS.apiKey);
  dispatchAuthChangedEvent();
}

export function hasOperatorAuth(): boolean {
  return Boolean(getAdminToken() || getApiKey());
}

