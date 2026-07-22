import { describe, expect, it } from "vitest";

import { basePersonas } from "./catalog";

describe("bundled persona catalog contract", () => {
  it("uses one localized content field without duplicate editorial fields", () => {
    expect(basePersonas.length).toBeGreaterThan(0);
    for (const persona of basePersonas) {
      expect(persona.content["zh-TW"].trim()).not.toBe("");
      expect(persona.content.en.trim()).not.toBe("");
      expect(persona).not.toHaveProperty("summary");
      expect(persona).not.toHaveProperty("profile");
      expect(persona).not.toHaveProperty("style");
      expect(persona).not.toHaveProperty("text");
    }
  });

  it("contains six detailed personas in every age group with balanced gender", () => {
    expect(basePersonas).toHaveLength(24);
    for (const ageGroup of ["20-35", "35-50", "50-65", "65+"] as const) {
      const group = basePersonas.filter((persona) => persona.ageGroup === ageGroup);
      expect(group).toHaveLength(6);
      expect(group.filter((persona) => persona.gender === "female")).toHaveLength(3);
      expect(group.filter((persona) => persona.gender === "male")).toHaveLength(3);
    }
    for (const persona of basePersonas) {
      expect(Array.from(persona.content["zh-TW"]).length).toBeGreaterThanOrEqual(180);
      expect(persona.content.en.length).toBeGreaterThanOrEqual(300);
    }
  });

  it("keeps the approved Wang Xiaolan details and Taiwanese expressions", () => {
    const persona = basePersonas.find((item) => item.id === "cautious-accounting-assistant");
    expect(persona?.content["zh-TW"]).toContain("與母親妹妹居住在新北市板橋");
    expect(persona?.content["zh-TW"]).toContain("70萬");
    expect(persona?.content["zh-TW"]).toContain("你不是詐騙吧？我朋友被騙過，好可怕..");
    expect(persona?.content["zh-TW"]).toContain("你幹嘛啦～");
    expect(persona?.content["zh-TW"]).toContain("好窩");
    expect(persona?.content["zh-TW"]).toContain("母湯啦");
  });
});
