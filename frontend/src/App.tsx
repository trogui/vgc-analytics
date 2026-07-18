import { AnalysisPage } from "./features/analysis/AnalysisPage";
import { TeamsPage } from "./features/teams/TeamsPage";

export function App() {
  return window.location.pathname === "/teams" ? <TeamsPage /> : <AnalysisPage />;
}
