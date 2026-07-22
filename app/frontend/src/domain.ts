export type Locale = "zh-TW" | "en";
export type Gender = "female" | "male";
export type AgeGroup = "20-35" | "35-50" | "50-65" | "65+";
export type CatalogSource = "base" | "custom";
export type TargetStatus = "active" | "ended";

export interface BasePersona {
  id: string;
  ageGroup: AgeGroup;
  gender: Gender;
  name: Record<Locale, string>;
  content: Record<Locale, string>;
  image: string;
}

export interface Target {
  id: string;
  name: string;
  ageGroup: AgeGroup;
  gender: Gender;
  personaId: string;
  personaSource: CatalogSource;
  weaponId: string;
  weaponSource: CatalogSource;
  replyEnabled: boolean;
  status: TargetStatus;
  roundTrips: number;
  firstReplyAt: string | null;
  lastReplyAt: string | null;
  endedAt?: string | null;
}

export interface CustomCatalogItem {
  id: string;
  name: string;
  text: string;
  imageDataUrl: string | null;
  sourceBaseId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AppSettings {
  aiProvider: "sweety" | "openai";
  openAiApiKey: string;
  openAiModel: string;
  checkIntervalSeconds: number;
  replyDelayMinSeconds: number;
  replyDelayMaxSeconds: number;
}

export interface AppState {
  version: 1;
  monitoringEnabled: boolean;
  settings: AppSettings;
  basePersonas: BasePersona[];
  targets: Target[];
  customPersonas: CustomCatalogItem[];
  customWeapons: CustomCatalogItem[];
}

export function detectLocale(language: string | null | undefined): Locale {
  return language?.toLowerCase() === "zh-tw" ? "zh-TW" : "en";
}

export function validateTargetName(name: string): boolean {
  return name.trim().length > 0;
}

export function validateReplyDelay(minimum: number, maximum: number): boolean {
  return Number.isFinite(minimum) && Number.isFinite(maximum) && minimum >= 0 && maximum >= minimum;
}

export function normalizeCatalogName(name: string): string {
  return name.trim().replace(/\s+/gu, " ").toLocaleLowerCase();
}

export function validateCustomName(name: string, existingCustomNames: string[], currentName?: string): boolean {
  const normalized = normalizeCatalogName(name);
  if (!normalized) {
    return false;
  }

  const current = currentName ? normalizeCatalogName(currentName) : null;
  return !existingCustomNames.some((existing) => {
    const candidate = normalizeCatalogName(existing);
    return candidate === normalized && candidate !== current;
  });
}

export function reviveTarget(target: Target): Target {
  return {
    ...target,
    status: "active",
    replyEnabled: false,
    endedAt: null,
  };
}

export function endTarget(target: Target, endedAt = new Date().toISOString()): Target {
  return {
    ...target,
    status: "ended",
    replyEnabled: false,
    endedAt,
  };
}

export function targetDurationMs(target: Target): number {
  if (!target.firstReplyAt || !target.lastReplyAt) {
    return 0;
  }
  return Math.max(0, Date.parse(target.lastReplyAt) - Date.parse(target.firstReplyAt));
}

export function aggregateDurationMs(targets: Target[]): number {
  return targets.reduce((sum, target) => sum + targetDurationMs(target), 0);
}

export function canDeleteCustomPersona(itemId: string, targets: Target[]): boolean {
  return !targets.some((target) => {
    return target.personaSource === "custom" && target.personaId === itemId;
  });
}

export function formatDuration(milliseconds: number, locale: Locale): string {
  const totalMinutes = Math.floor(milliseconds / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (locale === "zh-TW") {
    return hours > 0 ? `${hours} 小時 ${minutes} 分` : `${minutes} 分鐘`;
  }
  return hours > 0 ? `${hours} hr ${minutes} min` : `${minutes} min`;
}

export function formatDurationHours(milliseconds: number, locale: Locale): string {
  const hours = Math.round((milliseconds / 3_600_000) * 10) / 10;
  return locale === "zh-TW" ? `${hours} 小時` : `${hours} hr`;
}

export function formatPersonaStyle(value: string, locale: Locale): string {
  const trimmed = value.trim();
  if (!trimmed.startsWith("{")) {
    return value;
  }

  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>;
    const reactions = Array.isArray(parsed.natural_reactions)
      ? parsed.natural_reactions.filter((item): item is string => typeof item === "string")
      : [];
    const sentenceLength = parsed.sentence_length === "very_short"
      ? (locale === "zh-TW" ? "很短的句子" : "very short messages")
      : (locale === "zh-TW" ? "短句" : "short messages");
    const emoji = parsed.emoji_frequency === "none" || parsed.emoji_frequency === "rare"
      ? (locale === "zh-TW" ? "很少使用表情符號" : "rarely uses emoji")
      : (locale === "zh-TW" ? "偶爾使用表情符號" : "occasionally uses emoji");
    const reactionText = reactions.length
      ? (locale === "zh-TW" ? `常見反應：${reactions.join("、")}。` : `Typical reactions: ${reactions.join(", ")}.`)
      : "";
    return locale === "zh-TW"
      ? `說話自然，通常使用${sentenceLength}，${emoji}。${reactionText}`
      : `Speaks naturally in ${sentenceLength} and ${emoji}. ${reactionText}`.trim();
  } catch {
    return value;
  }
}

export function createId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}
