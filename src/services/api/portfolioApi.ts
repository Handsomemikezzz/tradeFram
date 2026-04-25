import { apiClient, QueryParams } from './client';
import { AccountSummaryResponse, PageResponse, PositionResponse } from './types';

export const portfolioApi = {
  getAccountSummary: () => apiClient.get<AccountSummaryResponse>('/portfolio/account-summary'),
  getPositions: (query?: QueryParams) => apiClient.get<PageResponse<PositionResponse>>('/portfolio/positions', query),
};
