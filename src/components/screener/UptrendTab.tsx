/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Eye, RefreshCw, RotateCcw, TrendingUp } from 'lucide-react';
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
  ScreenerSnapshotResponse,
} from '@/services/api';

const DEFAULT_PROVIDER = 'AkShare';

type Props = {
  tradeDate: string;
};

function formatPct(value: number | null | undefined): string {
  if (value == null) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatAmount(value: number | null | undefined): string {
  if (value == null) return '-';
  const m = value / 1_000_000;
  return `${m.toFixed(0)}万`;
}

function sortItems(items: ScreenerItemSummaryResponse[]): ScreenerItemSummaryResponse[] {
  return [...items].sort((a, b) => {
    const aType = a.setupType ?? '';
    const bType = b.setupType ?? '';
    if (aType !== bType) return aType === 'HEALTHY_PULLBACK' ? -1 : 1;
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
  return err instanceof Error ? err.message : '上行趋势快照加载失败';
}

export function UptrendTab({ tradeDate }: Props) {
  const [snapshot, setSnapshot] = useState<ScreenerSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ScreenerItemDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [showRules, setShowRules] = useState(false);

  const sortedItems = useMemo(() => sortItems(snapshot?.items || []), [snapshot]);

  const loadSnapshot = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = tradeDate
        ? await screenerApi.getSnapshot(tradeDate, { strategyType: 'uptrend', provider: DEFAULT_PROVIDER })
        : await screenerApi.getDefaultSnapshot({ strategyType: 'uptrend', provider: DEFAULT_PROVIDER });
      setSnapshot(data);
      setSelectedId(sortItems(data.items)[0]?.id ?? null);
    } catch (err) {
      setSnapshot(null);
      setSelectedId(null);
      setDetail(null);
      if (!isSnapshotNotFound(err)) setError(snapshotErrorMessage(err));
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
        strategyType: 'uptrend',
      });
      setSnapshot(data);
      setSelectedId(sortItems(data.items)[0]?.id ?? null);
      toast.success('上行趋势快照已生成', {
        description: `找到 ${data.confirmedCount} 只候选`,
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
    if (!sortedItems.length) {
      setSelectedId(null);
      setDetail(null);
      return;
    }
    if (!selectedId || !sortedItems.some((item) => item.id === selectedId)) {
      setSelectedId(sortedItems[0].id);
    }
  }, [sortedItems, selectedId]);

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
        source: 'uptrend',
        note: `上行趋势 ${snapshot?.strategyVersion || 'v1'} @ ${snapshot?.tradeDate || tradeDate}`,
      });
      toast.success(`${item.name} 已加入观察池`);
      loadSnapshot();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入观察池失败');
    }
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" className="h-8 text-[10px] font-bold uppercase tracking-widest" onClick={loadSnapshot} disabled={loading || generating}>
          <RefreshCw className={cn('w-3 h-3 mr-1.5', loading && 'animate-spin')} />
          查询
        </Button>
        <Button size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-emerald-600 hover:bg-emerald-700" onClick={generateSnapshot} disabled={loading || generating}>
          <RotateCcw className={cn('w-3 h-3 mr-1.5', generating && 'animate-spin')} />
          生成快照
        </Button>
        <span className="text-[10px] text-gray-500">扫描主板非 ST，需前复权 + 未复权数据</span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        <Metric label="扫描" value={snapshot ? `${snapshot.scanCount}` : '-'} />
        <Metric label="过滤后" value={snapshot ? `${snapshot.eligibleCount}` : '-'} />
        <Metric label="候选" value={snapshot ? `${snapshot.confirmedCount}` : '-'} />
        <Metric label="滤除" value={snapshot ? `${(snapshot as { criteria?: { anomalyFilteredCount?: number } }).criteria?.anomalyFilteredCount ?? '-'}` : '-'} />
        <Metric label="覆盖率" value={snapshot ? `${(snapshot.coverage * 100).toFixed(1)}%` : '-'} />
        <Metric label="更新" value={snapshot ? formatDateTime(snapshot.updatedAt) : '-'} />
      </div>

      {/* Loading / Error states */}
      {(loading || generating) && <div className="text-sm text-gray-400 py-8 text-center">正在处理上行趋势快照...</div>}
      {!loading && !generating && error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}
      {!loading && !generating && !error && !snapshot && (
        <Card><CardContent className="p-8 text-center text-gray-500 text-sm">暂无快照，可点击生成</CardContent></Card>
      )}
      {!loading && !generating && !error && snapshot && sortedItems.length === 0 && (
        <Card><CardContent className="p-8 text-center text-gray-500 text-sm">未找到上行趋势候选</CardContent></Card>
      )}

      {/* Main content */}
      {!loading && !generating && !error && snapshot && sortedItems.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-[340px_minmax(0,1fr)] gap-4">
          {/* Left: candidate list */}
          <Card className="border border-gray-200 max-h-[720px] overflow-y-auto">
            <CardContent className="p-0 divide-y divide-gray-100">
              {sortedItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className={cn(
                    'w-full text-left px-3 py-3 hover:bg-emerald-50 transition-colors',
                    selectedId === item.id && 'bg-emerald-50 border-l-2 border-emerald-500',
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-bold text-gray-900">{item.name}</div>
                      <div className="text-[10px] text-gray-400 font-mono">{item.code} · {item.industry}</div>
                    </div>
                    {item.setupType === 'HEALTHY_PULLBACK' ? (
                      <Badge className="text-[9px] bg-emerald-100 text-emerald-700 border-emerald-200">健康回踩</Badge>
                    ) : (
                      <Badge className="text-[9px] bg-blue-100 text-blue-700 border-blue-200">强势推进</Badge>
                    )}
                  </div>
                  {/* Tags */}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {item.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} className="text-[9px] bg-gray-100 text-gray-600 border-gray-200">{tag}</Badge>
                    ))}
                  </div>
                  {/* Metrics row */}
                  <div className="mt-2 grid grid-cols-3 text-[10px] text-gray-500">
                    <span>30日偏离 <span className={cn('font-bold', (item.deviation30Percent ?? 0) >= 150 ? 'text-orange-600' : 'text-gray-800')}>{formatPct(item.deviation30Percent)}</span></span>
                    <span className="text-center">距MA10 <span className="font-bold text-gray-800">{formatPct(item.distanceToMa10Percent)}</span></span>
                    <span className="text-right">评分 <span className="font-bold text-gray-800">{item.score}</span></span>
                  </div>
                  {/* Watchlist */}
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

          {/* Right: detail panel */}
          <Card className="border border-gray-200">
            <CardContent className="p-4 space-y-4">
              {detailLoading && <div className="h-[480px] flex items-center justify-center text-gray-400 text-sm">加载 K 线详情...</div>}
              {!detailLoading && detailError && (
                <div className="space-y-3">
                  <p className="text-sm text-red-600">{detailError}</p>
                  <Button size="sm" variant="outline" onClick={() => setSelectedId(selectedId)}>重试</Button>
                </div>
              )}
              {!detailLoading && !detailError && detail && (() => {
                const regulatory = (detail.reason?.regulatory ?? {}) as Record<string, unknown>;
                const trend = (detail.reason?.trend ?? {}) as Record<string, unknown>;
                const scores = (detail.reason?.scores ?? {}) as Record<string, unknown>;
                return (
                  <>
                    {/* Header */}
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-emerald-600" />
                          {detail.name}
                        </h3>
                        <p className="text-xs text-gray-500 font-mono">{detail.code} · {detail.industry}</p>
                      </div>
                      <div className="text-right text-xs text-gray-500">
                        <div>总分 <span className="font-bold text-gray-900">{detail.score}</span></div>
                        <div>价格 {detail.priceActionScore} / 均线 {detail.movingAverageScore} / 量能 {detail.volumeScore}</div>
                        <div className="text-[10px] mt-0.5 font-medium">{detail.setupLabel}</div>
                      </div>
                    </div>

                    {/* Regulatory & MA distance summary */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      <DetailMetric label="3日偏离" value={formatPct(detail.deviation3Percent)} />
                      <DetailMetric label="10日偏离" value={formatPct(detail.deviation10Percent)} />
                      <DetailMetric
                        label="30日偏离"
                        value={formatPct(detail.deviation30Percent)}
                        highlight={(detail.deviation30Percent ?? 0) >= 180 ? 'warn' : undefined}
                      />
                      <DetailMetric label="距MA10" value={formatPct(detail.distanceToMa10Percent)} />
                    </div>

                    {/* Regulatory index */}
                    {regulatory.indexName && (
                      <p className="text-[10px] text-gray-400">
                        对比指数：{String(regulatory.indexName)}（{String(regulatory.indexCode)}）
                        · 偏离余量 {formatPct(typeof regulatory.deviation30MarginPercent === 'number' ? regulatory.deviation30MarginPercent : null)}
                      </p>
                    )}

                    {/* Chart */}
                    <PatternAChart bars={detail.bars} markers={detail.markers} />

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2">
                      {detail.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-[10px]">{tag}</Badge>
                      ))}
                    </div>

                    {/* Score breakdown */}
                    {scores && (
                      <p className="text-[11px] text-gray-600 leading-relaxed">
                        入场设置 {String(scores.entry ?? detail.priceActionScore)} 分 ·
                        趋势 {String(scores.trend ?? detail.movingAverageScore)} 分 ·
                        量能 {String(scores.volume ?? detail.volumeScore)} 分 ·
                        合规 {String(scores.regulatory ?? '-')} 分
                      </p>
                    )}

                    {/* Trend details */}
                    <div className="text-[10px] text-gray-400 grid grid-cols-2 gap-1">
                      {trend.trendStartDate && <span>趋势起点: {String(trend.trendStartDate)}</span>}
                      {trend.recentHighDate && <span>近20日高点: {String(trend.recentHighDate)}</span>}
                      {trend.drawdownFromHigh20Percent != null && <span>距高点回撤: {String(trend.drawdownFromHigh20Percent)}%</span>}
                      {trend.recentAlignedDays != null && <span>近5日多头排列: {String(trend.recentAlignedDays)} 天</span>}
                    </div>

                    <button type="button" className="text-[11px] text-blue-600 underline" onClick={() => setShowRules((v) => !v)}>
                      {showRules ? '收起规则摘要' : '展开规则摘要'}
                    </button>
                    {showRules && (
                      <p className="text-[11px] text-gray-500 leading-relaxed">
                        上行趋势策略：MA5 &gt; MA10 &gt; MA20 多头排列 + 30日涨幅偏离 &lt; 200% + 量能温和放大。
                        趋势确认使用前复权数据，涨停判断使用未复权数据。仅供复盘验证，不构成投资建议。
                      </p>
                    )}
                  </>
                );
              })()}
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

function DetailMetric({ label, value, highlight }: { label: string; value: string; highlight?: 'warn' }) {
  return (
    <div className="bg-gray-50 rounded p-2">
      <p className="text-[9px] uppercase tracking-widest text-gray-400">{label}</p>
      <p className={cn('text-sm font-bold mt-0.5', highlight === 'warn' ? 'text-orange-600' : 'text-gray-900')}>{value}</p>
    </div>
  );
}
