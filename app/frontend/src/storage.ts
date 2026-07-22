import type { AppState, BasePersona } from "./domain";
import { api } from "./api";
import { basePersonas } from "./catalog";

export const defaultState: AppState = {
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
  basePersonas,
  targets: [],
  customPersonas: [],
  customWeapons: [],
};

export async function loadState(): Promise<AppState> {
  return normalizeLoadedState(await api.loadState());
}

type WireBasePersona = Omit<BasePersona, "content"> & {
  content?: BasePersona["content"];
  text?: BasePersona["content"];
};

export function normalizeLoadedState(value: unknown): AppState {
  const state = value as Omit<AppState, "basePersonas"> & { basePersonas?: WireBasePersona[] };
  const personas = Array.isArray(state.basePersonas) ? state.basePersonas : [];

  return {
    ...state,
    basePersonas: personas.map(({ text, ...persona }) => ({
      ...persona,
      content: persona.content ?? text ?? basePersonas.find((item) => item.id === persona.id)?.content ?? { "zh-TW": "", en: "" },
    })),
  } as AppState;
}

let saveQueue: Promise<AppState | undefined> = Promise.resolve(undefined);

export function saveState(state: AppState): Promise<AppState> {
  const snapshot = structuredClone(state);
  const operation = saveQueue.catch(() => undefined).then(() => api.saveState(snapshot));
  saveQueue = operation;
  return operation;
}
