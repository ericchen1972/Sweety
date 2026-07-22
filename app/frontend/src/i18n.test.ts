import { describe, expect, it } from "vitest";
import { getCopy } from "./i18n";

describe("custom persona copy", () => {
  it("uses the requested Traditional Chinese labels and placeholders", () => {
    const copy = getCopy("zh-TW");

    expect(copy.personaDetails).toBe("人設內容");
    expect(copy.personaNameField).toBe("人設名稱");
    expect(copy.personaNamePlaceholder).toBe("ex. 猶豫不決的小會計");
    expect(copy.personaTextPlaceholder).toBe("請在這裡輸入人物的基本資訊，姓名、年齡、工作、個性、說話風格等");
    expect(copy.aboutSweety).toBe("關於 Sweety");
    expect(copy.aboutLoadError).toBe("無法載入關於 Sweety 的內容。");
    expect(copy.basePersonaEditHint).toBe("＊如果你希望能修改基礎人設，增加其他細節，請點擊「增加到自訂人設」後，在自訂人設頁面進行修改");
  });
});
