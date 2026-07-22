import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import {
  Archive,
  Bot,
  Check,
  Clock3,
  Download,
  Gauge,
  Info,
  LayoutDashboard,
  Menu,
  MessageCircleMore,
  Pencil,
  Plus,
  RotateCcw,
  Settings,
  ShieldAlert,
  Sparkles,
  SquarePen,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { basePersonas as fallbackBasePersonas } from "./catalog";
import { api, type UpdateStatus } from "./api";
import sweetyLogo from "../../../web/images/logo.png";
import {
  aggregateDurationMs,
  canDeleteCustomPersona,
  createId,
  detectLocale,
  endTarget,
  formatDurationHours,
  reviveTarget,
  targetDurationMs,
  validateCustomName,
  validateReplyDelay,
  validateTargetName,
  type AgeGroup,
  type AppState,
  type BasePersona,
  type CatalogSource,
  type CustomCatalogItem,
  type Gender,
  type Locale,
  type Target,
} from "./domain";
import { personaPreview } from "./personaPreview";
import { getCopy, type Copy } from "./i18n";
import { defaultState, loadState, saveState } from "./storage";
import { UpdateNotice, startUpdateStatusPolling } from "./UpdateNotice";

type Page = "dashboard" | "settings" | "targets" | "catalog" | "about";
type CatalogKind = "persona";
type StateSetter = (updater: (current: AppState) => AppState) => void;

const ageGroups: AgeGroup[] = ["20-35", "35-50", "50-65", "65+"];

function cachedBasePersonas(state: AppState): BasePersona[] {
  return state.basePersonas.length ? state.basePersonas : fallbackBasePersonas;
}

function App() {
  const locale = useMemo(() => detectLocale(window.navigator.language), []);
  const copy = getCopy(locale);
  const [state, setAppState] = useState<AppState>(() => structuredClone(defaultState));
  const [activePage, setActivePage] = useState<Page>("dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>({ checked: false, updateAvailable: false });

  const setState: StateSetter = (updater) => setAppState((current) => {
    const next = updater(current);
    void saveState(next).catch((error: unknown) => {
      setToast(error instanceof Error ? error.message : (locale === "zh-TW" ? "儲存失敗" : "Save failed"));
    });
    return next;
  });

  useEffect(() => {
    document.documentElement.lang = locale === "zh-TW" ? "zh-Hant" : "en";
  }, [locale]);

  useEffect(() => {
    return startUpdateStatusPolling(() => api.updateStatus(), setUpdateStatus);
  }, []);

  useEffect(() => {
    if (loading) return;
    let cancelled = false;
    const refreshMonitor = async () => {
      try {
        const status = await api.monitorStatus();
        if (!cancelled) {
          setAppState((current) => current.monitoringEnabled === status.enabled
            ? current
            : { ...current, monitoringEnabled: status.enabled });
        }
      } catch {
        // The management view can remain usable while the local monitor is restarting.
      }
    };
    void refreshMonitor();
    const timer = window.setInterval(refreshMonitor, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [loading]);

  useEffect(() => {
    let active = true;
    void loadState()
      .then((loaded) => {
        if (active) setAppState(loaded);
      })
      .catch((error: unknown) => {
        if (active) setLoadError(error instanceof Error ? error.message : "Unable to load Sweety");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(""), 2600);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const selectedCount = state.targets.filter(
    (target) => target.status === "active" && target.replyEnabled,
  ).length;

  const pages = [
    { id: "dashboard" as const, label: copy.dashboard, icon: LayoutDashboard },
    { id: "settings" as const, label: copy.settings, icon: Settings },
    { id: "targets" as const, label: copy.targets, icon: ShieldAlert },
    { id: "catalog" as const, label: copy.catalog, icon: Sparkles },
    { id: "about" as const, label: copy.aboutSweety, icon: Info },
  ];

  function navigate(page: Page) {
    setActivePage(page);
    setMobileMenuOpen(false);
  }

  if (loading) {
    return <main className="flex min-h-dvh items-center justify-center bg-slate-50 text-sm font-medium text-slate-600 dark:bg-zinc-950 dark:text-zinc-300">{locale === "zh-TW" ? "正在載入 Sweety..." : "Loading Sweety..."}</main>;
  }

  if (loadError) {
    return <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-6 dark:bg-zinc-950"><section className="max-w-md text-center"><h1 className="text-lg font-semibold">{locale === "zh-TW" ? "無法連接 Sweety" : "Unable to connect to Sweety"}</h1><p className="mt-3 break-words text-sm text-slate-500 dark:text-zinc-400">{loadError}</p><button type="button" className="primary-button mt-5" onClick={() => window.location.reload()}>{locale === "zh-TW" ? "重試" : "Retry"}</button></section></main>;
  }

  return (
    <main className="min-h-dvh bg-slate-50 text-slate-950 dark:bg-zinc-950 dark:text-zinc-50">
      <div className="grid min-h-dvh lg:grid-cols-[17rem_1fr]">
        <aside
          className={`${mobileMenuOpen ? "fixed inset-0 z-40 flex" : "hidden"} border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950 lg:static lg:flex lg:min-h-dvh lg:flex-col`}
        >
          <div className="flex h-full w-[17rem] flex-col border-r border-zinc-200 bg-white px-3 py-4 dark:border-zinc-800 dark:bg-zinc-950 lg:w-full lg:border-r-0">
            <div className="flex h-14 items-center justify-between px-3">
              <button type="button" onClick={() => navigate("dashboard")} className="flex items-center gap-3 text-left">
                <img src={sweetyLogo} alt="" className="h-10 w-10 rounded-md object-contain shadow-sm" />
                <span>
                  <strong className="block text-lg font-semibold">{copy.appName}</strong>
                  <span className="block text-xs text-slate-500 dark:text-zinc-500">Anti-scam companion</span>
                </span>
              </button>
              <button type="button" className="icon-button lg:hidden" onClick={() => setMobileMenuOpen(false)} title={copy.close}>
                <X className="h-5 w-5" />
              </button>
            </div>

            <nav className="mt-6 space-y-2" aria-label="Main navigation">
              {pages.map((page) => {
                const Icon = page.icon;
                const active = activePage === page.id;
                return (
                  <button
                    key={page.id}
                    type="button"
                    onClick={() => navigate(page.id)}
                    className={`flex min-h-12 w-full items-center gap-3 rounded-md px-4 text-left text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-400 ${
                      active
                        ? "bg-sky-500 text-white shadow-lg shadow-sky-100 dark:shadow-sky-950"
                        : "text-slate-700 hover:bg-slate-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
                    }`}
                  >
                    <Icon className="h-5 w-5" aria-hidden="true" />
                    {page.label}
                  </button>
                );
              })}
            </nav>

            <div className="mt-auto border-t border-zinc-200 px-3 pt-5 dark:border-zinc-800">
              <p className="text-xs leading-5 text-slate-500 dark:text-zinc-500">{copy.slimwebPromo}</p>
              <a
                href="https://slimweb.tw"
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-sky-700 hover:text-sky-800 dark:text-sky-400 dark:hover:text-sky-300"
              >
                {copy.slimwebLink}
              </a>
            </div>
          </div>
          <button
            type="button"
            className="min-w-0 flex-1 bg-zinc-950/30 backdrop-blur-sm lg:hidden"
            aria-label={copy.close}
            onClick={() => setMobileMenuOpen(false)}
          />
        </aside>

        <section className="min-w-0">
          <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95">
            <div className="flex min-h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
              <div className="flex min-w-0 items-center gap-3">
                <button type="button" className="icon-button lg:hidden" onClick={() => setMobileMenuOpen(true)} title={copy.menu}>
                  <Menu className="h-5 w-5" />
                </button>
                <h1 className="truncate text-lg font-semibold">{pages.find((page) => page.id === activePage)?.label}</h1>
              </div>
              <div className="flex shrink-0 items-center gap-2 sm:gap-3">
                <span className={`hidden items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold sm:inline-flex ${state.monitoringEnabled ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" : "bg-zinc-100 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400"}`}>
                  <span className={`h-2 w-2 rounded-full ${state.monitoringEnabled ? "bg-emerald-500" : "bg-zinc-400"}`} />
                  {state.monitoringEnabled ? copy.monitoring : copy.stopped}
                </span>
                <span className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300">
                  {copy.selectedTargets} {selectedCount}
                </span>
              </div>
            </div>
          </header>

          <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
            {activePage === "dashboard" ? <Dashboard state={state} locale={locale} copy={copy} updateStatus={updateStatus} /> : null}
            {activePage === "settings" ? <SettingsPage state={state} setState={setState} copy={copy} onToast={setToast} /> : null}
            {activePage === "targets" ? <TargetsPage state={state} setState={setState} locale={locale} copy={copy} onToast={setToast} /> : null}
            {activePage === "catalog" ? <CatalogPage state={state} setState={setState} locale={locale} copy={copy} onToast={setToast} /> : null}
            {activePage === "about" ? <AboutPage copy={copy} /> : null}
          </div>
        </section>
      </div>

      {toast ? (
        <div className="fixed bottom-5 left-1/2 z-[70] -translate-x-1/2 rounded-md bg-zinc-950 px-4 py-3 text-sm font-medium text-white shadow-xl dark:bg-white dark:text-zinc-950">
          {toast}
        </div>
      ) : null}
    </main>
  );
}

function AboutPage({ copy }: { copy: Copy }) {
  const [requestKey, setRequestKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [html, setHtml] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    void api.loadAbout()
      .then((result) => {
        if (active) setHtml(result.html);
      })
      .catch(() => {
        if (active) setFailed(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [requestKey]);

  function retry() {
    setRequestKey((current) => current + 1);
  }

  return (
    <section className="min-h-[20rem]">
      {loading && !failed ? <div className="flex min-h-[20rem] items-center justify-center text-sm text-slate-500 dark:text-zinc-400">{copy.aboutLoading}</div> : null}
      {failed ? (
        <div className="flex min-h-[20rem] flex-col items-center justify-center gap-4 px-6 text-center">
          <p className="text-sm text-slate-600 dark:text-zinc-300">{copy.aboutLoadError}</p>
          <button type="button" className="secondary-button" onClick={retry}>{copy.retry}</button>
        </div>
      ) : null}
      {!loading && !failed ? <article className="about-content" dangerouslySetInnerHTML={{ __html: html }} /> : null}
    </section>
  );
}

function Dashboard({ state, locale, copy, updateStatus }: { state: AppState; locale: Locale; copy: Copy; updateStatus: UpdateStatus }) {
  const metrics = [
    { label: copy.targetCount, value: state.targets.length.toLocaleString(), icon: Users, color: "text-sky-600 bg-sky-100 dark:bg-sky-950 dark:text-sky-300" },
    { label: copy.totalDuration, value: formatDurationHours(aggregateDurationMs(state.targets), locale), icon: Clock3, color: "text-amber-700 bg-amber-100 dark:bg-amber-950 dark:text-amber-300" },
    { label: copy.totalRounds, value: state.targets.reduce((sum, target) => sum + target.roundTrips, 0).toLocaleString(), icon: MessageCircleMore, color: "text-emerald-700 bg-emerald-100 dark:bg-emerald-950 dark:text-emerald-300" },
    { label: copy.endedCount, value: state.targets.filter((target) => target.status === "ended").length.toLocaleString(), icon: Archive, color: "text-rose-700 bg-rose-100 dark:bg-rose-950 dark:text-rose-300" },
  ];
  const recent = [...state.targets].sort((a, b) => Date.parse(b.lastReplyAt ?? "0") - Date.parse(a.lastReplyAt ?? "0")).slice(0, 5);

  return (
    <div className="space-y-8">
      <UpdateNotice update={updateStatus} copy={copy} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article key={metric.label} className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-500 dark:text-zinc-400">{metric.label}</p>
                  <p className="mt-3 break-words text-2xl font-semibold text-slate-950 dark:text-white">{metric.value}</p>
                </div>
                <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md ${metric.color}`}>
                  <Icon className="h-5 w-5" />
                </span>
              </div>
            </article>
          );
        })}
      </div>

      <section className="border-t border-zinc-200 pt-7 dark:border-zinc-800">
        <h2 className="section-title">{copy.recentTargets}</h2>
        {recent.length ? (
          <div className="mt-4 overflow-hidden rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
            {recent.map((target, index) => (
              <div key={target.id} className={`flex flex-wrap items-center justify-between gap-3 px-5 py-4 ${index ? "border-t border-zinc-200 dark:border-zinc-800" : ""}`}>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{target.name}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-zinc-500">{target.roundTrips} {copy.rounds}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${target.status === "active" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"}`}>
                  {target.status === "active" ? copy.active : copy.ended}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon={Users} title={copy.noTargets} description={copy.noTargetsHint} />
        )}
      </section>
    </div>
  );
}

function SettingsPage({ state, setState, copy, onToast }: { state: AppState; setState: StateSetter; copy: Copy; onToast: (message: string) => void }) {
  const [form, setForm] = useState(state.settings);
  const [error, setError] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!validateReplyDelay(form.replyDelayMinSeconds, form.replyDelayMaxSeconds)) {
      setError(copy.invalidDelay);
      return;
    }
    setError("");
    setState((current) => ({ ...current, settings: form }));
    onToast(copy.saved);
  }

  return (
    <form onSubmit={submit} className="max-w-3xl space-y-8">
      <section className="space-y-5">
        <h2 className="section-title">{copy.provider}</h2>
        <label className="block">
          <span className="mb-2 block text-sm font-medium">{copy.provider}</span>
          <select className="form-input" value={form.aiProvider} onChange={(event) => setForm({ ...form, aiProvider: event.target.value as AppState["settings"]["aiProvider"] })}>
            <option value="sweety">{copy.sweetyDefault}</option>
            <option value="openai">{copy.openAI}</option>
          </select>
        </label>
        {form.aiProvider === "openai" ? (
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-medium">{copy.apiKey}</span>
              <input type="password" autoComplete="off" className="form-input" value={form.openAiApiKey} onChange={(event) => setForm({ ...form, openAiApiKey: event.target.value })} />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium">{copy.model}</span>
              <input className="form-input" value={form.openAiModel} onChange={(event) => setForm({ ...form, openAiModel: event.target.value })} />
            </label>
          </div>
        ) : null}
      </section>

      <section className="space-y-5 border-t border-zinc-200 pt-7 dark:border-zinc-800">
        <h2 className="section-title">{copy.conversations}</h2>
        <label className="block max-w-sm">
          <span className="mb-2 block text-sm font-medium">{copy.checkInterval}</span>
          <div className="relative">
            <input type="number" min={1} className="form-input pr-14" value={form.checkIntervalSeconds} onChange={(event) => setForm({ ...form, checkIntervalSeconds: Number(event.target.value) })} />
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500 dark:text-zinc-500">{copy.seconds}</span>
          </div>
        </label>
        <div>
          <p className="mb-2 text-sm font-medium">{copy.replyDelay}</p>
          <div className="grid max-w-xl gap-4 sm:grid-cols-2">
            <NumberField label={copy.minimum} suffix={copy.seconds} value={form.replyDelayMinSeconds} onChange={(value) => setForm({ ...form, replyDelayMinSeconds: value })} />
            <NumberField label={copy.maximum} suffix={copy.seconds} value={form.replyDelayMaxSeconds} onChange={(value) => setForm({ ...form, replyDelayMaxSeconds: value })} />
          </div>
        </div>
        {error ? <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p> : null}
      </section>

      <div className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
        <button type="submit" className="primary-button"><Check className="h-4 w-4" /> {copy.save}</button>
      </div>
    </form>
  );
}

function NumberField({ label, suffix, value, onChange }: { label: string; suffix: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-slate-500 dark:text-zinc-400">{label}</span>
      <div className="relative">
        <input type="number" min={0} className="form-input pr-14" value={value} onChange={(event) => onChange(Number(event.target.value))} />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500 dark:text-zinc-500">{suffix}</span>
      </div>
    </label>
  );
}

function TargetsPage({ state, setState, locale, copy, onToast }: { state: AppState; setState: StateSetter; locale: Locale; copy: Copy; onToast: (message: string) => void }) {
  const [tab, setTab] = useState<"active" | "ended">("active");
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<Target | null>(null);
  const [ending, setEnding] = useState<Target | null>(null);
  const [deleting, setDeleting] = useState<Target | null>(null);
  const targets = state.targets.filter((target) => target.status === tab);

  async function exportTarget(target: Target) {
    try {
      const exported = await api.exportTarget(target.id);
      const payload = {
      exported_at: new Date().toISOString(),
      target: {
        ...exported.target,
        persona_name: personaName(target, state, locale),
      },
        messages: exported.messages,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${safeFilename(target.name)}-conversation.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      onToast(error instanceof Error ? error.message : (locale === "zh-TW" ? "輸出失敗" : "Export failed"));
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="inline-flex rounded-md border border-zinc-200 bg-white p-1 dark:border-zinc-800 dark:bg-zinc-900">
          {(["active", "ended"] as const).map((value) => (
            <button key={value} type="button" onClick={() => setTab(value)} className={`min-h-10 rounded px-4 text-sm font-semibold transition ${tab === value ? "bg-zinc-950 text-white dark:bg-white dark:text-zinc-950" : "text-slate-600 hover:bg-slate-100 dark:text-zinc-400 dark:hover:bg-zinc-800"}`}>
              {value === "active" ? copy.active : copy.ended}
              <span className="ml-2 text-xs opacity-70">{state.targets.filter((target) => target.status === value).length}</span>
            </button>
          ))}
        </div>
        <button type="button" className="primary-button" onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> {copy.addTarget}</button>
      </div>

      {targets.length ? (
        <>
          <div className="hidden overflow-x-auto rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 md:block">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead className="border-b border-zinc-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-500">
                <tr>
                  <th className="w-14 px-4 py-3">{copy.replyEnabled}</th>
                  <th className="px-4 py-3">{copy.name}</th>
                  <th className="px-4 py-3">{copy.rounds}</th>
                  <th className="px-4 py-3">{copy.duration}</th>
                  <th className="px-4 py-3">{copy.persona}</th>
                  <th className="px-4 py-3 text-right">{copy.actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {targets.map((target) => (
                  <TargetTableRow key={target.id} target={target} state={state} locale={locale} copy={copy} setState={setState} onEdit={setEditing} onEnd={setEnding} onRevive={(item) => setState((current) => ({ ...current, targets: current.targets.map((targetItem) => targetItem.id === item.id ? reviveTarget(targetItem) : targetItem) }))} onDelete={setDeleting} onExport={exportTarget} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid gap-4 md:hidden">
            {targets.map((target) => (
              <TargetMobileCard key={target.id} target={target} state={state} locale={locale} copy={copy} setState={setState} onEdit={setEditing} onEnd={setEnding} onRevive={(item) => setState((current) => ({ ...current, targets: current.targets.map((targetItem) => targetItem.id === item.id ? reviveTarget(targetItem) : targetItem) }))} onDelete={setDeleting} onExport={exportTarget} />
            ))}
          </div>
        </>
      ) : (
        <EmptyState icon={tab === "active" ? Gauge : Archive} title={tab === "active" ? copy.emptyActive : copy.emptyEnded} description={copy.noTargetsHint} />
      )}

      {addOpen ? <TargetModal mode="create" state={state} locale={locale} copy={copy} onClose={() => setAddOpen(false)} onSave={(target) => { setState((current) => ({ ...current, targets: [...current.targets, target] })); setAddOpen(false); }} /> : null}
      {editing ? <TargetModal mode="edit" existing={editing} state={state} locale={locale} copy={copy} onClose={() => setEditing(null)} onSave={(updated) => { setState((current) => ({ ...current, targets: current.targets.map((target) => target.id === updated.id ? updated : target) })); setEditing(null); }} /> : null}
      {ending ? <ConfirmModal title={copy.markEnded} description={copy.endConfirm} confirmLabel={copy.confirmEnd} onCancel={() => setEnding(null)} onConfirm={() => { setState((current) => ({ ...current, targets: current.targets.map((target) => target.id === ending.id ? endTarget(target) : target) })); setEnding(null); setTab("ended"); }} /> : null}
      {deleting ? <ConfirmModal danger title={copy.deleteForever} description={copy.deleteConfirm} confirmLabel={copy.confirmDelete} onCancel={() => setDeleting(null)} onConfirm={() => { setState((current) => ({ ...current, targets: current.targets.filter((target) => target.id !== deleting.id) })); setDeleting(null); onToast(copy.deleteForever); }} /> : null}
    </div>
  );
}

interface TargetActionsProps {
  target: Target;
  state: AppState;
  locale: Locale;
  copy: Copy;
  setState: StateSetter;
  onEdit: (target: Target) => void;
  onEnd: (target: Target) => void;
  onRevive: (target: Target) => void;
  onDelete: (target: Target) => void;
  onExport: (target: Target) => void;
}

function TargetTableRow(props: TargetActionsProps) {
  const { target, state, locale, copy, setState } = props;
  return (
    <tr>
      <td className="px-4 py-4"><ReplyCheckbox target={target} setState={setState} copy={copy} /></td>
      <td className="max-w-56 px-4 py-4 font-semibold"><span className="block truncate" title={target.name}>{target.name}</span></td>
      <td className="px-4 py-4 tabular-nums">{target.roundTrips}</td>
      <td className="whitespace-nowrap px-4 py-4">{formatDurationHours(targetDurationMs(target), locale)}</td>
      <td className="max-w-48 px-4 py-4"><span className="block truncate">{personaName(target, state, locale)}</span></td>
      <td className="px-4 py-4"><TargetActionButtons {...props} /></td>
    </tr>
  );
}

function TargetMobileCard(props: TargetActionsProps) {
  const { target, state, locale, copy, setState } = props;
  return (
    <article className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="break-words font-semibold">{target.name}</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-zinc-500">{target.roundTrips} {copy.rounds} · {formatDurationHours(targetDurationMs(target), locale)}</p>
        </div>
        <ReplyCheckbox target={target} setState={setState} copy={copy} />
      </div>
      <dl className="mt-4 grid gap-3 text-sm">
        <div><dt className="text-xs text-slate-500 dark:text-zinc-500">{copy.persona}</dt><dd className="mt-1">{personaName(target, state, locale)}</dd></div>
      </dl>
      <div className="mt-4 border-t border-zinc-200 pt-4 dark:border-zinc-800"><TargetActionButtons {...props} /></div>
    </article>
  );
}

function ReplyCheckbox({ target, setState, copy }: { target: Target; setState: StateSetter; copy: Copy }) {
  return (
    <label className={`inline-flex items-center ${target.status === "ended" ? "cursor-not-allowed opacity-40" : "cursor-pointer"}`} title={copy.replyEnabled}>
      <input
        type="checkbox"
        className="h-5 w-5 rounded border-zinc-300 text-sky-600 focus:ring-sky-500 dark:border-zinc-700 dark:bg-zinc-950"
        checked={target.replyEnabled}
        disabled={target.status === "ended"}
        onChange={(event) => setState((current) => ({ ...current, targets: current.targets.map((item) => item.id === target.id ? { ...item, replyEnabled: event.target.checked } : item) }))}
      />
    </label>
  );
}

function TargetActionButtons({ target, copy, onEdit, onEnd, onRevive, onDelete, onExport }: TargetActionsProps) {
  return (
    <div className="flex justify-end gap-2">
      {target.status === "active" ? (
        <>
          <button type="button" className="icon-button" title={copy.editAssignment} onClick={() => onEdit(target)}><Pencil className="h-4 w-4" /></button>
          <button type="button" className="icon-button" title={copy.markEnded} onClick={() => onEnd(target)}><Archive className="h-4 w-4" /></button>
        </>
      ) : (
        <button type="button" className="icon-button" title={copy.revive} onClick={() => onRevive(target)}><RotateCcw className="h-4 w-4" /></button>
      )}
      <button type="button" className="icon-button" title={copy.exportLog} onClick={() => onExport(target)}><Download className="h-4 w-4" /></button>
      {target.status === "ended" ? <button type="button" className="icon-button text-red-600 dark:text-red-400" title={copy.deleteForever} onClick={() => onDelete(target)}><Trash2 className="h-4 w-4" /></button> : null}
    </div>
  );
}

function TargetModal({ mode, existing, state, locale, copy, onClose, onSave }: { mode: "create" | "edit"; existing?: Target; state: AppState; locale: Locale; copy: Copy; onClose: () => void; onSave: (target: Target) => void }) {
  const [name, setName] = useState(existing?.name ?? "");
  const [ageGroup, setAgeGroup] = useState<AgeGroup>(existing?.ageGroup ?? "20-35");
  const [gender, setGender] = useState<Gender>(existing?.gender ?? "female");
  const [personaId, setPersonaId] = useState(existing?.personaId ?? "");
  const [error, setError] = useState("");

  const basePersonas = cachedBasePersonas(state);
  const personaOptions = basePersonas.filter((persona) => persona.ageGroup === ageGroup && persona.gender === gender);
  const customPersonaOptions = state.customPersonas;
  const selectedPersonaSource: CatalogSource = basePersonas.some((persona) => persona.id === personaId) ? "base" : "custom";

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "create" && !validateTargetName(name)) {
      setError(copy.targetNameHint);
      return;
    }
    if (!personaId) {
      setError(copy.selectPersona);
      return;
    }
    onSave({
      id: existing?.id ?? createId("target"),
      name: mode === "edit" ? existing!.name : name.trim(),
      ageGroup,
      gender,
      personaId,
      personaSource: selectedPersonaSource,
      weaponId: "persona-only",
      weaponSource: "base",
      replyEnabled: existing?.replyEnabled ?? false,
      status: existing?.status ?? "active",
      roundTrips: existing?.roundTrips ?? 0,
      firstReplyAt: existing?.firstReplyAt ?? null,
      lastReplyAt: existing?.lastReplyAt ?? null,
      endedAt: existing?.endedAt ?? null,
    });
  }

  return (
    <Modal title={mode === "create" ? copy.addTarget : copy.editAssignment} closeLabel={copy.close} onClose={onClose}>
      <form onSubmit={submit} className="space-y-5">
        {mode === "create" ? (
          <>
            <label className="block"><span className="mb-2 block text-sm font-medium">{copy.targetName}</span><input autoFocus className="form-input" value={name} onChange={(event) => setName(event.target.value)} /><span className="mt-2 block text-xs text-slate-500 dark:text-zinc-500">{copy.targetNameHint}</span></label>
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">{copy.targetNameWarning}</div>
          </>
        ) : (
          <div className="rounded-md bg-slate-100 px-4 py-3 text-sm font-semibold dark:bg-zinc-800">{existing?.name}</div>
        )}
        <div className="rounded-md border border-sky-200 bg-sky-50 p-4 text-sm leading-6 text-sky-900 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-200">{copy.profileNotice}</div>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField label={copy.age} value={ageGroup} onChange={(value) => { setAgeGroup(value as AgeGroup); setPersonaId(""); }} options={ageGroups.map((age) => ({ value: age, label: age }))} />
          <SelectField label={copy.gender} value={gender} onChange={(value) => { setGender(value as Gender); setPersonaId(""); }} options={[{ value: "female", label: copy.female }, { value: "male", label: copy.male }]} />
        </div>
        {personaOptions.length === 0 && customPersonaOptions.length === 0 ? <p className="text-sm text-amber-700 dark:text-amber-300">{copy.noBaseForAge}</p> : null}
        <label className="block">
          <span className="mb-2 block text-sm font-medium">{copy.persona}</span>
          <select className="form-input" value={personaId} onChange={(event) => { setPersonaId(event.target.value); }}>
            <option value="">{copy.selectPersona}</option>
            {personaOptions.length ? <optgroup label={copy.baseOptions}>{personaOptions.map((persona) => <option key={persona.id} value={persona.id}>{persona.name[locale]}</option>)}</optgroup> : null}
            {customPersonaOptions.length ? <optgroup label={copy.customOptions}>{customPersonaOptions.map((persona) => <option key={persona.id} value={persona.id}>{persona.name}</option>)}</optgroup> : null}
          </select>
        </label>
        {error ? <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p> : null}
        <ModalActions copy={copy} onCancel={onClose} submitLabel={mode === "create" ? copy.create : copy.save} />
      </form>
    </Modal>
  );
}

function CatalogPage({ state, setState, locale, copy, onToast }: { state: AppState; setState: StateSetter; locale: Locale; copy: Copy; onToast: (message: string) => void }) {
  const [tab, setTab] = useState<"base" | "custom">("base");
  const [age, setAge] = useState<AgeGroup>("20-35");
  const [gender, setGender] = useState<"all" | Gender>("all");
  const [viewing, setViewing] = useState<{ kind: CatalogKind; item: BasePersona } | null>(null);
  const [editing, setEditing] = useState<{ kind: CatalogKind; item: CustomCatalogItem | null } | null>(null);
  const [deleting, setDeleting] = useState<{ kind: CatalogKind; item: CustomCatalogItem } | null>(null);

  const basePersonas = cachedBasePersonas(state);
  const filteredPersonas = basePersonas.filter((persona) => persona.ageGroup === age && (gender === "all" || persona.gender === gender));

  function cloneBase(kind: CatalogKind, item: BasePersona) {
    const list = state.customPersonas;
    const name = item.name[locale];
    if (!validateCustomName(name, list.map((entry) => entry.name))) {
      onToast(copy.alreadyCloned);
      return;
    }
    const custom: CustomCatalogItem = {
      id: createId(kind),
      name,
      text: item.content[locale],
      imageDataUrl: item.image,
      sourceBaseId: item.id,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setState((current) => ({ ...current, customPersonas: [...current.customPersonas, custom] }));
    setViewing(null);
    setTab("custom");
    onToast(copy.cloned);
  }

  function requestDelete(kind: CatalogKind, item: CustomCatalogItem) {
    if (!canDeleteCustomPersona(item.id, state.targets)) {
      onToast(copy.deleteInUse);
      return;
    }
    setDeleting({ kind, item });
  }

  return (
    <div className="space-y-7">
      <div className="inline-flex max-w-full overflow-x-auto rounded-md border border-zinc-200 bg-white p-1 dark:border-zinc-800 dark:bg-zinc-900">
        <button type="button" onClick={() => setTab("base")} className={`min-h-10 whitespace-nowrap rounded px-4 text-sm font-semibold ${tab === "base" ? "bg-zinc-950 text-white dark:bg-white dark:text-zinc-950" : "text-slate-600 dark:text-zinc-400"}`}>{copy.baseCatalog}</button>
        <button type="button" onClick={() => setTab("custom")} className={`min-h-10 whitespace-nowrap rounded px-4 text-sm font-semibold ${tab === "custom" ? "bg-zinc-950 text-white dark:bg-white dark:text-zinc-950" : "text-slate-600 dark:text-zinc-400"}`}>{copy.customCatalog}</button>
      </div>

      {tab === "base" ? (
        <div className="space-y-9">
          <div className="space-y-3">
            <div className="flex flex-wrap items-end gap-4">
              <div className="w-44"><SelectField label={copy.age} value={age} onChange={(value) => setAge(value as AgeGroup)} options={ageGroups.map((item) => ({ value: item, label: item }))} /></div>
              <SegmentedGender value={gender} onChange={setGender} copy={copy} />
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-500 dark:text-zinc-400">{copy.basePersonaEditHint}</p>
          </div>
          <CatalogSection title={copy.personas} icon={Users}>
            {filteredPersonas.length ? <CardGrid>{filteredPersonas.map((persona) => <BaseCard key={persona.id} item={persona} locale={locale} actionLabel={copy.fullText} onAction={() => setViewing({ kind: "persona", item: persona })} />)}</CardGrid> : <EmptyState icon={Users} title={copy.noBaseForAge} />}
          </CatalogSection>
        </div>
      ) : (
        <div className="space-y-10">
          <CatalogSection title={copy.personas} icon={Users} action={<button type="button" className="primary-button" onClick={() => setEditing({ kind: "persona", item: null })}><Plus className="h-4 w-4" /> {copy.createPersona}</button>}>
            {state.customPersonas.length ? <CardGrid>{state.customPersonas.map((item) => <CustomCard key={item.id} item={item} copy={copy} editLabel={copy.editCustomPersona} onEdit={() => setEditing({ kind: "persona", item })} onDelete={() => requestDelete("persona", item)} />)}</CardGrid> : <EmptyState icon={SquarePen} title={copy.createPersona} />}
          </CatalogSection>
        </div>
      )}

      {viewing ? <BaseDetailModal kind={viewing.kind} item={viewing.item} locale={locale} copy={copy} onClose={() => setViewing(null)} onClone={() => cloneBase(viewing.kind, viewing.item)} /> : null}
      {editing ? <CustomItemModal kind={editing.kind} existing={editing.item} state={state} copy={copy} onClose={() => setEditing(null)} onSave={(item) => { setState((current) => saveCustomItem(current, editing.kind, item)); setEditing(null); }} /> : null}
      {deleting ? <ConfirmModal danger title={copy.deleteItem} description={copy.deleteItemConfirm} confirmLabel={copy.deleteItem} onCancel={() => setDeleting(null)} onConfirm={() => { setState((current) => ({ ...current, customPersonas: current.customPersonas.filter((item) => item.id !== deleting.item.id) })); setDeleting(null); }} /> : null}
    </div>
  );
}

function CatalogSection({ title, icon: Icon, action, children }: { title: string; icon: typeof Users; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-t border-zinc-200 pt-7 dark:border-zinc-800">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4"><h2 className="section-title flex items-center gap-2"><Icon className="h-5 w-5 text-sky-600 dark:text-sky-400" />{title}</h2>{action}</div>
      {children}
    </section>
  );
}

function CardGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{children}</div>;
}

function BaseCard({ item, locale, actionLabel, onAction }: { item: BasePersona; locale: Locale; actionLabel: string; onAction: () => void }) {
  return (
    <article className="overflow-hidden rounded-md border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <img src={item.image} alt="" className="aspect-video w-full object-cover" />
      <div className="p-5">
        <h3 className="text-base font-semibold">{item.name[locale]}</h3>
        <p className="mt-2 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-slate-600 dark:text-zinc-400">{personaPreview(item.content[locale])}</p>
        <button type="button" className="secondary-button mt-4 w-full" onClick={onAction}>{actionLabel}</button>
      </div>
    </article>
  );
}

function CustomCard({ item, copy, editLabel, onEdit, onDelete }: { item: CustomCatalogItem; copy: Copy; editLabel: string; onEdit: () => void; onDelete: () => void }) {
  return (
    <article className="overflow-hidden rounded-md border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <CatalogImage source={item.imageDataUrl} />
      <div className="p-5">
        <div className="flex items-start justify-between gap-3"><h3 className="break-words text-base font-semibold">{item.name}</h3><span className="rounded bg-sky-100 px-2 py-1 text-[11px] font-semibold text-sky-700 dark:bg-sky-950 dark:text-sky-300">{copy.custom}</span></div>
        <p className="mt-2 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-slate-600 dark:text-zinc-400">{item.text}</p>
        <div className="mt-4 flex gap-2"><button type="button" className="secondary-button flex-1" onClick={onEdit}><Pencil className="h-4 w-4" /> {editLabel}</button><button type="button" className="icon-button text-red-600 dark:text-red-400" title={copy.deleteItem} onClick={onDelete}><Trash2 className="h-4 w-4" /></button></div>
      </div>
    </article>
  );
}

function BaseDetailModal({ item, locale, copy, onClose, onClone }: { kind: CatalogKind; item: BasePersona; locale: Locale; copy: Copy; onClose: () => void; onClone: () => void }) {
  return (
    <Modal title={item.name[locale]} closeLabel={copy.close} onClose={onClose} wide>
      <img src={item.image} alt="" className="aspect-video w-full rounded-md object-cover" />
      <section className="mt-5 border-t border-zinc-200 pt-5 dark:border-zinc-800">
        <h3 className="text-sm font-semibold">{copy.personaDetails}</h3>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700 dark:text-zinc-300">{item.content[locale]}</p>
      </section>
      <div className="mt-6 flex justify-end"><button type="button" className="primary-button" onClick={onClone}><Plus className="h-4 w-4" /> {copy.addToCustomPersona}</button></div>
    </Modal>
  );
}

function CustomItemModal({ kind, existing, state, copy, onClose, onSave }: { kind: CatalogKind; existing: CustomCatalogItem | null; state: AppState; copy: Copy; onClose: () => void; onSave: (item: CustomCatalogItem) => void }) {
  const [name, setName] = useState(existing?.name ?? "");
  const [text, setText] = useState(existing?.text ?? "");
  const [image, setImage] = useState<string | null>(existing?.imageDataUrl ?? null);
  const [error, setError] = useState("");
  const existingNames = state.customPersonas.map((item) => item.name);

  function chooseImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/") || file.size > 2 * 1024 * 1024) {
      setError(copy.imageTooLarge);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setImage(typeof reader.result === "string" ? reader.result : null);
    reader.readAsDataURL(file);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) { setError(copy.nameRequired); return; }
    if (!validateCustomName(name, existingNames, existing?.name)) { setError(copy.duplicateCustomName); return; }
    if (!text.trim()) { setError(copy.promptRequired); return; }
    const now = new Date().toISOString();
    onSave({ id: existing?.id ?? createId(kind), name: name.trim(), text: text.trim(), imageDataUrl: image, sourceBaseId: existing?.sourceBaseId ?? null, createdAt: existing?.createdAt ?? now, updatedAt: now });
  }

  return (
    <Modal title={existing ? copy.editCustomPersona : copy.createPersona} closeLabel={copy.close} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-5">
        <CatalogImage source={image} />
        <label className="secondary-button w-full cursor-pointer"><SquarePen className="h-4 w-4" /> {copy.chooseImage}<input type="file" accept="image/*" className="sr-only" onChange={chooseImage} /></label>
        <label className="block"><span className="mb-2 block text-sm font-medium">{copy.personaNameField}</span><input autoFocus className="form-input" placeholder={copy.personaNamePlaceholder} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label className="block"><span className="mb-2 block text-sm font-medium">{copy.promptText}</span><textarea className="form-input min-h-44 resize-y py-3 leading-6" placeholder={copy.personaTextPlaceholder} value={text} onChange={(event) => setText(event.target.value)} /></label>
        {error ? <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p> : null}
        <ModalActions copy={copy} onCancel={onClose} submitLabel={existing ? copy.save : copy.create} />
      </form>
    </Modal>
  );
}

function CatalogImage({ source }: { source: string | null }) {
  return source ? <img src={source} alt="" className="aspect-video w-full rounded-md bg-slate-100 object-cover dark:bg-zinc-800" /> : <div className="flex aspect-video w-full items-center justify-center rounded-md bg-slate-100 text-slate-400 dark:bg-zinc-800 dark:text-zinc-600"><Bot className="h-12 w-12" /></div>;
}

function SegmentedGender({ value, onChange, copy }: { value: "all" | Gender; onChange: (value: "all" | Gender) => void; copy: Copy }) {
  return (
    <div><span className="mb-2 block text-sm font-medium">{copy.gender}</span><div className="inline-flex rounded-md border border-zinc-200 bg-white p-1 dark:border-zinc-800 dark:bg-zinc-900">{(["all", "female", "male"] as const).map((item) => <button key={item} type="button" className={`min-h-9 rounded px-3 text-sm font-medium ${value === item ? "bg-sky-500 text-white" : "text-slate-600 dark:text-zinc-400"}`} onClick={() => onChange(item)}>{item === "all" ? copy.all : item === "female" ? copy.female : copy.male}</button>)}</div></div>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void }) {
  return <label className="block"><span className="mb-2 block text-sm font-medium">{label}</span><select className="form-input" value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>;
}

function EmptyState({ icon: Icon, title, description }: { icon: typeof Users; title: string; description?: string }) {
  return <div className="flex min-h-52 flex-col items-center justify-center rounded-md border border-dashed border-zinc-300 bg-white px-6 text-center dark:border-zinc-700 dark:bg-zinc-900"><span className="flex h-12 w-12 items-center justify-center rounded-md bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400"><Icon className="h-6 w-6" /></span><p className="mt-4 text-sm font-semibold">{title}</p>{description ? <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500 dark:text-zinc-500">{description}</p> : null}</div>;
}

function Modal({ title, closeLabel, onClose, wide, children }: { title: string; closeLabel: string; onClose: () => void; wide?: boolean; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-950/55 p-0 backdrop-blur-sm sm:items-center sm:p-5" role="dialog" aria-modal="true">
      <div className={`max-h-[92dvh] w-full overflow-y-auto rounded-t-md border border-zinc-200 bg-white shadow-2xl dark:border-zinc-800 dark:bg-zinc-900 sm:rounded-md ${wide ? "sm:max-w-2xl" : "sm:max-w-lg"}`}>
        <header className="sticky top-0 z-10 flex min-h-16 items-center justify-between gap-4 border-b border-zinc-200 bg-white px-5 dark:border-zinc-800 dark:bg-zinc-900"><h2 className="min-w-0 break-words text-base font-semibold">{title}</h2><button type="button" className="icon-button border-0" aria-label={closeLabel} title={closeLabel} onClick={onClose}><X className="h-5 w-5" /></button></header>
        <div className="p-5 sm:p-6">{children}</div>
      </div>
    </div>
  );
}

function ModalActions({ copy, onCancel, submitLabel }: { copy: Copy; onCancel: () => void; submitLabel: string }) {
  return <div className="flex flex-col-reverse gap-3 border-t border-zinc-200 pt-5 dark:border-zinc-800 sm:flex-row sm:justify-end"><button type="button" className="secondary-button" onClick={onCancel}>{copy.cancel}</button><button type="submit" className="primary-button">{submitLabel}</button></div>;
}

function ConfirmModal({ title, description, confirmLabel, danger, onCancel, onConfirm }: { title: string; description: string; confirmLabel: string; danger?: boolean; onCancel: () => void; onConfirm: () => void }) {
  const copy = getCopy(detectLocale(window.navigator.language));
  return <Modal title={title} closeLabel={copy.close} onClose={onCancel}><p className="text-sm leading-7 text-slate-600 dark:text-zinc-300">{description}</p><div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"><button type="button" className="secondary-button" onClick={onCancel}>{copy.cancel}</button><button type="button" className={danger ? "danger-button" : "primary-button"} onClick={onConfirm}>{confirmLabel}</button></div></Modal>;
}

function personaName(target: Target, state: AppState, locale: Locale): string {
  if (target.personaSource === "base") return cachedBasePersonas(state).find((persona) => persona.id === target.personaId)?.name[locale] ?? target.personaId;
  return state.customPersonas.find((persona) => persona.id === target.personaId)?.name ?? target.personaId;
}

function saveCustomItem(state: AppState, kind: CatalogKind, item: CustomCatalogItem): AppState {
  const key = "customPersonas";
  const list = state[key];
  const exists = list.some((entry) => entry.id === item.id);
  return { ...state, [key]: exists ? list.map((entry) => entry.id === item.id ? item : entry) : [...list, item] };
}

function safeFilename(value: string): string {
  return value.trim().replace(/[^\p{L}\p{N}._-]+/gu, "-").replace(/^-+|-+$/gu, "") || "sweety-target";
}

export default App;
