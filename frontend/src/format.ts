import type { RecordSummary } from "./types";

export const formatNumber = (value: number) => new Intl.NumberFormat("en-US").format(value);

export const formatRecord = (record: RecordSummary, showTies: boolean) =>
  [record.wins, record.losses, ...(showTies ? [record.ties] : [])].map(formatNumber).join(" - ");

export const formatPercent = (value: number | null | undefined, digits = 1) =>
  value == null ? "—" : `${(value * 100).toFixed(digits)}%`;

export const pluralize = (value: number, singular: string, plural = `${singular}s`) =>
  `${formatNumber(value)} ${value === 1 ? singular : plural}`;
