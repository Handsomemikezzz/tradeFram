/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Eye, RefreshCw, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { PatternAChart } from '@/components/screener/PatternAChart';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import {
  ApiClientError,
  formatDateTime,
  monitoringApi,
  screenerApi,
  ScreenerItemDetailResponse,
  ScreenerItemSummaryResponse,
  ScreenerItemStatus,
  ScreenerSnapshotResponse,
} from '@/services/api';

const DEFAULT_PROVIDER = 'AkShare';

type StatusFilter = 'CONFIRMED' | 'ALL' | 'PENDING_CONFIRMATION';

type Props = {
  tradeDate: string;
};

function statusLabel(status: ScreenerItemStatus): string {
  return status === 'CONFIRMED' ? '已确认' : '待确认';
}

function formatPercent(value: number | null): string {
  if (value === null) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function sortItems(items: ScreenerItemSummaryResponse[]): ScreenerItemSummaryResponse[] {
  return [...items].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'CONFIRMED' ? -1 : 1;
    if (b.score !== a.score) return b.score - a.score;
    return a.code.localeCompare(b.code);
  });
}

function isSnapshotNotFound(err: unknown): boolean {
  return err instanceof ApiClientError && err.code === 'SCREENER_SNAPSHOT_NOT_FOUND';
}

function snapshotErrorMessage(err: unknown): string {
  if (err instanceof ApiClientError && err.code === 'SCREENER_DATA_COVERAGE_TOO_LOW') {
    return `数据问题：${err.message}`;
  }
  return err instanceof Error ? err.message : '走势 A 快照加载失败';
}

export function PatternATab({ tradeDate }: Props) {
  const [snapshot, setSnapshot] = useState<ScreenerSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('CONFIRMED');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ScreenerItemDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [showRules, setShowRules] = useState(false);

  const filteredItems = useMemo(() => {
    const items = sortItems(snapshot?.items || []);
    if (statusFilter === 'ALL') return items;
    return items.filter((item) => item.status === statusFilter);
  }, [snapshot, statusFilter]);

  const loadSnapshot = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = tradeDate
        ? await screenerApi.getSnapshot(tradeDate, { strategyType: 'pattern_a', provider: DEFAULT_PROVIDER })
        : await screenerApi.getDefaultSnapshot({ strategyType: 'pattern_a', provider: DEFAULT_PROVIDER });
      setSnapshot(data);
      const nextItems = sortItems(data.items).filter((item) => statusFilter === 'ALL' || item.status === statusFilter);
      setSelectedId(nextItems[0]?.id ?? null);
    } catch (err) {
      setSnapshot(null);
      setSelectedId(null);
      setDetail(null);
      if (isSnapshotNotFound(err)) {
        setError(null);
      } else {
        setError(snapshotErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const generateSnapshot = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await screenerApi.createSnapshot({
        tradeDate: tradeDate || undefined,
        provider: DEFAULT_PROVIDER,
        strategyType: 'pattern_a',
      });
      setSnapshot(data);
      const nextItems = sortItems(data.items).filter((item) => statusFilter === 'ALL' || item.status === statusFilter);
      setSelectedId(nextItems[0]?.id ?? null);
      toast.success('走势 A 快照已生成', {
        description: `已确认 ${data.confirmedCount}，待确认 ${data.pendingCount}`,
      });
    } catch (err) {
      const message = snapshotErrorMessage(err);
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    loadSnapshot();
  }, [tradeDate]);

  useEffect(() => {
    const nextItems = filteredItems;
    if (!nextItems.length) {
      setSelectedId(null);
      setDetail(null);
      return;
    }
    if (!selectedId || !nextItems.some((item) => item.id === selectedId)) {
      setSelectedId(nextItems[0].id);
    }
  }, [filteredItems, selectedId]);

  useEffect(() => {
    if (!snapshot || !selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    screenerApi
      .getItemDetail(snapshot.id, selectedId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setDetailError(err instanceof Error ? err.message : '详情加载失败');
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [snapshot?.id, selectedId]);

  const handleWatchlist = async (item: ScreenerItemSummaryResponse) => {
    try {
      await monitoringApi.addWatchlistItem({
        code: item.code,
        source: 'pattern_a',
        note: `走势 A ${snapshot?.strategyVersion || 'v2'} @ ${snapshot?.tradeDate || tradeDate}`,
      });
      toast.success(`${item.name} 已加入观察池`);
      loadSnapshot();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入观察池失败');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" className="h-8 text-[10px] font-bold uppercase tracking-widest" onClick={loadSnapshot} disabled={loading || generating}>
          <RefreshCw className={cn('w-3 h-3 mr-1.5', loading && 'animate-spin')} />
          查询
        </Button>
        <Button size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700" onClick={generateSnapshot} disabled={loading || generating}>
          <RotateCcw className={cn('w-3 h-3 mr-1.5', generating && 'animate-spin')} />
          生成快照
        </Button>
        <span className="text-[10px] text-gray-500">正在扫描主板非 ST 股票，可能需要几十秒</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        <Metric label="扫描" value={snapshot ? `${snapshot.scanCount}` : '-'} />
        <Metric label="过滤后" value={snapshot ? `${snapshot.eligibleCount}` : '-'} />
        <Metric label="已确认" value={snapshot ? `${snapshot.confirmedCount}` : '-'} />
        <Metric label="待确认" value={snapshot ? `${snapshot.pendingCount}` : '-'} />
        <Metric label="覆盖率" value={snapshot ? `${(snapshot.coverage * 100).toFixed(1)}%` : '-'} />
        <Metric label="更新" value={snapshot ? formatDateTime(snapshot.updatedAt) : '-'} />
      </div>

      <div className="flex flex-wrap gap-2">
        {(['CONFIRMED', 'ALL', 'PENDING_CONFIRMATION'] as StatusFilter[]).map((value) => (
          <Button
            key={value}
            size="sm"
            variant={statusFilter === value ? 'default' : 'outline'}
            className="h-7 text-[10px]"
            onClick={() => setStatusFilter(value)}
          >
            {value === 'CONFIRMED' ? '已确认' : value === 'PENDING_CONFIRMATION' ? '待确认' : '全部'}
          </Button>
        ))}
      </div>

      {(loading || generating) && <div className="text-sm text-gray-400 py-8 text-center">正在处理走势 A 快照...</div>}
      {!loading && !generating && error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}
      {!loading && !generating && !error && !snapshot && (
        <Card><CardContent className="p-8 text-center text-gray-500 text-sm">暂无快照，可点击生成</CardContent></Card>
      )}
      {!loading && !generating && !error && snapshot && filteredItems.length === 0 && (
        <Card><CardContent className="p-8 text-center text-gray-500 text-sm">当前筛选下暂无候选</CardContent></Card>
      )}

      {!loading && !generating && !error && snapshot && filteredItems.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-[320px_minmax(0,1fr)] gap-4">
          <Card className="border border-gray-200 max-h-[720px] overflow-y-auto">
            <CardContent className="p-0 divide-y divide-gray-100">
              {filteredItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className={cn(
                    'w-full text-left px-3 py-3 hover:bg-blue-50 transition-colors',
                    selectedId === item.id && 'bg-blue-50 border-l-2 border-blue-500',
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-bold text-gray-900">{item.name}</div>
                      <div className="text-[10px] text-gray-400 font-mono">{item.code} · {item.industry}</div>
                    </div>
                    <Badge variant="outline" className="text-[10px]">{statusLabel(item.status)}</Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {item.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} className="text-[9px] bg-gray-100 text-gray-600 border-gray-200">{tag}</Badge>
                    ))}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[10px] text-gray-500">
                    <span>信号 {item.signalDate}</span>
                    <span className="font-bold text-gray-800">评分 {item.score}</span>
                    <span className={cn(item.changePercent !== null && item.changePercent >= 0 ? 'text-red-600' : 'text-green-600')}>
                      {formatPercent(item.changePercent)}
                    </span>
                  </div>
                  <div className="mt-2">
                    {item.inWatchlist ? (
                      <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200">已观察</Badge>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-7 text-[10px]"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleWatchlist(item);
                        }}
                      >
                        <Eye className="w-3 h-3 mr-1" />
                        加入观察池
                      </Button>
                    )}
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="border border-gray-200">
            <CardContent className="p-4 space-y-4">
              {detailLoading && <div className="h-[480px] flex items-center justify-center text-gray-400 text-sm">加载 K 线详情...</div>}
              {!detailLoading && detailError && (
                <div className="space-y-3">
                  <p className="text-sm text-red-600">{detailError}</p>
                  <Button size="sm" variant="outline" onClick={() => setSelectedId(selectedId)}>重试</Button>
                </div>
              )}
              {!detailLoading && !detailError && detail && (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">{detail.name}</h3>
                      <p className="text-xs text-gray-500 font-mono">{detail.code} · {detail.industry}</p>
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      <div>总分 <span className="font-bold text-gray-900">{detail.score}</span></div>
                      <div>价格行为 {detail.priceActionScore} / 均线 {detail.movingAverageScore} / 量能 {detail.volumeScore}</div>
                    </div>
                  </div>
                  <PatternAChart bars={detail.bars} markers={detail.markers} />
                  <div className="flex flex-wrap gap-2">
                    {detail.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-[10px]">{tag}</Badge>
                    ))}
                  </div>
                  {typeof detail.reason?.scores === 'object' && detail.reason.scores !== null && (
                    <p className="text-[11px] text-gray-600 leading-relaxed">
                      价格行为 {String((detail.reason.scores as Record<string, unknown>).priceAction ?? detail.priceActionScore)} 分 ·
                      均线 {String((detail.reason.scores as Record<string, unknown>).movingAverage ?? detail.movingAverageScore)} 分 ·
                      量能 {String((detail.reason.scores as Record<string, unknown>).volume ?? detail.volumeScore)} 分
                    </p>
                  )}
                  <button type="button" className="text-[11px] text-blue-600 underline" onClick={() => setShowRules((value) => !value)}>
                    {showRules ? '收起规则摘要' : '展开规则摘要'}
                  </button>
                  {showRules && (
                    <p className="text-[11px] text-gray-500 leading-relaxed">
                      本页信号基于盘后未复权日 K 规则引擎生成，仅供复盘验证，不构成投资建议。
                    </p>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="border border-gray-200">
      <CardContent className="p-3">
        <p className="text-[10px] uppercase tracking-widest text-gray-400">{label}</p>
        <p className="text-sm font-bold text-gray-900 mt-1 truncate">{value}</p>
      </CardContent>
    </Card>
  );
}
