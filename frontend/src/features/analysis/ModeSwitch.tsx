type Mode = "basic" | "versus";

interface Props {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onSwap: () => void;
}

export function ModeSwitch({ mode, onModeChange, onSwap }: Props) {
  return (
    <div className="view-actions" data-testid="analysis-actions">
      <button id="swap-teams" className={mode === "versus" ? "" : "is-placeholder"} type="button" disabled={mode !== "versus"} aria-hidden={mode !== "versus"} aria-label="Swap your team and the opponent team" onClick={onSwap}><span aria-hidden="true">⇄</span> Swap teams</button>
      <div className="mode-switch" aria-label="Analysis mode">
        <button type="button" aria-pressed={mode === "basic"} onClick={() => onModeChange("basic")}>Basic</button>
        <button type="button" aria-pressed={mode === "versus"} onClick={() => onModeChange("versus")}>Versus</button>
      </div>
    </div>
  );
}
