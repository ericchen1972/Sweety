import { describe, expect, it } from "vitest";

import { personaPreview } from "./personaPreview";

describe("personaPreview", () => {
  it("uses the canonical content and removes only its leading section label", () => {
    expect(personaPreview("人物資料：\n王筱蘭住在板橋。", 20)).toBe("王筱蘭住在板橋。");
    expect(personaPreview("Character information:\nWang lives in Banqiao.", 30)).toBe("Wang lives in Banqiao.");
  });

  it("appends three dots only when the normalized content is truncated", () => {
    expect(personaPreview("人物資料：\n這是一段超過限制的完整人設內容", 8)).toBe("這是一段超過限制...");
    expect(personaPreview("短內容", 8)).toBe("短內容");
  });
});
