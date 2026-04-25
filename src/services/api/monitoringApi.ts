import { apiClient, QueryParams } from './client';
import { MonitoringItemResponse, PageResponse, WatchlistItemResponse } from './types';

export const monitoringApi = {
  addWatchlistItem: (body: { code: string; source?: string; reportId?: string | null; note?: string | null }) =>
    apiClient.post<WatchlistItemResponse>('/watchlist/items', body),
  getMonitoringItems: (query?: QueryParams) => apiClient.get<PageResponse<MonitoringItemResponse>>('/monitoring-pool/items', query),
  addMonitoringItem: (body: { code: string; strategyId?: string; strategyName?: string; enabled?: boolean; source?: string; reportId?: string | null }) =>
    apiClient.post<MonitoringItemResponse>('/monitoring-pool/items', body),
  updateMonitoringItem: (id: string, body: { enabled?: boolean; reason?: string }) =>
    apiClient.patch<MonitoringItemResponse>(`/monitoring-pool/items/${id}`, body),
};
