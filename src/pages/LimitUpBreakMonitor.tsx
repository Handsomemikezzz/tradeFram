/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Activity, CalendarDays, Database, RefreshCw, RotateCcw, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { ApiClientError, formatDateTime, limitUpBreakApi, LimitUpBreakItemResponse, LimitUpBreakSnapshotResponse } from '@/services/api';

const DEFAULT_PROVIDER = 'AkShare';

function todayText(): string {
  return new Date().toISOString().slice(0, 10);
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

function sortItems(items: LimitUpBreakItemResponse[]): LimitUpBreakItemResponse[] {
  return [...items].sort((a, b) => {
    if (b.previousLimitUpHeight !== a.previousLimitUpHeight) return b.previousLimitUpHeight - a.previousLimitUpHeight;
    return a.code.localeCompare(b.code);
  });
}

export default function LimitUpBreakMonitor() {
  const [tradeDate, setTradeDate] = useState(todayText());
  const [threshold, setThreshold] = useState(2);
  const [snapshot, setSnapshot] = useState<LimitUpBreakSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const items = useMemo(() => sortItems(snapshot?.items || []), [snapshot]);

  const loadSnapshot = async () => {
    if (!tradeDate) return;
    setLoading(true);
    try {
      let data: LimitUpBreakSnapshotResponse;
      try {
        data = await limitUpBreakApi.getSnapshot(tradeDate, { threshold, provider: DEFAULT_PROVIDER });
      } catch (err) {
        if (!(err instanceof ApiClientError) || err.code !== 'LIMIT_UP_BREAK_SNAPSHOT_NOT_FOUND') throw err;
        data = await limitUpBreakApi.createSnapshot({ tradeDate, threshold, provider: DEFAULT_PROVIDER });
      }
      setSnapshot(data);
      if (data.tradeDate !== tradeDate) setTradeDate(data.tradeDate);
      setError(null);
    } catch (err) {
      setSnapshot(null);
      setError(err instanceof Error ? err.message : '断板快照加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSnapshot();
  }, []);

  const generateSnapshot = async () => {
    if (!tradeDate) return;
    setGenerating(true);
    try {
      const data = await limitUpBreakApi.createSnapshot({ tradeDate, threshold, provider: DEFAULT_PROVIDER });
      setSnapshot(data);
      if (data.tradeDate !== tradeDate) setTradeDate(data.tradeDate);
      setError(null);
      toast.success('断板快照已更新', {
        description: `${data.tradeDate} 候选 ${data.candidateCount} 只，断板 ${data.breakCount} 只`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : '生成断板快照失败';
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-[#1A1C1E]">
            连板断板监控
            <span className="px-2 py-0.5 bg-red-50 text-red-700 text-[10px] font-bold rounded uppercase tracking-tighter border border-red-100">盘后确认</span>
          </h2>
          <p className="text-gray-500 text-xs font-medium uppercase tracking-widest mt-1">主板短线专题监控</p>
        </div>

        <div className="flex flex-wrap items-center gap-2 bg-white p-2 rounded-lg border border-gray-200 shadow-sm">
          <div className="relative">
            <CalendarDays className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <Input type="date" value={tradeDate} onChange={(event) => setTradeDate(event.target.value)} className="h-8 pl-8 w-[150px] text-[11px] bg-white border-gray-200 rounded" />
          </div>
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
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">断板类型</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">断板前高度</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">当日涨跌幅</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">当日成交额</TableHead>
                <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">是否炸板</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-xs font-mono">
              {(loading || generating) && <TableRow><TableCell colSpan={6} className="px-4 py-8 text-center text-gray-400">正在处理断板快照...</TableCell></TableRow>}
              {!loading && !generating && error && <TableRow><TableCell colSpan={6} className="px-4 py-8 text-center text-red-500">{error}</TableCell></TableRow>}
              {!loading && !generating && !error && !snapshot && <TableRow><TableCell colSpan={6} className="px-4 py-8 text-center text-gray-400">当前日期暂无快照，可点击生成快照。</TableCell></TableRow>}
              {!loading && !generating && !error && snapshot && items.length === 0 && <TableRow><TableCell colSpan={6} className="px-4 py-8 text-center text-gray-400">当日候选连板股未出现断板。</TableCell></TableRow>}
              {!loading && !generating && !error && items.map((item) => (
                <TableRow key={item.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                  <TableCell className="px-4 py-3 border-b border-gray-50">
                    <div className="flex flex-col">
                      <span className="text-[11px] font-bold text-gray-900">{item.name}</span>
                      <span className="text-[10px] text-gray-400 font-mono tracking-tight">{item.code}</span>
                    </div>
                  </TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                    <Badge className={cn("text-[10px] px-2 py-0.5 rounded border font-bold", item.breakType === 'SUSPENDED' ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-700 border-red-100")}>{breakTypeLabel(item.breakType)}</Badge>
                  </TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                    <span className="text-[11px] font-bold text-gray-900 tabular-nums">{item.previousLimitUpHeight} 板</span>
                  </TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                    <span className={cn("text-[11px] font-bold tabular-nums", item.changePercent === null ? "text-gray-400" : item.changePercent >= 0 ? "text-red-600" : "text-green-600")}>
                      {item.changePercent === null ? '-' : `${item.changePercent >= 0 ? '+' : ''}${item.changePercent.toFixed(2)}%`}
                    </span>
                  </TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-right text-[11px] font-bold text-gray-700 tabular-nums">{formatAmount(item.amount)}</TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-center text-[11px] text-gray-400">{item.intradayBreak === null ? '留空' : item.intradayBreak ? '是' : '否'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
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
