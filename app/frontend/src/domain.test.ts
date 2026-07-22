import {
  aggregateDurationMs,
  canDeleteCustomPersona,
  detectLocale,
  formatPersonaStyle,
  formatDurationHours,
  reviveTarget,
  validateCustomName,
  validateReplyDelay,
  validateTargetName,
  type Target,
} from "./domain";
import { describe, expect, it } from "vitest";

const target: Target = {
  id: "target-1",
  name: "LINE 完整名稱",
  ageGroup: "20-35",
  gender: "female",
  personaId: "persona-1",
  personaSource: "base",
  weaponId: "weapon-1",
  weaponSource: "base",
  replyEnabled: true,
  status: "active",
  roundTrips: 3,
  firstReplyAt: "2026-07-21T08:00:00.000Z",
  lastReplyAt: "2026-07-21T10:00:00.000Z",
};

describe("detectLocale", () => {
  it("uses Traditional Chinese only for zh-TW", () => {
    expect(detectLocale("zh-TW")).toBe("zh-TW");
    expect(detectLocale("zh-tw")).toBe("zh-TW");
    expect(detectLocale("zh-HK")).toBe("en");
    expect(detectLocale("zh-CN")).toBe("en");
    expect(detectLocale("ja-JP")).toBe("en");
  });
});

describe("target validation", () => {
  it("requires the exact non-empty LINE name", () => {
    expect(validateTargetName("  ")).toBe(false);
    expect(validateTargetName("王小明✨")).toBe(true);
  });

  it("requires a valid reply delay range", () => {
    expect(validateReplyDelay(15, 45)).toBe(true);
    expect(validateReplyDelay(45, 15)).toBe(false);
    expect(validateReplyDelay(-1, 10)).toBe(false);
  });
});

describe("target lifecycle and metrics", () => {
  it("revives ended targets without clearing persona, weapon, or metrics", () => {
    const revived = reviveTarget({ ...target, status: "ended", replyEnabled: true });
    expect(revived.status).toBe("active");
    expect(revived.replyEnabled).toBe(false);
    expect(revived.personaId).toBe(target.personaId);
    expect(revived.firstReplyAt).toBe(target.firstReplyAt);
  });

  it("sums the first-to-last successful reply duration per target", () => {
    const second = {
      ...target,
      id: "target-2",
      firstReplyAt: "2026-07-21T08:00:00.000Z",
      lastReplyAt: "2026-07-21T09:00:00.000Z",
    };
    expect(aggregateDurationMs([target, second])).toBe(3 * 60 * 60 * 1000);
  });

  it("formats the dashboard total in hours", () => {
    expect(formatDurationHours(0, "zh-TW")).toBe("0 小時");
    expect(formatDurationHours(90 * 60 * 1000, "zh-TW")).toBe("1.5 小時");
    expect(formatDurationHours(3 * 60 * 60 * 1000, "en")).toBe("3 hr");
  });
});

describe("custom catalog rules", () => {
  it("allows a base-name collision but rejects a custom-name collision", () => {
    expect(validateCustomName("謹慎的會計助理", ["我的人設"])).toBe(true);
    expect(validateCustomName(" 我的 人設 ", ["我的 人設"])).toBe(false);
  });

  it("blocks persona deletion while active or ended targets reference the item", () => {
    const customTarget = { ...target, personaSource: "custom" as const };
    expect(canDeleteCustomPersona("persona-1", [customTarget])).toBe(false);
    expect(canDeleteCustomPersona("persona-2", [customTarget])).toBe(true);
    expect(canDeleteCustomPersona("persona-1", [{ ...customTarget, status: "ended" }])).toBe(false);
  });
});

describe("persona style display", () => {
  it("turns legacy JSON into readable Traditional Chinese", () => {
    const legacy = JSON.stringify({
      initiative: "medium_low",
      warmth: "warm_practical",
      sentence_length: "short",
      emoji_frequency: "occasional",
      natural_reactions: ["有客人先離開", "忙完回來問上一句"],
    });

    const formatted = formatPersonaStyle(legacy, "zh-TW");

    expect(formatted).not.toContain("{");
    expect(formatted).toContain("短句");
    expect(formatted).toContain("有客人先離開");
  });

  it("keeps natural-language style text unchanged", () => {
    const style = "說話親切而務實，通常使用短句。";
    expect(formatPersonaStyle(style, "zh-TW")).toBe(style);
  });
});
