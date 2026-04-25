import { apiClient } from './client';
import { DashboardOverviewResponse, DataSourceHealthItem, MonitoringItemResponse, SystemStatusResponse } from './types';

export const systemApi = {
  getStatus: () => apiClient.get<SystemStatusResponse>('/system/status'),
  getDataSourcesHealth: () => apiClient.get<{ items: DataSourceHealthItem[] }>('/data-sources/health'),
  getDashboardOverview: () => apiClient.get<DashboardOverviewResponse>('/dashboard/overview'),
  getDashboardMonitoringSummary: (limit = 4) => apiClient.get<{ items: MonitoringItemResponse[] }>('/dashboard/monitoring-summary', { limit }),
};
