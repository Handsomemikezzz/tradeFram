/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Activity, CalendarDays, CheckCircle2, Database, RefreshCw, ServerCog, ShieldAlert, TrendingDown } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { dataHealthApi, DataHealthOverviewResponse, DataHealthStatus, formatDateTime } from '@/services/api';

function statusLabel(status: DataHealthStatus): string {
  if (status === 'READY') return '正常';
  if (status === 'STALE') return '滞后';
  if (status === 'INCOMPLETE') return '覆盖不足';
  if (status === 'MISSING') return '缺失';
  if (status === 'running') return '运行中';
  if (status === 'success') return '成功';
  if (status === 'partial') return '部分成功';
  if (status === 'failed') return '失败';
  return status;
}

function statusTone(status: string): 'green' | 'amber' | 'red' | 'blue' | 'gray' {
  if (['READY', 'success'].includes(status)) return 'green';
  if (['STALE', 'INCOMPLETE', 'partial'].includes(status)) return 'amber';
  if (['MISSING', 'failed'].includes(status)) return 'red';
  if (status === 'running') return 'blue';
  return 'gray';
}

function percent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export default function DataHealth() {
  const [overview, setOverview] = useState<DataHealthOverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const data = await dataHealthApi.getOverview();
      setOverview(data);
      setError(null);
    } catch (err) {
      setOverview(null);
      setError(err instanceof Error ? err.message : '数据健康状态加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const coverageValue = useMemo(() => Math.min(100, Math.max(0, (overview?.dailyBars.coverage || 0) * 100)), [overview]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-[#1A1C1E]">
            数据健康检查
            <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded uppercase tracking-tighter border border-blue-100">只读诊断</span>
          </h2>
          <p className="text-gray-500 text-xs font-medium uppercase tracking-widest mt-1">交易日历 / 日 K / 同步任务 / 断板快照</p>
        </div>
        <Button size="sm" variant="outline" className="h-8 text-[10px] font-bold uppercase tracking-widest" onClick={loadOverview} disabled={loading}>
          <RefreshCw className={cn("w-3 h-3 mr-1.5", loading && "animate-spin")} />
          刷新状态
        </Button>
      </div>

      {error && <div className="text-[12px] text-red-500 bg-red-50 border border-red-100 rounded-md px-3 py-2">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <HealthCard
          icon={CalendarDays}
          label="最新交易日"
          value={overview?.calendar.latestOpenDate || '-'}
          sub={overview ? (overview.calendar.todayIsOpen ? `${overview.asOfDate} 是交易日` : `${overview.asOfDate} 非本地交易日`) : '加载中'}
          tone={overview?.calendar.todayIsOpen ? 'green' : 'gray'}
        />
        <HealthCard
          icon={Database}
          label="日 K 数据"
          value={overview?.dailyBars.latestTradeDate || '-'}
          sub={overview ? `${statusLabel(overview.dailyBars.status)} / 覆盖 ${percent(overview.dailyBars.coverage)}` : '加载中'}
          tone={statusTone(overview?.dailyBars.status || '')}
        />
        <HealthCard
          icon={ServerCog}
          label="最近同步"
          value={overview?.sync ? statusLabel(overview.sync.status) : '-'}
          sub={overview?.sync ? `${overview.sync.endDate || '-'} / 失败 ${overview.sync.failedItems ?? '-'}` : '暂无记录'}
          tone={statusTone(overview?.sync?.status || '')}
        />
        <HealthCard
          icon={TrendingDown}
          label="断板快照"
          value={overview?.snapshot.tradeDate || '-'}
          sub={overview ? `${statusLabel(overview.snapshot.status)} / 断板 ${overview.snapshot.breakCount ?? '-'}` : '加载中'}
          tone={statusTone(overview?.snapshot.status || '')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 bg-white border border-gray-200 rounded-lg shadow-sm">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-[11px] font-bold uppercase tracking-widest text-gray-700">主板日 K 覆盖率</h3>
                <p className="text-[10px] text-gray-400 font-mono mt-1">{overview?.dailyBars.coverageDate || '-'} / 阈值 {overview ? percent(overview.dailyBars.minCoverage) : '-'}</p>
              </div>
              <StatusBadge status={overview?.dailyBars.status || 'MISSING'} />
            </div>
            <Progress value={coverageValue} className="h-2" />
            <div className="grid grid-cols-3 gap-3 text-xs font-mono">
              <Detail label="可用日 K" value={overview?.dailyBars.availableBars.toLocaleString() || '-'} />
              <Detail label="应有股票" value={overview?.dailyBars.expectedBars.toLocaleString() || '-'} />
              <Detail label="覆盖率" value={overview ? percent(overview.dailyBars.coverage) : '-'} />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-[11px] font-bold uppercase tracking-widest text-gray-700">快照状态</h3>
              <StatusBadge status={overview?.snapshot.status || 'MISSING'} />
            </div>
            <Detail label="快照日期" value={overview?.snapshot.tradeDate || '-'} />
            <Detail label="更新时间" value={overview?.snapshot.updatedAt ? formatDateTime(overview.snapshot.updatedAt) : '-'} />
            <Detail label="候选 / 断板" value={overview?.snapshot.candidateCount === null || !overview ? '-' : `${overview.snapshot.candidateCount} / ${overview.snapshot.breakCount}`} />
            <Detail label="停牌断板" value={overview?.snapshot.suspendedBreakCount === null || !overview ? '-' : `${overview.snapshot.suspendedBreakCount}`} />
          </CardContent>
        </Card>
      </div>

      <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-gray-700">最近同步任务</h3>
            {overview?.sync && <Badge variant="outline" className="text-[9px] bg-white border-gray-200 text-gray-500 font-bold uppercase tracking-widest">{overview.sync.runId}</Badge>}
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <Detail label="任务类型" value={overview?.sync?.jobType || '-'} />
            <Detail label="同步区间" value={overview?.sync ? `${overview.sync.startDate || '-'} -> ${overview.sync.endDate || '-'}` : '-'} />
            <Detail label="开始时间" value={overview?.sync?.startedAt ? formatDateTime(overview.sync.startedAt) : '-'} />
            <Detail label="完成时间" value={overview?.sync?.finishedAt ? formatDateTime(overview.sync.finishedAt) : '-'} />
            <Detail label="成功项" value={overview?.sync?.successItems?.toLocaleString() || '-'} />
            <Detail label="失败项" value={overview?.sync?.failedItems?.toLocaleString() || '-'} />
            <Detail label="跳过项" value={overview?.sync?.skippedItems?.toLocaleString() || '-'} />
            <Detail label="告警数" value={overview?.sync?.warningCount?.toLocaleString() || '-'} />
          </div>
          {overview?.sync?.errorMessage && <div className="mt-3 text-[11px] text-red-500 bg-red-50 border border-red-100 rounded-md px-3 py-2">{overview.sync.errorMessage}</div>}
        </CardContent>
      </Card>
    </div>
  );
}

function HealthCard({ icon: Icon, label, value, sub, tone }: { icon: typeof Activity; label: string; value: string; sub: string; tone: 'green' | 'amber' | 'red' | 'blue' | 'gray' }) {
  return (
    <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <CardContent className="p-4 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">{label}</p>
          <p className="text-lg font-bold text-gray-900 mt-1 truncate">{value}</p>
          <p className="text-[10px] text-gray-400 font-mono mt-0.5 truncate">{sub}</p>
        </div>
        <div className={cn("w-9 h-9 rounded-md flex items-center justify-center shrink-0", iconTone(tone))}>
          <Icon className="w-4 h-4" />
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone = statusTone(status);
  const Icon = tone === 'green' ? CheckCircle2 : tone === 'red' ? ShieldAlert : Activity;
  return (
    <Badge className={cn("text-[10px] px-2 py-0.5 rounded border font-bold", badgeTone(tone))}>
      <Icon className="w-3 h-3 mr-1" />
      {statusLabel(status)}
    </Badge>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-gray-50 border border-gray-100 px-3 py-2 min-w-0">
      <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{label}</p>
      <p className="text-[12px] text-gray-900 font-bold mt-1 truncate">{value}</p>
    </div>
  );
}

function iconTone(tone: 'green' | 'amber' | 'red' | 'blue' | 'gray'): string {
  if (tone === 'green') return 'bg-green-50 text-green-600';
  if (tone === 'amber') return 'bg-amber-50 text-amber-600';
  if (tone === 'red') return 'bg-red-50 text-red-600';
  if (tone === 'blue') return 'bg-blue-50 text-blue-600';
  return 'bg-gray-100 text-gray-500';
}

function badgeTone(tone: 'green' | 'amber' | 'red' | 'blue' | 'gray'): string {
  if (tone === 'green') return 'bg-green-50 text-green-700 border-green-100';
  if (tone === 'amber') return 'bg-amber-50 text-amber-700 border-amber-100';
  if (tone === 'red') return 'bg-red-50 text-red-700 border-red-100';
  if (tone === 'blue') return 'bg-blue-50 text-blue-700 border-blue-100';
  return 'bg-gray-50 text-gray-600 border-gray-100';
}
