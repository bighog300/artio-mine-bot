import { beforeEach, describe, expect, it } from "vitest";
import {
  clearAdminToken,
  clearApiKey,
  getAdminToken,
  getApiKey,
  hasOperatorAuth,
  setAdminToken,
  setApiKey,
} from "@/lib/auth";
import { ApiAuthError, buildAuthHeaders, isApiAuthError } from "@/lib/api";

describe("auth storage helpers", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("stores and clears admin tokens", () => {
    expect(getAdminToken()).toBeNull();
    setAdminToken(" admin-token ");
    expect(getAdminToken()).toBe("admin-token");
    clearAdminToken();
    expect(getAdminToken()).toBeNull();
  });

  it("stores and clears API keys", () => {
    expect(getApiKey()).toBeNull();
    setApiKey(" api-key ");
    expect(getApiKey()).toBe("api-key");
    clearApiKey();
    expect(getApiKey()).toBeNull();
  });
});

describe("auth bridge headers", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("prefers X-Admin-Token when both auth methods are present", () => {
    setAdminToken("admin-token");
    setApiKey("api-key");
    expect(buildAuthHeaders()).toEqual({ "X-Admin-Token": "admin-token" });
  });

  it("falls back to X-API-Key and reports auth presence", () => {
    setApiKey("api-key");
    expect(buildAuthHeaders()).toEqual({ "X-API-Key": "api-key" });
    expect(hasOperatorAuth()).toBe(true);
  });

  it("exposes a recognizable auth error", () => {
    const error = new ApiAuthError("Admin authentication required");
    expect(isApiAuthError(error)).toBe(true);
    expect(isApiAuthError(new Error("random"))).toBe(false);
  });
});

