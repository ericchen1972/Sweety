import type { AppState } from "./domain";

type Fetcher = typeof fetch;

export interface TargetExport {
  target: Record<string, unknown>;
  messages: Array<Record<string, unknown>>;
}

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
    loadState: () => request<AppState>("/api/state"),
    loadAbout: () => request<{ html: string }>("/api/about"),
    updateStatus: () => request<UpdateStatus>("/api/update"),
    saveState: (state: AppState) => request<AppState>("/api/state", { method: "PUT", body: JSON.stringify(state) }),
    exportTarget: (targetId: string) => request<TargetExport>(`/api/targets/${encodeURIComponent(targetId)}/export`),
    monitorStatus: () => request<{ enabled: boolean; testMode: boolean; status: string }>("/api/monitor/status"),
  };
}

export const api = createApiClient();
