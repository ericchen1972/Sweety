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
    expect(copy.targetNameWarning).toBe(
      "名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。 名稱不可包含特殊字元與表情符號，必須使用英文字母或數字，否則 Sweety 將無法正確辨識。\n範例：Fraud1, Fraud2....",
    );
    expect(copy.targetNameError).toBe("名稱只能使用英文字母或數字。");
  });

  it("provides complete natural Japanese copy", () => {
    const japanese = getCopy("ja");
    const english = getCopy("en");

    expect(Object.keys(japanese).sort()).toEqual(Object.keys(english).sort());
    expect(japanese.dashboard).toBe("ダッシュボード");
    expect(japanese.targets).toBe("詐欺アカウント一覧");
    expect(japanese.addTarget).toBe("対象を追加");
    expect(japanese.save).toBe("設定を保存");
    expect(japanese.aboutSweety).toBe("Sweetyについて");
    expect(japanese.updateAvailable).toBe("新しいバージョンをダウンロードできます");
  });
});
