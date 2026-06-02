/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Activity, CalendarDays, ChevronDown, ChevronRight, Database, RefreshCw, RotateCcw, TrendingDown } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { ApiClientError, formatDateTime, limitUpBreakApi, LimitUpBreakItemResponse, LimitUpBreakSnapshotResponse, PostBreakBarsResponse } from '@/services/api';

const DEFAULT_PROVIDER = 'AkShare';

function todayText(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, '0');
  const day = `${now.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function breakTypeLabel(type: string): string {
  if (type === 'SUSPENDED') return '停牌断板';
  if (type === 'CLOSE_NOT_LIMIT_UP') return '收盘断板';
  return type;
}

function formatAmount(amount: number | null): string {
  if (amount === null) return '-';
  if (Math.abs(amount) >= 100_000_000) return `${(amount / 100_000_000).toFixed(2)} 亿`;
  if (Math.abs(amount) >= 10_000) return `${(amount / 10_000).toFixed(2)} 万`;
  return amount.toLocaleString();
}

function formatPercent(value: number | null): string {
  if (value === null) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function sortItems(items: LimitUpBreakItemResponse[]): LimitUpBreakItemResponse[] {
  return [...items].sort((a, b) => {
    if (b.previousLimitUpHeight !== a.previousLimitUpHeight) return b.previousLimitUpHeight - a.previousLimitUpHeight;
    return a.code.localeCompare(b.code);
  });
}

function snapshotErrorMessage(err: unknown): string {
  if (err instanceof ApiClientError && err.code === 'DATA_COVERAGE_TOO_LOW') {
    return `数据问题：${err.message}`;
  }
  return err instanceof Error ? err.message : '断板快照加载失败';
}

type LimitUpBreakMonitorProps = {
  embedded?: boolean;
  tradeDate?: string;
  onTradeDateChange?: (value: string) => void;
};

export default function LimitUpBreakMonitor({ embedded = false, tradeDate: externalTradeDate, onTradeDateChange }: LimitUpBreakMonitorProps = {}) {
  const [internalTradeDate, setInternalTradeDate] = useState('');
  const tradeDate = externalTradeDate ?? internalTradeDate;
  const setTradeDate = onTradeDateChange ?? setInternalTradeDate;
  const [threshold, setThreshold] = useState(2);
  const [snapshot, setSnapshot] = useState<LimitUpBreakSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  const [trendCache, setTrendCache] = useState<Record<string, PostBreakBarsResponse>>({});
  const [trendLoading, setTrendLoading] = useState<Record<string, boolean>>({});
  const [trendErrors, setTrendErrors] = useState<Record<string, string>>({});

  const items = useMemo(() => sortItems(snapshot?.items || []), [snapshot]);

  const loadSnapshot = async () => {
    setLoading(true);
    try {
      let data: LimitUpBreakSnapshotResponse;
      if (tradeDate) {
        data = await limitUpBreakApi.getSnapshot(tradeDate, { threshold, provider: DEFAULT_PROVIDER });
      } else {
        data = await limitUpBreakApi.getDefaultSnapshot({ threshold, provider: DEFAULT_PROVIDER });
      }
      setSnapshot(data);
      setExpandedCode(null);
      setTrendCache({});
      setTrendErrors({});
      if (data.tradeDate !== tradeDate) setTradeDate(data.tradeDate);
      setError(null);
    } catch (err) {
      setSnapshot(null);
      setError(snapshotErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSnapshot();
  }, [tradeDate, threshold]);

  const generateSnapshot = async () => {
    setGenerating(true);
    try {
      const data = await limitUpBreakApi.createSnapshot({ tradeDate: tradeDate || undefined, threshold, provider: DEFAULT_PROVIDER });
      setSnapshot(data);
      setExpandedCode(null);
      setTrendCache({});
      setTrendErrors({});
      if (data.tradeDate !== tradeDate) setTradeDate(data.tradeDate);
      setError(null);
      toast.success('断板快照已更新', {
        description: `${data.tradeDate} 候选 ${data.candidateCount} 只，断板 ${data.breakCount} 只`,
      });
    } catch (err) {
      const message = snapshotErrorMessage(err);
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const toggleTrend = async (item: LimitUpBreakItemResponse) => {
    if (!snapshot) return;
    if (expandedCode === item.code) {
      setExpandedCode(null);
      return;
    }
    setExpandedCode(item.code);
    if (trendCache[item.code] || trendLoading[item.code]) return;
    setTrendLoading((current) => ({ ...current, [item.code]: true }));
    setTrendErrors((current) => {
      const next = { ...current };
      delete next[item.code];
      return next;
    });
    try {
      const data = await limitUpBreakApi.getPostBreakBars(item.code, {
        breakDate: snapshot.tradeDate,
        maxForwardDays: 5,
        adjustment: 'none',
      });
      setTrendCache((current) => ({ ...current, [item.code]: data }));
    } catch (err) {
      setTrendErrors((current) => ({ ...current, [item.code]: err instanceof Error ? err.message : '走势数据加载失败' }));
    } finally {
      setTrendLoading((current) => ({ ...current, [item.code]: false }));
    }
  };

  return (
    <div className="space-y-5">
      <div className={cn("flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4", embedded && "lg:items-end")}>
        {!embedded && (
          <div>
            <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-[#1A1C1E]">
              连板断板监控
              <span className="px-2 py-0.5 bg-red-50 text-red-700 text-[10px] font-bold rounded uppercase tracking-tighter border border-red-100">盘后确认</span>
            </h2>
            <p className="text-gray-500 text-xs font-medium uppercase tracking-widest mt-1">主板短线专题监控</p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 bg-white p-2 rounded-lg border border-gray-200 shadow-sm">
          {!embedded && (
            <div className="relative">
              <CalendarDays className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <Input type="date" value={tradeDate} onChange={(event) => setTradeDate(event.target.value)} className="h-8 pl-8 w-[150px] text-[11px] bg-white border-gray-200 rounded" placeholder={todayText()} />
            </div>
          )}
          <div className="flex items-center gap-1 px-2 h-8 rounded border border-gray-200 bg-gray-50">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">门槛</span>
            <Input
              type="number"
              min={1}
              value={threshold}
              onChange={(event) => setThreshold(Math.max(1, Number(event.target.value) || 1))}
              className="h-6 w-12 border-0 bg-transparent p-0 text-center text-[11px] font-bold focus-visible:ring-0"
            />
          </div>
          <Button size="sm" variant="outline" className="h-8 text-[10px] font-bold uppercase tracking-widest" onClick={loadSnapshot} disabled={loading || generating}>
            <RefreshCw className={cn("w-3 h-3 mr-1.5", loading && "animate-spin")} />
            查询
          </Button>
          <Button size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700" onClick={generateSnapshot} disabled={loading || generating}>
            <RotateCcw className={cn("w-3 h-3 mr-1.5", generating && "animate-spin")} />
            生成快照
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <MetricCard icon={Database} label="数据源" value={snapshot?.provider || DEFAULT_PROVIDER} tone="neutral" sub={snapshot?.priceAdjustment === 'none' ? '未复权日 K' : '等待快照'} />
        <MetricCard icon={Activity} label="候选连板" value={snapshot ? `${snapshot.candidateCount}` : '-'} tone="blue" sub={`${threshold} 连板起步`} />
        <MetricCard icon={TrendingDown} label="确认断板" value={snapshot ? `${snapshot.breakCount}` : '-'} tone="red" sub={snapshot ? `停牌 ${snapshot.suspendedBreakCount} 只` : '未加载'} />
        <MetricCard icon={CalendarDays} label="更新时间" value={snapshot ? formatDateTime(snapshot.updatedAt) : '-'} tone="neutral" sub={snapshot?.previousTradeDate ? `前序 ${snapshot.previousTradeDate}` : '按日留存'} />
      </div>

      <Card className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-700 italic font-serif">断板名单</h4>
            <p className="text-[9px] text-gray-400 font-mono mt-0.5">{snapshot ? `${snapshot.tradeDate} / ${snapshot.threshold} 连板阈值` : '查询或生成快照后展示'}</p>
          </div>
          {snapshot && <Badge variant="outline" className="text-[9px] bg-white border-gray-200 text-gray-500 font-bold uppercase tracking-widest">Snapshot {snapshot.id}</Badge>}
        </div>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">股票</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">走势</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">断板类型</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">断板前高度</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">当日涨跌幅</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">当日成交额</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">是否炸板</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-xs font-mono">
              {(loading || generating) && <TableRow><TableCell colSpan={7} className="px-4 py-8 text-center text-gray-400">正在处理断板快照...</TableCell></TableRow>}
              {!loading && !generating && error && <TableRow><TableCell colSpan={7} className="px-4 py-8 text-center text-red-500">{error}</TableCell></TableRow>}
              {!loading && !generating && !error && !snapshot && <TableRow><TableCell colSpan={7} className="px-4 py-8 text-center text-gray-400">当前日期暂无快照，可点击生成快照。</TableCell></TableRow>}
              {!loading && !generating && !error && snapshot && items.length === 0 && <TableRow><TableCell colSpan={7} className="px-4 py-8 text-center text-gray-400">当日候选连板股未出现断板。</TableCell></TableRow>}
              {!loading && !generating && !error && items.map((item) => (
                <React.Fragment key={item.id}>
                  <TableRow className="hover:bg-blue-50 transition-colors border-gray-50 cursor-pointer" aria-expanded={expandedCode === item.code} onClick={() => toggleTrend(item)}>
                    <TableCell className="px-4 py-3 border-b border-gray-50">
                      <div className="flex flex-col">
                        <span className="text-[11px] font-bold text-gray-900">{item.name}</span>
                        <span className="text-[10px] text-gray-400 font-mono tracking-tight">{item.code}</span>
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                      <Button type="button" variant="outline" size="sm" className="h-7 w-7 p-0 border-gray-200 bg-white" aria-label={expandedCode === item.code ? '收起断板后走势' : '展开断板后走势'}>
                        {expandedCode === item.code ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      </Button>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                      <Badge className={cn("text-[10px] px-2 py-0.5 rounded border font-bold", item.breakType === 'SUSPENDED' ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-700 border-red-100")}>{breakTypeLabel(item.breakType)}</Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                      <span className="text-[11px] font-bold text-gray-900 tabular-nums">{item.previousLimitUpHeight} 板</span>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                      <span className={cn("text-[11px] font-bold tabular-nums", item.changePercent === null ? "text-gray-400" : item.changePercent >= 0 ? "text-red-600" : "text-green-600")}>
                        {formatPercent(item.changePercent)}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right text-[11px] font-bold text-gray-700 tabular-nums">{formatAmount(item.amount)}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center text-[11px] text-gray-400">{item.intradayBreak === null ? '留空' : item.intradayBreak ? '是' : '否'}</TableCell>
                  </TableRow>
                  {expandedCode === item.code && (
                    <TableRow className="bg-gray-50/60 hover:bg-gray-50/60 border-gray-100">
                      <TableCell colSpan={7} className="px-4 py-4 whitespace-normal">
                        <PostBreakTrendPanel data={trendCache[item.code]} loading={Boolean(trendLoading[item.code])} error={trendErrors[item.code]} />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function PostBreakTrendPanel({ data, loading, error }: { data?: PostBreakBarsResponse; loading: boolean; error?: string }) {
  if (loading) {
    return <div className="h-40 flex items-center justify-center text-[11px] text-gray-400">正在加载断板后走势...</div>;
  }
  if (error) {
    return <div className="h-40 flex items-center justify-center text-[11px] text-red-500">{error}</div>;
  }
  if (!data || data.bars.length === 0) {
    return <div className="h-40 flex items-center justify-center text-[11px] text-gray-400">暂无可展示的后续日 K 数据</div>;
  }

  const chartData = data.bars.map((bar) => ({
    ...bar,
    label: bar.dayOffset === 0 ? 'T0' : `T+${bar.dayOffset}`,
    dateLabel: bar.tradeDate.slice(5),
  }));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_280px] gap-4">
      <div className="h-44 min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 2, left: 0 }}>
            <CartesianGrid stroke="#EEF0F2" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#6B7280' }} />
            <YAxis dataKey="close" domain={['dataMin', 'dataMax']} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#6B7280' }} width={42} />
            <Tooltip content={<PostBreakTooltip />} />
            <ReferenceLine x="T0" stroke="#DC2626" strokeDasharray="4 4" label={{ value: '断板日', fill: '#DC2626', fontSize: 10, position: 'insideTopLeft' }} />
            <Line type="monotone" dataKey="close" stroke="#2563EB" strokeWidth={2} dot={{ r: 3, strokeWidth: 2, fill: '#FFFFFF' }} activeDot={{ r: 4 }} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-2 gap-2 content-start">
        {chartData.map((bar) => (
          <div key={bar.tradeDate} className={cn("border rounded-md px-2.5 py-2 bg-white", bar.dayOffset === 0 ? "border-red-200" : "border-gray-200")}>
            <div className="flex items-center justify-between gap-2">
              <span className={cn("text-[10px] font-bold", bar.dayOffset === 0 ? "text-red-600" : "text-gray-500")}>{bar.label}</span>
              <span className="text-[10px] text-gray-400">{bar.dateLabel}</span>
            </div>
            <div className="mt-1 flex items-baseline justify-between gap-2">
              <span className="text-[12px] font-bold text-gray-900 tabular-nums">{bar.close.toFixed(2)}</span>
              <span className={cn("text-[11px] font-bold tabular-nums", bar.changePercent === null ? "text-gray-400" : bar.changePercent >= 0 ? "text-red-600" : "text-green-600")}>{formatPercent(bar.changePercent)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PostBreakTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { label: string; tradeDate: string; close: number; changePercent: number | null } }> }) {
  if (!active || !payload?.length) return null;
  const bar = payload[0].payload;
  return (
    <div className="rounded-md border border-gray-200 bg-white px-3 py-2 shadow-sm">
      <div className="text-[10px] font-bold text-gray-500">{bar.label} / {bar.tradeDate}</div>
      <div className="mt-1 text-[11px] text-gray-700">收盘价 <span className="font-bold tabular-nums">{bar.close.toFixed(2)}</span></div>
      <div className={cn("text-[11px] font-bold tabular-nums", bar.changePercent === null ? "text-gray-400" : bar.changePercent >= 0 ? "text-red-600" : "text-green-600")}>涨跌幅 {formatPercent(bar.changePercent)}</div>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, sub, tone }: { icon: typeof Activity; label: string; value: string; sub: string; tone: 'blue' | 'red' | 'neutral' }) {
  return (
    <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <CardContent className="p-4 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">{label}</p>
          <p className="text-lg font-bold text-gray-900 mt-1 truncate">{value}</p>
          <p className="text-[10px] text-gray-400 font-mono mt-0.5 truncate">{sub}</p>
        </div>
        <div className={cn("w-9 h-9 rounded-md flex items-center justify-center shrink-0", tone === 'red' ? "bg-red-50 text-red-600" : tone === 'blue' ? "bg-blue-50 text-blue-600" : "bg-gray-100 text-gray-500")}>
          <Icon className="w-4 h-4" />
        </div>
      </CardContent>
    </Card>
  );
}
