import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { getCopy } from "./i18n";
import { UpdateNotice, availableDownloads, startUpdateStatusPolling, type UpdateStatus } from "./UpdateNotice";

describe("availableDownloads", () => {
  it("uses Win then Mac order and omits missing platforms", () => {
    const update: UpdateStatus = {
      checked: true,
      updateAvailable: true,
      latestVersion: "1.1.0",
      downloads: { macos: "https://sweety.tw/Sweety.dmg" },
    };

    expect(availableDownloads(update)).toEqual([
      { platform: "macos", url: "https://sweety.tw/Sweety.dmg" },
    ]);
  });

  it("returns no buttons unless a checked update is available", () => {
    expect(availableDownloads({ checked: false, updateAvailable: false })).toEqual([]);
    expect(availableDownloads({ checked: true, updateAvailable: false })).toEqual([]);
  });
});

describe("UpdateNotice", () => {
  const available: UpdateStatus = {
    checked: true,
    updateAvailable: true,
    latestVersion: "1.2.0",
    downloads: {
      windows: "https://sweety.tw/Sweety.exe",
      macos: "https://sweety.tw/Sweety.dmg",
    },
  };

  it("renders exact Traditional Chinese copy and safe download links", () => {
    const html = renderToStaticMarkup(createElement(UpdateNotice, { update: available, copy: getCopy("zh-TW") }));

    expect(html).toContain("新版 1.2.0，立即下載");
    expect(html).toContain("＊Mac OS 版安裝後請重新設定，輔助使用、");
    expect(html).toContain("<strong");
    expect(html).toContain("螢幕與系統錄音以及自動化等三種權限");
    expect(html).toContain("Win 版");
    expect(html).toContain("Mac OS 版");
    expect(html.match(/target="_blank"/g)).toHaveLength(2);
    expect(html.match(/rel="noreferrer noopener"/g)).toHaveLength(2);
    expect(html).not.toContain("dismiss");
  });

  it("renders English copy and omits a missing platform", () => {
    const html = renderToStaticMarkup(createElement(UpdateNotice, {
      update: { ...available, downloads: { macos: available.downloads?.macos } },
      copy: getCopy("en"),
    }));

    expect(html).toContain("Version 1.2.0 is ready to download");
    expect(html).toContain("Mac OS");
    expect(html).not.toContain("Windows");
  });

  it("does not render before a checked update with a usable download", () => {
    expect(renderToStaticMarkup(createElement(UpdateNotice, {
      update: { checked: false, updateAvailable: false },
      copy: getCopy("zh-TW"),
    }))).toBe("");
    expect(renderToStaticMarkup(createElement(UpdateNotice, {
      update: { checked: true, updateAvailable: true, latestVersion: "1.2.0", downloads: {} },
      copy: getCopy("zh-TW"),
    }))).toBe("");
  });
});

describe("startUpdateStatusPolling", () => {
  it("retries a transient failure and stops after a checked result", async () => {
    const checked: UpdateStatus = { checked: true, updateAvailable: false };
    const load = vi.fn()
      .mockRejectedValueOnce(new Error("local API restarting"))
      .mockResolvedValueOnce(checked);
    const onStatus = vi.fn();
    let scheduled: (() => void) | undefined;
    const schedule = vi.fn((callback: () => void, delay: number) => {
      scheduled = callback;
      return delay;
    });

    const stop = startUpdateStatusPolling(load, onStatus, schedule, vi.fn());
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(schedule).toHaveBeenCalledWith(expect.any(Function), 500);
    scheduled?.();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(load).toHaveBeenCalledTimes(2);
    expect(onStatus).toHaveBeenCalledWith(checked);
    expect(schedule).toHaveBeenCalledTimes(1);
    stop();
  });
});
