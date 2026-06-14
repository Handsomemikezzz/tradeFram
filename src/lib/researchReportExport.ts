import { formatDateTime } from '@/services/api';
import type { ResearchReportResponse } from '@/services/api';
import { listTradingAgentsSections, TRADING_AGENTS_SECTION_LABELS } from '@/lib/tradingAgentsSections';

const section = (title: string, body: string[]) => [`## ${title}`, '', ...body, ''];

export function buildResearchReportMarkdown(report: ResearchReportResponse): string {
  const lines: string[] = [
    `# ${report.name}（${report.code}）研究报告`,
    '',
    `- Symbol: ${report.symbol}`,
    `- 生成时间: ${formatDateTime(report.generatedAt)}`,
    `- 研究基期: ${report.researchBasePeriod}`,
    `- 数据源: ${report.dataSources.join(' / ') || '-'}`,
    '',
  ];

  lines.push(
    ...section('当前行情', [
      `- 价格: ${report.quote.price.toFixed(2)}`,
      `- 涨跌: ${report.quote.change >= 0 ? '+' : ''}${report.quote.change.toFixed(2)} (${report.quote.changePercent >= 0 ? '+' : ''}${report.quote.changePercent.toFixed(2)}%)`,
      `- 成交量: ${(report.quote.volume / 10000).toFixed(2)} 万`,
      `- 成交额: ${(report.quote.amount / 100000000).toFixed(2)} 亿`,
    ]),
  );

  if (report.tradingAgentsDecision) {
    const decision = report.tradingAgentsDecision;
    lines.push(
      ...section('TradingAgents Decision', [
        `- Rating: ${decision.rating}`,
        `- Price Target: ${decision.priceTarget || '-'}`,
        `- Time Horizon: ${decision.timeHorizon || '-'}`,
        `- Yahoo Ticker: ${decision.yahooTicker}`,
        '',
        '### Executive Summary',
        '',
        decision.executiveSummary || '-',
        '',
        '### Investment Thesis',
        '',
        decision.investmentThesis || '暂无完整投资论点。',
      ]),
    );
  }

  lines.push(
    ...section('AI 核心结论', [
      report.report.overview,
      '',
      '### Key Insights',
      '',
      ...report.report.keyInsights.map((item) => `- ${item}`),
      '',
      `- 值得继续研究: ${report.report.worthFurtherResearch ? '是' : '否'}`,
      `- AI 置信度: ${report.report.aiConfidence === null ? '暂无' : `${Math.round(report.report.aiConfidence * 100)}%`}`,
      `- 数据完整度: ${Math.round(report.report.dataCompleteness * 100)}%`,
      '',
      `> ${report.report.aiDisclaimer}`,
    ]),
  );

  if (report.report.risks.length > 0) {
    lines.push(
      ...section('风险提示', report.report.risks.flatMap((risk) => [
        `### ${risk.title}`,
        '',
        risk.description,
        '',
      ])),
    );
  }

  const agentSections = listTradingAgentsSections(report.tradingAgentsSections);

  if (agentSections.length > 0) {
    lines.push('## TradingAgents 引擎全文', '');
    for (const item of agentSections) {
      lines.push(`### ${item.label}`, '', item.content, '');
    }
  }

  lines.push(
    '---',
    '',
    `- Provider: ${report.dataMeta.provider}`,
    `- 数据更新时间: ${formatDateTime(report.dataUpdatedAt)}`,
    `- 缓存: ${report.dataMeta.usedCache ? (report.dataMeta.dataStale ? '使用过期缓存' : '命中缓存') : '实时刷新'}`,
  );

  return lines.join('\n').trimEnd() + '\n';
}

export async function copyResearchReportMarkdown(report: ResearchReportResponse): Promise<void> {
  const text = buildResearchReportMarkdown(report);
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

export function downloadResearchReportMarkdown(report: ResearchReportResponse): void {
  const content = buildResearchReportMarkdown(report);
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  const datePart = report.generatedAt.slice(0, 10);
  anchor.href = url;
  anchor.download = `${report.code}_${report.name}_research_${datePart}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

// Keep export for tests or external use
export { TRADING_AGENTS_SECTION_LABELS };
