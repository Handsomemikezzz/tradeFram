import type { ResearchReportResponse } from '@/services/api';

/** TradingAgents pipeline order — single source for report page and export */
export const TRADING_AGENTS_SECTION_LABELS: Array<
  [keyof NonNullable<ResearchReportResponse['tradingAgentsSections']>, string]
> = [
  ['pastContext', 'Memory Context'],
  ['instrumentContext', 'Instrument Context'],
  ['market', 'Market Analyst'],
  ['sentiment', 'Sentiment Analyst'],
  ['news', 'News Analyst'],
  ['fundamentals', 'Fundamentals Analyst'],
  ['investmentDebate', 'Bull / Bear Debate'],
  ['researchTeam', 'Research Team Plan'],
  ['trader', 'Trader Plan'],
  ['riskDebate', 'Risk Management Debate'],
  ['portfolioManager', 'Portfolio Manager Decision'],
];

export function listTradingAgentsSections(
  sections: ResearchReportResponse['tradingAgentsSections'] | undefined,
) {
  return TRADING_AGENTS_SECTION_LABELS.map(([key, label]) => ({
    key,
    label,
    content: sections?.[key]?.trim() || '',
  })).filter((section) => section.content.length > 0);
}
