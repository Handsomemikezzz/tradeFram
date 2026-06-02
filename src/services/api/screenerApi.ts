/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './client';
import { ScreenerItemDetailResponse, ScreenerSnapshotResponse } from './types';

export const screenerApi = {
  createSnapshot: (body: { tradeDate?: string; provider?: string; strategyType?: string }) =>
    apiClient.post<ScreenerSnapshotResponse>('/screeners/snapshots', body),
  getDefaultSnapshot: (query?: { strategyType?: string; provider?: string }) =>
    apiClient.get<ScreenerSnapshotResponse>('/screeners/snapshots/default/latest', query),
  getSnapshot: (tradeDate: string, query?: { strategyType?: string; provider?: string }) =>
    apiClient.get<ScreenerSnapshotResponse>(`/screeners/snapshots/${tradeDate}`, query),
  getItemDetail: (snapshotId: string, itemId: string) =>
    apiClient.get<ScreenerItemDetailResponse>(`/screeners/snapshots/${snapshotId}/items/${itemId}`),
};
