/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { MOCK_STOCKS, MOCK_RESEARCH_RECORDS, MOCK_MONITORING_POOL, MOCK_HOLDINGS, MOCK_ORDERS, MOCK_RISK_RECORDS, MOCK_LOGS, MOCK_DATA_SOURCES } from './mockData';
import { Stock, ResearchRecord, MonitoringStock, Holding, Order, RiskRecord, SystemLog, DataSource } from '../types';

// Simple mock service to simulate API calls
export const mockService = {
  getSystemKPIs: async () => ({
    observationCount: 24,
    monitoringCount: MOCK_MONITORING_POOL.length,
    holdingCount: MOCK_HOLDINGS.length,
    todaySignalCount: 8,
    todayOrderCount: 12,
    todayRiskCount: 2,
  }),
  
  getDataSources: async (): Promise<DataSource[]> => MOCK_DATA_SOURCES,
  
  getRecentResearch: async (): Promise<ResearchRecord[]> => MOCK_RESEARCH_RECORDS,
  
  getLogs: async (): Promise<SystemLog[]> => MOCK_LOGS,
  
  getStock: async (code: string): Promise<Stock | null> => {
    return MOCK_STOCKS[code] || null;
  },
  
  getMonitoringPool: async (): Promise<MonitoringStock[]> => MOCK_MONITORING_POOL,
  
  getHoldings: async (): Promise<Holding[]> => MOCK_HOLDINGS,
  
  getOrders: async (): Promise<Order[]> => MOCK_ORDERS,
  
  getRiskRecords: async (): Promise<RiskRecord[]> => MOCK_RISK_RECORDS,
};
