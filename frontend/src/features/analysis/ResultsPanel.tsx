import { formatNumber, formatPercent, formatRecord } from "../../format";
import type { AnalysisResult } from "../../types";

interface Props {
  result: AnalysisResult | null;
  busy: boolean;
  showTies: boolean;
  empty: boolean;
}

export function ResultsPanel({ result, busy, showTies, empty }: Props) {
  const record = result?.record;
  return (
    <section className="panel results" aria-live="polite" aria-busy={busy}>
      <div className="panel-header"><h2>Results</h2></div>
      {empty ? <p className="result-empty">Add a Pokémon or exclusion to calculate a win rate.</p> : <div className="result-summary">
        <div className="result-primary"><span>Win rate</span><strong>{formatPercent(result?.metrics.decisive_win_rate)}</strong></div>
        <div className="result-row"><span>Record</span><strong>{record ? formatRecord(record, showTies) : "—"}</strong></div>
        <div className="result-row"><span>Matches</span><strong>{result ? formatNumber(result.sample.matches - (showTies ? 0 : (result.sample.tie_matches ?? result.record.ties))) : "—"}</strong></div>
      </div>}
    </section>
  );
}
