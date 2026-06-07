import { apiClient, QueryParams } from './client';
import { PageResponse, ResearchRecordResponse, ResearchReportResponse, ResearchStatsResponse, ResearchTaskResponse } from './types';

export const researchApi = {
  createTask: (body: { code: string; market?: string; source?: string; options?: Record<string, unknown> }) =>
    apiClient.post<ResearchTaskResponse>('/research/tasks', body),
  getTask: (taskId: string) => apiClient.get<ResearchTaskResponse>(`/research/tasks/${taskId}`),
  deleteTask: (taskId: string) => apiClient.delete<{ deleted: boolean }>(`/research/tasks/${taskId}`),
  getRecords: (query?: QueryParams) => apiClient.get<PageResponse<ResearchRecordResponse>>('/research/records', query),
  getReportByCode: (code: string) => apiClient.get<ResearchReportResponse>(`/research/reports/by-code/${code}`),
  getStats: (period = 'month') => apiClient.get<ResearchStatsResponse>('/research/stats', { period }),
};
