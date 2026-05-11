import { apiClient } from './client';
import { LimitUpBreakSnapshotResponse } from './types';

export const limitUpBreakApi = {
  createSnapshot: (body: { tradeDate?: string; threshold?: number; provider?: string }) =>
    apiClient.post<LimitUpBreakSnapshotResponse>('/limit-up-breaks/snapshots', body),
  getDefaultSnapshot: (query?: { threshold?: number; provider?: string }) =>
    apiClient.get<LimitUpBreakSnapshotResponse>('/limit-up-breaks/snapshots/default/latest', query),
  getSnapshot: (tradeDate: string, query?: { threshold?: number; provider?: string }) =>
    apiClient.get<LimitUpBreakSnapshotResponse>(`/limit-up-breaks/snapshots/${tradeDate}`, query),
};
