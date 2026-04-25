
export interface DashboardOverviewResponse {
  riskDisclaimer: string;
  kpis: {
    watchlistCount: number;
    monitoringCount: number;
    watchlistTrendText: string;
    todaySignalCount: number;
    todayBuySignalCount: number;
    todaySellSignalCount: number;
    todayRiskBlockedCount: number;
    paperAccountNetAsset: number;
    monthReturnPct: number;
  };
  tasks: {
    riskBlockedToReview: number;
    staleDataOver24h: number;
    failedResearchReports: number;
    pausedMonitoringStocks: number;
  };
  quickResearchStats: {
    completedResearchCount: number;
    pendingTaskCount: number;
  };
  system: {
    status: string;
    tradeDay: boolean;
    market: string;
    currentTime: string;
  };
}

export interface ResearchStatsResponse {
  period: string;
  researchCount: number;
  watchlistConvertedCount: number;
  popularIndustries: string[];
}

export interface RiskSystemRuleResponse {
  rule: string;
  label: string;
  passed: boolean;
  description: string;
}

export interface RiskSystemStatusResponse {
  overallStatus: 'PASSED' | 'BLOCKED' | string;
  rules: RiskSystemRuleResponse[];
}

export interface ExecutionTraceStepResponse {
  step: string;
  label: string;
  status: string;
  relId: string | null;
}

export interface ExecutionTraceResponse {
  traceId: string;
  runId: string;
  monitoringItemId: string;
  code: string;
  symbol: string | null;
  currentStep: string;
  status: string;
  steps: ExecutionTraceStepResponse[];
  createdAt: string;
  updatedAt: string;
}

export interface PageResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  hasMore: boolean;
}

export interface SystemStatusResponse {
  status: string;
  mode: 'PAPER_TRADING_ONLY';
  tradeDay: boolean;
  market: string;
  currentTime: string;
  paperTrading: {
    active: boolean;
    pollingEnabled: boolean;
    lastRunId: string | null;
  };
}

export interface DataSourceHealthItem {
  name: string;
  status: 'HEALTHY' | 'WARNING' | 'ERROR' | string;
  latency: string;
  latencyMs: number;
  lastCheckedAt: string;
  lastError: string | null;
}

export interface ResearchTaskResponse {
  taskId: string;
  code: string;
  symbol: string;
  status: string;
  currentStep: string;
  progressPct: number;
  createdAt: string;
  updatedAt: string;
  reportId: string | null;
  redirectTo: string | null;
}

export interface ResearchRecordResponse {
  id: string;
  taskId: string;
  reportId: string | null;
  code: string;
  symbol: string;
  name: string;
  researchTime: string;
  status: string;
  updateTime: string;
}

export interface ResearchReportResponse {
  reportId: string;
  code: string;
  symbol: string;
  name: string;
  market: string;
  industry: string;
  generatedAt: string;
  researchBasePeriod: string;
  dataSources: string[];
  updateFrequency: string;
  quote: {
    price: number;
    change: number;
    changePercent: number;
    volume: number;
    amount: number;
    updateTime: string;
  };
  trend: Array<{ date: string; price: number }>;
  financialSnapshot: {
    revenue: string;
    profit: string;
    grossMargin: number;
    netMargin: number;
    roe: number;
    pe: number;
  };
  report: {
    overview: string;
    keyInsights: string[];
    worthFurtherResearch: boolean;
    aiConfidence: number;
    dataCompleteness: number;
    aiDisclaimer: string;
    risks: Array<{ title: string; description: string; severity: string }>;
    businessSegments: Array<{ name: string; percent: number }>;
    newsItems: Array<{ id: string; title: string; date: string; type: string; url: string | null }>;
  };
}

export interface WatchlistItemResponse {
  id: string;
  code: string;
  symbol: string;
  name: string;
  source: string;
  reportId: string | null;
  note: string | null;
  createdAt: string;
}

export interface SignalResponse {
  id: string;
  runId: string;
  traceId: string;
  code: string;
  type: string;
  reason: string;
  confidence: number;
  generatedAt: string;
}

export interface RiskCheckResponse {
  id: string;
  runId: string;
  traceId: string;
  signalId: string;
  time: string;
  code: string;
  signal: string;
  passed: boolean;
  status: string;
  reason: string;
  rule: string;
}

export interface OrderResponse {
  id: string;
  runId: string;
  traceId: string;
  signalId: string;
  riskCheckId: string;
  createTime: string;
  code: string;
  symbol: string;
  name: string;
  side: string;
  type: string;
  orderType: string;
  quantity: number;
  price: number;
  filledQuantity: number;
  avgPrice: number;
  status: string;
  rejectReason: string | null;
}

export interface MonitoringItemResponse {
  id: string;
  code: string;
  symbol: string;
  name: string;
  enabled: boolean;
  strategyId: string;
  strategyName: string;
  source: string;
  reportId: string | null;
  createdAt: string;
  updatedAt: string;
  latestSignal: SignalResponse | null;
  latestRiskCheck: RiskCheckResponse | null;
  latestOrder: OrderResponse | null;
}

export interface EngineResponse {
  active: boolean;
  mode: 'PAPER_TRADING_ONLY';
  pollingEnabled: boolean;
  pollingIntervalSec: number;
  lastRunId: string | null;
  updatedAt: string;
  message?: string;
}

export interface PaperTradingRunResponse {
  runId: string;
  status: string;
  trigger: string;
  summary: {
    scannedStockCount: number;
    generatedSignalCount: number;
    riskPassedCount: number;
    riskBlockedCount: number;
    createdPaperOrderCount: number;
    simulatedExecutionCount: number;
    durationMs: number;
  };
  traceIds: string[];
  startedAt: string;
  finishedAt: string;
}

export interface AccountSummaryResponse {
  accountId: string;
  currency: string;
  totalAssets: number;
  availableCash: number;
  positionMarketValue: number;
  todayPnl: number;
  todayPnlPct: number;
  positionRatio: number;
  updateTime: string;
}

export interface PositionResponse {
  id: string;
  accountId: string;
  code: string;
  symbol: string;
  name: string;
  quantity: number;
  available: number;
  costPrice: number;
  currentPrice: number;
  marketValue: number;
  realizedPnl: number;
  unrealizedPnl: number;
  profitProgress: number;
  lastRunId: string | null;
  lastTraceId: string | null;
  updateTime: string;
}

export interface LogResponse {
  id: string;
  time: string;
  level: string;
  module: string;
  code: string | null;
  event: string;
  detail: string;
  relId: string | null;
  runId: string | null;
  traceId: string | null;
}
