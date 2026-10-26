import type { AppState } from "./domain";

type Fetcher = typeof fetch;

export interface UpdateStatus {
  checked: boolean;
  updateAvailable: boolean;
  latestVersion?: string;
  downloads?: { windows?: string; macos?: string };
}

export class ApiError extends Error {
  constructor(message: string, readonly code: string, readonly status: number) {
    super(message);
  }
}

export function createApiClient(fetcher: Fetcher = globalThis.fetch.bind(globalThis)) {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetcher(path, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    const payload = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      const error = (payload ?? {}) as { code?: string; message?: string };
      throw new ApiError(error.message || response.statusText, error.code || "request_failed", response.status);
    }
    return payload as T;
  }

  return {
    codexStatus: (refresh=false) => request<import('./CodexSettings').CodexStatus>(`/api/codex/status${refresh ? '?refresh=true' : ''}`),
    codexLogin: () => request<{authUrl: string}>('/api/codex/login', {method:'POST'}),
    codexTest: () => request<{ready: boolean; status: string}>('/api/codex/test', {method:'POST'}),
    lineStatus: () => request<import("./LineConnection").LineStatus>("/api/line/status"),
    lineLogin: () => request("/api/line/login", {method:"POST"}),
    lineLogout: () => request("/api/line/logout", {method:"POST"}),
    lineContacts: (refresh=false) => request<import("./LineConnection").LineContact[]>(refresh?"/api/line/contacts/refresh":"/api/line/contacts", refresh?{method:"POST"}:{}),
    updateTarget: (target:import("./domain").Target) => request<import("./domain").Target>(`/api/targets/${encodeURIComponent(target.id)}`,{method:"PUT",body:JSON.stringify(target)}),
    addLineTarget: (contactId:string, assignment:import("./domain").Target) => request<import("./domain").Target>("/api/line/contacts/add", {method:"POST",body:JSON.stringify({contactId,assignment})}),
    bindLineTarget: (targetId:string,contactId:string) => request<import("./domain").Target>("/api/line/targets/bind",{method:"POST",body:JSON.stringify({targetId,contactId})}),
    loadState: () => request<AppState>("/api/state"),
    loadAbout: () => request<{ html: string }>("/api/about"),
    updateStatus: () => request<UpdateStatus>("/api/update"),
    saveState: (state: AppState) => request<AppState>("/api/state", { method: "PUT", body: JSON.stringify(state) }),
    monitorStatus: () => request<{ enabled: boolean; testMode: boolean; status: string }>("/api/monitor/status"),
  };
}

export const api = createApiClient();
