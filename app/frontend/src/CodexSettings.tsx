import {useEffect, useState} from 'react';
import {api, ApiError} from './api';
import type {Copy} from './i18n';

export interface CodexStatus {
  available: boolean;
  ready: boolean;
  status: string;
  planType?: string;
  loginPending?: boolean;
  loginError?: string | null;
}

export function codexMessage(code: string, copy: Copy): string {
  if (code === 'codex_ready') return copy.codexReady;
  if (code === 'codex_verified') return copy.codexVerified;
  if (code === 'codex_login_required') return copy.codexLoginRequired;
  if (code === 'codex_login_pending') return copy.codexLoginPending;
  if (code === 'codex_not_installed') return copy.codexMissing;
  if (code === 'codex_rate_limited') return copy.codexQuota;
  if (code === 'codex_timeout') return copy.codexTimeout;
  if (code === 'codex_model_unavailable') return copy.codexModelUnavailable;
  return copy.codexFailed;
}

export function useCodexStatus(selected: boolean) {
  const [status, setStatus] = useState<CodexStatus | null>(null);
  async function refresh() { setStatus(await api.codexStatus(true)); }
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await api.codexStatus();
        if (active) setStatus(result);
      } catch {
        if (active) setStatus({available: status?.available ?? selected, ready:false, status:'codex_unavailable'});
      }
      if (active && selected) timer = setTimeout(poll, 5000);
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [selected]);
  return {status, refresh};
}

export function CodexOption({status, selected, copy}: {status: CodexStatus | null; selected: boolean; copy: Copy}) {
  if (!status?.available && !selected) return null;
  return <option value="codex" disabled={!status?.available}>{copy.codexProvider}{!status?.available ? ` (${copy.codexMissing})` : ''}</option>;
}

export function CodexSettings({status, copy, refresh}: {status: CodexStatus | null; copy: Copy; refresh: () => Promise<void>}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [authUrl, setAuthUrl] = useState('');
  useEffect(() => { if (status?.ready) setAuthUrl(''); }, [status?.ready]);

  async function act(kind: 'login' | 'test' | 'refresh') {
    setBusy(true); setMessage('');
    try {
      if (kind === 'login') {
        const result = await api.codexLogin();
        setAuthUrl(result.authUrl);
      } else if (kind === 'test') {
        await api.codexTest();
        setMessage(copy.codexVerified);
      }
      await refresh();
    } catch (error) {
      setMessage(codexMessage(error instanceof ApiError ? error.code : 'codex_unavailable', copy));
    } finally { setBusy(false); }
  }

  return <div className="space-y-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800" aria-live="polite">
    <p className="text-sm font-medium">{status ? codexMessage(status.status, copy) : copy.codexChecking}</p>
    <p className="text-xs leading-5 text-slate-500 dark:text-zinc-400">{copy.codexHint}</p>
    {status?.planType ? <p className="text-xs">{copy.codexPlan}: {status.planType}</p> : null}
    {status?.loginPending ? <p className="text-sm">{copy.codexLoginPending}</p> : null}
    {status?.loginError && !status.ready ? <p className="text-sm text-red-600">{codexMessage(status.loginError, copy)}</p> : null}
    <div className="flex flex-wrap gap-3">
      {!status?.ready && status?.available ? <button type="button" className="primary-button" disabled={busy || status.loginPending} onClick={()=>void act('login')}>{copy.codexLogin}</button> : null}
      {status?.ready ? <button type="button" className="primary-button" disabled={busy} onClick={()=>void act('test')}>{busy ? copy.codexChecking : copy.codexTest}</button> : null}
      <button type="button" className="secondary-button" disabled={busy} onClick={()=>void act('refresh')}>{copy.codexRefresh}</button>
    </div>
    {authUrl && !status?.ready ? <a className="inline-block text-sm text-sky-600 underline" href={authUrl} target="_blank" rel="noopener noreferrer">{copy.codexOpenLogin}</a> : null}
    {message ? <p className="text-sm">{message}</p> : null}
  </div>;
}
