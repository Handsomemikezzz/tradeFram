/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { 
  SystemStatus, ReportStatus, SignalType, OrderStatus, LogLevel,
  Stock, ResearchRecord, MonitoringStock, Holding, Order, RiskRecord, SystemLog, DataSource
} from '../types';

export const MOCK_STOCKS: Record<string, Stock> = {
  '600519': {
    code: '600519.SH',
    name: '贵州茅台',
    price: 1650.50,
    change: 12.30,
    changePercent: 0.75,
    volume: 12500,
    amount: 2063000000,
    market: '上证主板',
    industry: '白酒',
    pe: 28.5,
    roe: 31.2,
    revenue: '1500.20 亿',
    profit: '740.10 亿',
    grossMargin: 91.5,
    netMargin: 49.3,
    updateTime: '2024-05-20 15:00:00'
  },
  '000858': {
    code: '000858.SZ',
    name: '五粮液',
    price: 152.30,
    change: -1.20,
    changePercent: -0.78,
    volume: 45000,
    amount: 685000000,
    market: '深证主板',
    industry: '白酒',
    pe: 18.2,
    roe: 25.1,
    revenue: '830.50 亿',
    profit: '300.20 亿',
    grossMargin: 75.2,
    netMargin: 36.1,
    updateTime: '2024-05-20 15:00:00'
  },
  '300750': {
    code: '300750.SZ',
    name: '宁德时代',
    price: 198.45,
    change: 5.60,
    changePercent: 2.90,
    volume: 250000,
    amount: 4960000000,
    market: '创业板',
    industry: '锂电池',
    pe: 15.6,
    roe: 22.4,
    revenue: '4000.10 亿',
    profit: '440.50 亿',
    grossMargin: 20.2,
    netMargin: 11.0,
    updateTime: '2024-05-20 15:00:00'
  },
  '601318': {
    code: '601318.SH',
    name: '中国平安',
    price: 45.30,
    change: 0.10,
    changePercent: 0.22,
    volume: 800000,
    amount: 3624000000,
    market: '上证主板',
    industry: '保险',
    pe: 8.5,
    roe: 12.1,
    revenue: '12000.50 亿',
    profit: '1000.20 亿',
    grossMargin: 100.0,
    netMargin: 8.3,
    updateTime: '2024-05-20 15:00:00'
  }
};

export const MOCK_RESEARCH_RECORDS: ResearchRecord[] = [
  { id: '1', code: '600519', name: '贵州茅台', researchTime: '2024-05-20 10:30', status: ReportStatus.COMPLETED, updateTime: '2024-05-20 15:00' },
  { id: '2', code: '000858', name: '五粮液', researchTime: '2024-05-19 14:20', status: ReportStatus.COMPLETED, updateTime: '2024-05-20 15:00' },
  { id: '3', code: '300750', name: '宁德时代', researchTime: '2024-05-20 11:15', status: ReportStatus.COMPLETED, updateTime: '2024-05-20 15:00' },
  { id: '4', code: '601318', name: '中国平安', researchTime: '2024-05-20 13:45', status: ReportStatus.FAILED, updateTime: '2024-05-20 14:00' },
];

export const MOCK_MONITORING_POOL: MonitoringStock[] = [
  {
    code: '600519',
    name: '贵州茅台',
    enabled: true,
    strategy: '均线回归',
    lastSignal: SignalType.HOLD,
    signalReason: '价格处于中位线，无明显趋势',
    riskStatus: '通过',
    lastOrder: '2024-05-18',
    lastTrade: '2024-05-18'
  },
  {
    code: '300750',
    name: '宁德时代',
    enabled: true,
    strategy: '突破策略',
    lastSignal: SignalType.BUY,
    signalReason: '放量突破20日均线',
    riskStatus: '通过',
    lastOrder: '2024-05-20',
    lastTrade: '2024-05-20'
  },
  {
    code: '000858',
    name: '五粮液',
    enabled: false,
    strategy: '抄底宝',
    lastSignal: SignalType.HOLD,
    signalReason: '策略未激活',
    riskStatus: '通过',
    lastOrder: '-',
    lastTrade: '-'
  }
];

export const MOCK_HOLDINGS: Holding[] = [
  {
    code: '600519',
    name: '贵州茅台',
    quantity: 100,
    available: 100,
    costPrice: 1600.00,
    currentPrice: 1650.50,
    marketValue: 165050,
    profitProgress: 3.15,
    updateTime: '2024-05-20 15:00'
  },
  {
    code: '300750',
    name: '宁德时代',
    quantity: 500,
    available: 500,
    costPrice: 190.00,
    currentPrice: 198.45,
    marketValue: 99225,
    profitProgress: 4.45,
    updateTime: '2024-05-20 15:00'
  }
];

export const MOCK_ORDERS: Order[] = [
  {
    id: 'ORD20240520001',
    createTime: '2024-05-20 09:35',
    code: '300750',
    name: '宁德时代',
    type: '买入',
    orderType: '限价',
    quantity: 500,
    price: 198.00,
    filledQuantity: 500,
    avgPrice: 198.00,
    status: OrderStatus.FILLED
  },
  {
    id: 'ORD20240520002',
    createTime: '2024-05-20 10:15',
    code: '000858',
    name: '五粮液',
    type: '买入',
    orderType: '限价',
    quantity: 1000,
    price: 150.00,
    filledQuantity: 0,
    avgPrice: 0,
    status: OrderStatus.REJECTED,
    rejectReason: '超过单股限额 (50,000 RMB)'
  }
];

export const MOCK_RISK_RECORDS: RiskRecord[] = [
  {
    id: 'R1',
    time: '2024-05-20 10:15',
    code: '000858',
    signal: SignalType.BUY,
    passed: false,
    reason: '订单金额 150,000 RMB 超过最大单股持仓限制 50,000 RMB',
    rule: 'MAX_SINGLE_STOCK_POS'
  },
  {
    id: 'R2',
    time: '2024-05-20 09:35',
    code: '300750',
    signal: SignalType.BUY,
    passed: true,
    reason: '各项指标符合风控规则',
    rule: 'BASIC_CHECK'
  }
];

export const MOCK_LOGS: SystemLog[] = [
  { id: 'L1', time: '2024-05-20 15:00:05', level: LogLevel.INFO, module: 'DataSync', event: '行情更新成功', detail: '成功从 Tushare 同步 1500 只股票日线数据' },
  { id: 'L2', time: '2024-05-20 14:30:12', level: LogLevel.SUCCESS, module: 'AI', event: '报告生成', code: '600519', detail: '贵州茅台深度研究报告生成完毕' },
  { id: 'L3', time: '2024-05-20 10:15:00', level: LogLevel.WARN, module: 'RiskEngine', event: '风控拦截', code: '000858', detail: '五粮液买入信号被风控引擎拦截', relId: 'R1' },
];

export const MOCK_DATA_SOURCES: DataSource[] = [
  { name: 'Tushare', status: 'Healthy', latency: '45ms' },
  { name: 'AkShare', status: 'Healthy', latency: '120ms' },
  { name: 'AI Service', status: 'Healthy', latency: '1.2s' },
  { name: 'Local DB', status: 'Healthy', latency: '2ms' },
];
