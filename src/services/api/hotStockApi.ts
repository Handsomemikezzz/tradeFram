/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './client';
import { HotStockSnapshotResponse } from './types';

export const hotStockApi = {
  getLatest: (limit = 20) => apiClient.get<HotStockSnapshotResponse>('/hot-stocks/latest', { limit }),
  createSnapshot: (body?: { limit?: number; forceRefresh?: boolean; source?: string }) =>
    apiClient.post<HotStockSnapshotResponse>('/hot-stocks/snapshots', body ?? { limit: 20, forceRefresh: true, source: 'EastmoneyHotRank' }),
  getSummary: (limit = 5) => apiClient.get<HotStockSnapshotResponse>('/hot-stocks/summary', { limit }),
};
