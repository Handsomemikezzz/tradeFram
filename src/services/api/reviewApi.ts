import { apiClient, QueryParams } from './client';
import { PageResponse, ReviewEntryRequest, ReviewEntryResponse, ReviewStatsResponse, WeeklyReviewRequest, WeeklyReviewResponse, WeeklyWorkbenchResponse } from './types';

export const reviewApi = {
  createEntry: (body: ReviewEntryRequest) => apiClient.post<ReviewEntryResponse>('/reviews/entries', body),
  getEntries: (query?: QueryParams) => apiClient.get<PageResponse<ReviewEntryResponse>>('/reviews/entries', query),
  getEntry: (id: string) => apiClient.get<ReviewEntryResponse>(`/reviews/entries/${id}`),
  updateEntry: (id: string, body: Partial<ReviewEntryRequest>) => apiClient.patch<ReviewEntryResponse>(`/reviews/entries/${id}`, body),
  deleteEntry: (id: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/entries/${id}`),
  getStats: (query: { startDate: string; endDate: string }) => apiClient.get<ReviewStatsResponse>('/reviews/stats', query),
  getWeek: (weekStart: string) => apiClient.get<WeeklyWorkbenchResponse>(`/reviews/weeks/${weekStart}`),
  saveWeek: (weekStart: string, body: WeeklyReviewRequest) => apiClient.put<WeeklyReviewResponse>(`/reviews/weeks/${weekStart}`, body),
};
