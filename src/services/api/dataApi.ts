import { apiClient } from './client';
import { StockDataRefreshResponse, StockDataStatusResponse } from './types';

export const dataApi = {
  getStockStatus: (code: string, provider?: string) =>
    apiClient.get<StockDataStatusResponse>(`/data/stocks/${code}/status`, provider ? { provider } : undefined),
  refreshStock: (code: string, provider?: string) =>
    apiClient.post<StockDataRefreshResponse>(`/data/stocks/${code}/refresh`, undefined, provider ? { provider } : undefined),
};
