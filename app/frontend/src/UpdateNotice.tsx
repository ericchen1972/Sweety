import { Download } from "lucide-react";
import type { UpdateStatus } from "./api";
import type { Copy } from "./i18n";

export type { UpdateStatus } from "./api";

type Schedule = (callback: () => void, delay: number) => number;
type ClearSchedule = (timer: number) => void;

export function startUpdateStatusPolling(
  load: () => Promise<UpdateStatus>,
  onStatus: (status: UpdateStatus) => void,
  schedule: Schedule = (callback, delay) => window.setTimeout(callback, delay),
  clearSchedule: ClearSchedule = (timer) => window.clearTimeout(timer),
) {
  let active = true;
  let timer: number | undefined;

  const readUpdate = async () => {
    let complete = false;
    try {
      const result = await load();
      if (!active) return;
      onStatus(result);
      complete = result.checked;
    } catch {
      // A transient update-status failure must not block the dashboard.
    }

    if (active && !complete) {
      timer = schedule(() => { void readUpdate(); }, 500);
    }
  };

  void readUpdate();
  return () => {
    active = false;
    if (timer !== undefined) clearSchedule(timer);
  };
}

export function availableDownloads(update: UpdateStatus) {
  if (!update.checked || !update.updateAvailable || !update.downloads) return [];
  return (["windows", "macos"] as const).flatMap((platform) => {
    const url = update.downloads?.[platform];
    return url ? [{ platform, url }] : [];
  });
}

export function UpdateNotice({ update, copy }: { update: UpdateStatus; copy: Copy }) {
  const downloads = availableDownloads(update);
  if (!update.checked || !update.updateAvailable || !update.latestVersion || downloads.length === 0) return null;

  return (
    <section
      className="rounded-xl border border-sky-700/40 bg-gradient-to-br from-sky-950 to-zinc-950 p-5 text-white shadow-lg shadow-sky-950/20 sm:p-6"
      aria-label={copy.updateAvailable}
    >
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div>
          <h2 className="text-xl font-semibold">{copy.updateHeading.replace("{version}", update.latestVersion)}</h2>
          <p className="mt-2 text-sm leading-6 text-sky-100">
            {copy.updateMacPrefix}<strong className="font-bold text-white">{copy.updateMacEmphasis}</strong>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {downloads.map(({ platform, url }) => (
            <a
              key={platform}
              href={url}
              target="_blank"
              rel="noreferrer noopener"
              className="primary-button whitespace-nowrap"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              {platform === "windows" ? copy.updateWindows : copy.updateMacOS}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
