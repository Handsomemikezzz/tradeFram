
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
  tradingTimeMode: {
    allowManualRunOutsideTradingTime: boolean;
    strictTradingTimeCheck: boolean;
  };
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

export interface StockDataStatusResponse {
  provider: string;
  code: string;
  symbol: string;
  lastFetchedAt: string | null;
  latestTradeDate: string | null;
  priceBarCount: number;
  financialSnapshotAvailable: boolean;
  cacheHit: boolean;
  dataStale: boolean;
  dataCompleteness: number;
  lastError: string | null;
}

export interface StockDataRefreshResponse {
  code: string;
  symbol: string;
  provider: string;
  priceBarCount: number;
  dataUpdatedAt: string | null;
  dataCompleteness: number;
  usedCache: boolean;
  dataStale: boolean;
  refreshError: string | null;
}

export interface ResearchTaskResponse {
  taskId: string;
  code: string;
  symbol: string;
  status: string;
  currentStep: string;
  progressPct: number;
  errorMessage: string | null;
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
  dataUpdatedAt: string;
  dataMeta: {
    provider: string;
    usedCache: boolean;
    dataStale: boolean;
    dataCompleteness: number;
    lastError: string | null;
  };
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
  } | null;
  tradingAgentsDecision: {
    rating: string;
    executiveSummary: string;
    investmentThesis: string;
    priceTarget: string;
    timeHorizon: string;
    yahooTicker: string;
  } | null;
  tradingAgentsSections: {
    market?: string;
    sentiment?: string;
    news?: string;
    fundamentals?: string;
    researchTeam?: string;
    trader?: string;
    portfolioManager?: string;
  };
  report: {
    overview: string;
    keyInsights: string[];
    worthFurtherResearch: boolean;
    aiConfidence: number | null;
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
  rawPrice: number;
  executedPrice: number;
  slippageAmount: number;
  commission: number;
  stampTax: number;
  totalFee: number;
  estimatedAmount: number;
  finalAmount: number;
  netAmount: number;
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
  strategyParams: Record<string, unknown>;
  riskParams: Record<string, unknown>;
  source: string;
  reportId: string | null;
  createdAt: string;
  updatedAt: string;
  latestSignal: SignalResponse | null;
  latestRiskCheck: RiskCheckResponse | null;
  latestOrder: OrderResponse | null;
}

export interface LimitUpBreakItemResponse {
  id: string;
  code: string;
  name: string;
  previousLimitUpHeight: number;
  changePercent: number | null;
  amount: number | null;
  intradayBreak: boolean | null;
  breakType: 'CLOSE_NOT_LIMIT_UP' | 'SUSPENDED' | string;
}

export interface LimitUpBreakSnapshotResponse {
  id: string;
  tradeDate: string;
  previousTradeDate: string | null;
  threshold: number;
  provider: string;
  priceAdjustment: string;
  candidateCount: number;
  breakCount: number;
  suspendedBreakCount: number;
  generatedAt: string;
  updatedAt: string;
  items: LimitUpBreakItemResponse[];
}

export interface PostBreakBarResponse {
  tradeDate: string;
  close: number;
  changePercent: number | null;
  dayOffset: number;
}

export interface PostBreakBarsResponse {
  code: string;
  breakDate: string;
  priceAdjustment: string;
  bars: PostBreakBarResponse[];
}

export type ScreenerItemStatus = 'CONFIRMED' | 'PENDING_CONFIRMATION';

export interface ScreenerItemSummaryResponse {
  id: string;
  snapshotId: string;
  tradeDate: string;
  code: string;
  name: string;
  industry: string;
  status: ScreenerItemStatus;
  signalDate: string;
  score: number;
  priceActionScore: number;
  movingAverageScore: number;
  volumeScore: number;
  changePercent: number | null;
  tags: string[];
  inWatchlist: boolean;
  // uptrend-specific nullable fields
  setupType?: string | null;
  setupLabel?: string | null;
  indexCode?: string | null;
  indexName?: string | null;
  deviation3Percent?: number | null;
  deviation10Percent?: number | null;
  deviation30Percent?: number | null;
  distanceToMa10Percent?: number | null;
  avgAmount20?: number | null;
  avgAmount5?: number | null;
}

export interface ScreenerDailyBarResponse {
  tradeDate: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
  changePercent: number | null;
  ma5: number | null;
  ma10: number | null;
  ma20: number | null;
}

export interface ScreenerMarkerResponse {
  tradeDate: string;
  endDate?: string;
  kind: 'key_bearish' | 'stabilization' | 'confirm' | 'trend_start' | 'recent_high' | 'pullback';
  label: string;
}

export interface ScreenerStockDailyBarsResponse {
  code: string;
  endDate: string;
  lookback: number;
  priceAdjustment: string;
  bars: ScreenerDailyBarResponse[];
}

export interface ScreenerSnapshotResponse {
  id: string;
  tradeDate: string;
  strategyType: string;
  strategyName: string;
  strategyVersion: string;
  provider: string;
  priceAdjustment: string;
  criteria: Record<string, unknown>;
  scanCount: number;
  eligibleCount: number;
  confirmedCount: number;
  pendingCount: number;
  coverage: number;
  generatedAt: string;
  updatedAt: string;
  items: ScreenerItemSummaryResponse[];
}

export interface ScreenerItemDetailResponse extends ScreenerItemSummaryResponse {
  reason: Record<string, unknown>;
  bars: ScreenerDailyBarResponse[];
  markers: ScreenerMarkerResponse[];
}

export type ReviewEntryType = 'TRADE_ACTION' | 'OBSERVATION_DECISION';
export type ReviewPlanStatus = 'PLANNED' | 'UNPLANNED' | 'INTRADAY_ADJUSTMENT' | 'OBSERVED_ONLY';

export interface ReviewEntryResponse {
  id: string;
  entryType: ReviewEntryType;
  actionType: string;
  tradeDate: string;
  code: string | null;
  name: string | null;
  sectorTags: string[];
  positionContext: string | null;
  planStatus: ReviewPlanStatus;
  emotionTags: string[];
  problemTags: string[];
  reasonText: string;
  reflectionText: string;
  conclusionText: string;
  nextActionText: string;
  disciplineScore: number;
  outcomeText: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewEntryRequest {
  entryType: ReviewEntryType;
  actionType: string;
  tradeDate: string;
  code?: string | null;
  name?: string | null;
  sectorTags: string[];
  positionContext?: string | null;
  planStatus: ReviewPlanStatus;
  emotionTags: string[];
  problemTags: string[];
  reasonText: string;
  reflectionText: string;
  conclusionText: string;
  nextActionText: string;
  disciplineScore: number;
  outcomeText?: string | null;
}

export interface ReviewStatsResponse {
  startDate: string;
  endDate: string;
  totalCount: number;
  tradeActionCount: number;
  observationDecisionCount: number;
  planStatusCounts: Record<string, number>;
  emotionTagCounts: Record<string, number>;
  problemTagCounts: Record<string, number>;
  sectorTagCounts: Record<string, number>;
  codeCounts: Record<string, number>;
  averageDisciplineScore: number | null;
  lowDisciplineCount: number;
  lowDisciplineThreshold: number;
  planDeviationRatio: number;
}

export interface WeeklyReviewRequest {
  summaryText: string;
  repeatedMistakesText: string;
  effectiveActionsText: string;
  emotionPatternText: string;
  nextWeekFocusText: string;
  ruleCandidatesText: string;
  linkedEntryIds: string[];
}

export interface WeeklyReviewResponse extends WeeklyReviewRequest {
  id: string;
  weekStart: string;
  weekEnd: string;
  createdAt: string;
  updatedAt: string;
}

export interface WeeklyWorkbenchResponse {
  weekStart: string;
  weekEnd: string;
  stats: ReviewStatsResponse;
  entries: ReviewEntryResponse[];
  planDeviationEntries: ReviewEntryResponse[];
  lowDisciplineEntries: ReviewEntryResponse[];
  weeklyReview: WeeklyReviewResponse | null;
}

export type StockReviewCardStatus = 'OPEN' | 'CLOSED';
export type StockReviewInitialAction = 'BUY' | 'WATCH' | 'PLAN_BUY';
export type StockReviewEventType = 'HOLD' | 'ADD' | 'REDUCE' | 'SELL' | 'DO_T' | 'PLAN_CHANGE' | 'EMOTION' | 'OBSERVATION';

export interface StockReviewEventResponse {
  id: string;
  cardId: string;
  eventDate: string;
  eventType: StockReviewEventType;
  title: string;
  reasonText: string;
  positionSnapshot: string | null;
  deviatedFromPlan: boolean;
  emotionTags: string[];
  problemTags: string[];
  images?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface StockReviewCardResponse {
  id: string;
  status: StockReviewCardStatus;
  code: string | null;
  name: string | null;
  sectorTags: string[];
  startDate: string;
  endDate: string | null;
  initialAction: StockReviewInitialAction;
  initialPositionContext: string | null;
  initialPlanStatus: ReviewPlanStatus;
  initialReasonText: string;
  expectedMoveText: string;
  originalPlanText: string;
  initialEmotionTags: string[];
  problemTags: string[];
  sellReasonText: string | null;
  pnlText: string | null;
  followedPlan: boolean | null;
  disciplineScore: number | null;
  didWellText: string | null;
  didWrongText: string | null;
  reflectionText: string | null;
  ruleText: string | null;
  initialImages?: string[];
  closeImages?: string[];
  
  // Professional Trading Audit Fields
  strategyType: string | null;
  expectedRrRatio: string | null;
  stopLossTarget: string | null;
  pnlAmount: number | null;
  rMultiple: number | null;
  marketRegime: string | null;
  exitQuality: string | null;

  createdAt: string;
  updatedAt: string;
  events?: StockReviewEventResponse[];
}

export interface StockReviewCardRequest {
  code?: string | null;
  name?: string | null;
  sectorTags: string[];
  startDate: string;
  initialAction: StockReviewInitialAction;
  initialPositionContext?: string | null;
  initialPlanStatus: ReviewPlanStatus;
  initialReasonText: string;
  expectedMoveText: string;
  originalPlanText: string;
  initialEmotionTags: string[];
  initialImages?: string[];
  
  // Professional Trading Audit Fields
  strategyType?: string | null;
  expectedRrRatio?: string | null;
  stopLossTarget?: string | null;
}

export interface StockReviewEventRequest {
  eventDate: string;
  eventType: StockReviewEventType;
  title: string;
  reasonText: string;
  positionSnapshot?: string | null;
  deviatedFromPlan: boolean;
  emotionTags: string[];
  problemTags: string[];
  images?: string[];
}

export interface StockReviewCardCloseRequest {
  endDate: string;
  sellReasonText: string;
  pnlText: string;
  followedPlan: boolean;
  disciplineScore: number;
  problemTags: string[];
  didWellText: string;
  didWrongText: string;
  reflectionText: string;
  ruleText: string;
  closeImages?: string[];
  
  // Professional Trading Audit Fields
  pnlAmount?: number | null;
  rMultiple?: number | null;
  marketRegime?: string | null;
  exitQuality?: string | null;
}

export interface StockReviewCardSummaryResponse {
  startDate: string;
  endDate: string;
  openCount: number;
  closedCount: number;
  followedPlanCount?: number;
  deviatedPlanCount?: number;
  createdInRangeCount: number;
  closedInRangeCount: number;
  lowDisciplineClosedCount: number;
  lowDisciplineThreshold: number;
}

export type DataHealthStatus = 'READY' | 'STALE' | 'INCOMPLETE' | 'MISSING' | string;

export interface DataHealthOverviewResponse {
  asOfDate: string;
  calendar: {
    todayIsOpen: boolean;
    latestOpenDate: string | null;
    knownOpenDateCount: number;
  };
  dailyBars: {
    status: DataHealthStatus;
    latestTradeDate: string | null;
    coverageDate: string | null;
    availableBars: number;
    expectedBars: number;
    coverage: number;
    minCoverage: number;
  };
  sync: {
    runId: string;
    provider: string;
    jobType: string;
    status: string;
    startDate: string | null;
    endDate: string | null;
    startedAt: string | null;
    finishedAt: string | null;
    errorMessage: string | null;
    successItems: number | null;
    failedItems: number | null;
    skippedItems: number | null;
    warningCount: number | null;
  } | null;
  snapshot: {
    status: DataHealthStatus;
    tradeDate: string | null;
    updatedAt: string | null;
    candidateCount: number | null;
    breakCount: number | null;
    suspendedBreakCount: number | null;
  };
}

export interface EngineResponse {
  active: boolean;
  mode: 'PAPER_TRADING_ONLY';
  pollingEnabled: boolean;
  pollingIntervalSec: number;
  lastRunId: string | null;
  updatedAt: string;
  tradingTimeMode: {
    allowManualRunOutsideTradingTime: boolean;
    strictTradingTimeCheck: boolean;
  };
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

export interface IronLawRequest {
  text: string;
  tag: string;
  status: 'COMPLIANT' | 'CHALLENGED' | 'VIOLATED';
}

export interface IronLawResponse extends IronLawRequest {
  id: string;
  createdAt: string;
  updatedAt: string;
}

// --- Hot Stocks ---

export type HotStockResearchStatus = 'NONE' | 'HAS_REPORT' | 'PENDING' | 'PROCESSING';

export interface HotStockResearchState {
  status: HotStockResearchStatus;
  taskId: string | null;
  reportId: string | null;
}

export interface HotStockItemResponse {
  id: string;
  rank: number;
  code: string;
  name: string;
  price: number | null;
  changePercent: number | null;
  industry: string | null;
  ma5: number | null;
  ma20: number | null;
  trendLabel: string;
  isRecentLimitUpBreak: boolean;
  inWatchlist: boolean;
  hasOpenReviewCard: boolean;
  research: HotStockResearchState;
  createdAt: string;
}

export interface HotStockSnapshotResponse {
  snapshotId: string | null;
  tradeDate: string | null;
  source: string;
  isToday: boolean;
  isFallback: boolean;
  errorMessage: string | null;
  generatedAt?: string;
  createdAt?: string;
  updatedAt?: string;
  items: HotStockItemResponse[];
}
