import { apiClient } from './client';
import { EngineResponse, ExecutionTraceResponse, PaperTradingRunResponse, RiskSystemStatusResponse } from './types';

export const tradingApi = {
  getEngine: () => apiClient.get<EngineResponse>('/paper-trading/engine'),
  updateEngine: (body: { active: boolean; reason?: string }) => apiClient.patch<EngineResponse>('/paper-trading/engine', body),
  runPaperTrading: (body: { trigger?: 'MANUAL' | 'AUTO'; scope?: { monitoringItemIds?: string[]; enabledOnly?: boolean }; dryRun?: boolean } = {}) =>
    apiClient.post<PaperTradingRunResponse>('/paper-trading/runs', body),
  getRiskSystemStatus: () => apiClient.get<RiskSystemStatusResponse>('/risk/system-status'),
  getLatestExecutionTrace: () => apiClient.get<ExecutionTraceResponse>('/execution-traces/latest'),
};
