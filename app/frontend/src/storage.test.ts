import { describe, expect, it } from "vitest";

import { normalizeLoadedState } from "./storage";

describe("loaded state compatibility", () => {
  it("maps legacy localized persona text to canonical content", () => {
    const state = normalizeLoadedState({
      version: 1,
      monitoringEnabled: false,
      settings: {
        aiProvider: "sweety",
        openAiApiKey: "",
        openAiModel: "gpt-5.5",
        checkIntervalSeconds: 10,
        replyDelayMinSeconds: 15,
        replyDelayMaxSeconds: 45,
      },
      basePersonas: [{
        id: "legacy-persona",
        ageGroup: "20-35",
        gender: "female",
        name: { "zh-TW": "舊版人設", en: "Legacy Persona" },
        text: { "zh-TW": "舊版中文內容", en: "Legacy English content" },
        image: "data:image/png;base64,abc",
      }],
      targets: [],
      customPersonas: [],
      customWeapons: [],
    });

    expect(state.basePersonas[0].content).toEqual({
      "zh-TW": "舊版中文內容",
      en: "Legacy English content",
    });
  });
});
