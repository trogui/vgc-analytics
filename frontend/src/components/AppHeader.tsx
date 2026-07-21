import { useState, type ReactNode } from "react";

import type { AppSettings } from "../hooks/useSettings";
import { useStoredState } from "../hooks/useStoredState";
import { Modal } from "./Modal";

interface Props {
  active: "analysis" | "teams";
  status: string;
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  filters?: ReactNode;
  refreshing?: boolean;
  onRefresh?: () => void;
}

export function AppHeader({
  active,
  status,
  settings,
  onSettingsChange,
  filters,
  refreshing = false,
  onRefresh,
}: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [dataNoticeDismissed, setDataNoticeDismissed] = useStoredState("vgc-analytics-data-notice-dismissed-v1", false);

  return (
    <>
      <header className="app-bar">
        <strong>VGC M-B Analytics</strong>
        <nav className="app-nav" aria-label="Main navigation">
          <a className={active === "analysis" ? "active" : ""} href="/" aria-current={active === "analysis" ? "page" : undefined}>Win rates</a>
          <a className={active === "teams" ? "active" : ""} href="/teams" aria-current={active === "teams" ? "page" : undefined}>Find teams</a>
        </nav>
        <div className="dataset-actions">
          <span>{status}</span>
          <button type="button" onClick={() => setSettingsOpen(true)}>Settings</button>
          {onRefresh && <button type="button" disabled={refreshing} onClick={onRefresh}>{refreshing ? "Refreshing…" : "Refresh"}</button>}
        </div>
      </header>
      {!dataNoticeDismissed && <aside className="source-data-notice" aria-label="Data and privacy notice">
        <span>Uses public Play Limitless tournament data. Player names, countries, and source account IDs are not stored or displayed.</span>
        <button type="button" aria-label="Dismiss data and privacy notice" onClick={() => setDataNoticeDismissed(true)}>Dismiss</button>
      </aside>}
      <Modal id="settings-dialog" open={settingsOpen} onClose={() => setSettingsOpen(false)}>
        <div className="picker-header">
          <h2>Settings</h2>
          <button type="button" aria-label="Close settings" onClick={() => setSettingsOpen(false)}>×</button>
        </div>
        <div className="settings-body">
          <details className="data-notice-details">
            <summary>Data and privacy information</summary>
            <p>Uses public Play Limitless tournament data. Player names, countries, and source account IDs are not stored or displayed. Tournament, team-list, and match-result data remain traceable to public source events.</p>
          </details>
          <label className="settings-field">
            <span>Minimum tournament players</span>
            <input
              type="number"
              name="min-players"
              min="1"
              value={settings.minPlayers}
              onChange={(event) => onSettingsChange({ ...settings, minPlayers: Math.max(1, Number(event.target.value) || 1) })}
            />
          </label>
          <label className="settings-check">
            <input
              type="checkbox"
              name="show-ties"
              checked={settings.showTies}
              onChange={(event) => onSettingsChange({ ...settings, showTies: event.target.checked })}
            />
            <span>Show ties in records</span>
          </label>
          {filters}
        </div>
      </Modal>
    </>
  );
}
