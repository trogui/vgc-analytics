import { useStoredState } from "./useStoredState";

export interface AppSettings {
  minPlayers: number;
  showTies: boolean;
}

const initialSettings: AppSettings = { minPlayers: 1, showTies: true };

export function useSettings() {
  return useStoredState("vgc-analytics-settings-v1", initialSettings);
}
