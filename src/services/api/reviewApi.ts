import { apiClient, QueryParams } from './client';
import { PageResponse, ReviewEntryRequest, ReviewEntryResponse, ReviewStatsResponse, WeeklyReviewRequest, WeeklyReviewResponse, WeeklyWorkbenchResponse, IronLawRequest, IronLawResponse } from './types';

export const reviewApi = {
  createEntry: (body: ReviewEntryRequest) => apiClient.post<ReviewEntryResponse>('/reviews/entries', body),
  getEntries: (query?: QueryParams) => apiClient.get<PageResponse<ReviewEntryResponse>>('/reviews/entries', query),
  getEntry: (id: string) => apiClient.get<ReviewEntryResponse>(`/reviews/entries/${id}`),
  updateEntry: (id: string, body: Partial<ReviewEntryRequest>) => apiClient.patch<ReviewEntryResponse>(`/reviews/entries/${id}`, body),
  deleteEntry: (id: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/entries/${id}`),
  getStats: (query: { startDate: string; endDate: string }) => apiClient.get<ReviewStatsResponse>('/reviews/stats', query),
  getWeek: (weekStart: string) => apiClient.get<WeeklyWorkbenchResponse>(`/reviews/weeks/${weekStart}`),
  saveWeek: (weekStart: string, body: WeeklyReviewRequest) => apiClient.put<WeeklyReviewResponse>(`/reviews/weeks/${weekStart}`, body),

  // Iron Laws Backend API
  getIronLaws: () => apiClient.get<{ items: IronLawResponse[] }>('/reviews/iron-laws'),
  createIronLaw: (body: IronLawRequest) => apiClient.post<IronLawResponse>('/reviews/iron-laws', body),
  updateIronLaw: (id: string, body: Partial<IronLawRequest>) => apiClient.patch<IronLawResponse>(`/reviews/iron-laws/${id}`, body),
  deleteIronLaw: (id: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/iron-laws/${id}`),
};
