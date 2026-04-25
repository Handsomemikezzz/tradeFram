import { apiClient, QueryParams } from './client';
import { LogResponse, OrderResponse, PageResponse, RiskCheckResponse } from './types';

export const auditApi = {
  getOrders: (query?: QueryParams) => apiClient.get<PageResponse<OrderResponse>>('/orders', query),
  getRiskChecks: (query?: QueryParams) => apiClient.get<PageResponse<RiskCheckResponse>>('/risk-checks', query),
  getLogs: (query?: QueryParams) => apiClient.get<PageResponse<LogResponse>>('/logs', query),
};
