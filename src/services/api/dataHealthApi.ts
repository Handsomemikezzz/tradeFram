import { apiClient } from './client';
import { DataHealthOverviewResponse } from './types';

export const dataHealthApi = {
  getOverview: () => apiClient.get<DataHealthOverviewResponse>('/data-health/overview'),
};
