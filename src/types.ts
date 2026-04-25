/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export enum SystemStatus {
  NORMAL = '正常',
  API_ERROR = '数据源异常',
  RISK_PAUSE = '风控暂停',
}

export enum ReportStatus {
  COMPLETED = '已完成',
  PROCESSING = '生成中',
  FAILED = '失败',
}

export enum SignalType {
  BUY = '买入',
  SELL = '卖出',
  HOLD = '观望',
}

export enum OrderStatus {
  PENDING = '委托中',
  FILLED = '已成交',
  CANCELLED = '已取消',
  REJECTED = '已拒绝',
}

export enum LogLevel {
  INFO = '信息',
  WARN = '警告',
  ERROR = '错误',
  SUCCESS = '成功',
}

export interface Stock {
  code: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  amount: number;
  market: string;
  industry: string;
  pe: number;
  roe: number;
  revenue: string;
  profit: string;
  grossMargin: number;
  netMargin: number;
  updateTime: string;
}

export interface ResearchRecord {
  id: string;
  code: string;
  name: string;
  researchTime: string;
  status: ReportStatus;
  updateTime: string;
}

export interface MonitoringStock {
  code: string;
  name: string;
  enabled: boolean;
  strategy: string;
  lastSignal: SignalType;
  signalReason: string;
  riskStatus: '通过' | '拦截';
  lastOrder: string;
  lastTrade: string;
}

export interface Holding {
  code: string;
  name: string;
  quantity: number;
  available: number;
  costPrice: number;
  currentPrice: number;
  marketValue: number;
  profitProgress: number; // profit/loss percent
  updateTime: string;
}

export interface Order {
  id: string;
  createTime: string;
  code: string;
  name: string;
  type: '买入' | '卖出';
  orderType: '限价' | '市价';
  quantity: number;
  price: number;
  filledQuantity: number;
  avgPrice: number;
  status: OrderStatus;
  rejectReason?: string;
}

export interface RiskRecord {
  id: string;
  time: string;
  code: string;
  signal: SignalType;
  passed: boolean;
  reason: string;
  rule: string;
}

export interface SystemLog {
  id: string;
  time: string;
  level: LogLevel;
  module: string;
  code?: string;
  event: string;
  detail: string;
  relId?: string;
}

export interface DataSource {
  name: string;
  status: 'Healthy' | 'Warning' | 'Error';
  latency: string;
}
