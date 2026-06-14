/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  Eye, 
  Terminal, 
  ShoppingCart, 
  ShieldAlert, 
  TrendingUp, 
  History,
  Activity,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  ChevronDown,
  Flame,
} from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TodayTasks } from '@/components/dashboard/TodayTasks';
import { MonitoringTable } from '@/components/dashboard/MonitoringTable';
import { DailyFlow } from '@/components/dashboard/DailyFlow';
import { auditApi, DashboardOverviewResponse, formatCurrency, formatTime, hotStockApi, HotStockSnapshotResponse, logLevelLabel, LogResponse, researchApi, systemApi } from '@/services/api';
import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

export default function Dashboard() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<LogResponse[]>([]);
  const [logsError, setLogsError] = useState<string | null>(null);
  const [quickCode, setQuickCode] = useState('');
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [hotSummary, setHotSummary] = useState<HotStockSnapshotResponse | null>(null);
  const [hotStocksExpanded, setHotStocksExpanded] = useState(false);

  const HOT_STOCKS_PREVIEW_COUNT = 5;

  useEffect(() => {
    let cancelled = false;
    systemApi.getDashboardOverview()
      .then((data) => { if (!cancelled) setOverview(data); })
      .catch((err: Error) => { if (!cancelled) setOverviewError(err.message); });
    auditApi.getLogs({ pageSize: 20 })
      .then((page) => { if (!cancelled) setLogs(page.items); })
      .catch((err: Error) => { if (!cancelled) setLogsError(err.message); });
    hotStockApi.getSummary(50)
      .then((data) => { if (!cancelled) setHotSummary(data); })
      .catch(() => { if (!cancelled) setHotSummary(null); });
    return () => { cancelled = true; };
  }, []);

  const startQuickResearch = async () => {
    if (!quickCode || quickCode.length < 6) return;
    const task = await researchApi.createTask({ code: quickCode });
    window.location.href = `/research/${task.code}`;
  };

  const kpis = [
    { label: '观察池监控', value: overview?.kpis.watchlistCount ?? '-', icon: Eye, color: 'text-[#1A1C1E]', trend: overview?.kpis.watchlistTrendText || '加载中', trendColor: 'text-blue-500' },
    { label: '今日信号 (Signals)', value: overview?.kpis.todaySignalCount ?? '-', icon: Terminal, color: 'text-red-600', trend: overview ? `${overview.kpis.todayBuySignalCount} 买入 / ${overview.kpis.todaySellSignalCount} 卖出` : '加载中', trendColor: 'text-gray-400' },
    { label: '风控拦截', value: overview?.kpis.todayRiskBlockedCount ?? '-', icon: ShieldAlert, color: 'text-amber-600', trend: '查看拦截详情', trendColor: 'text-amber-600 underline' },
    { label: '模拟账户净值', value: overview ? formatCurrency(overview.kpis.paperAccountNetAsset) : '-', icon: TrendingUp, color: 'text-green-600', trend: overview ? `${overview.kpis.monthReturnPct >= 0 ? '+' : ''}${overview.kpis.monthReturnPct}% 本月收益` : '加载中', trendColor: 'text-green-600' },
  ];

  return (
    <div className="space-y-4">
      {overviewError && <div className="text-[11px] text-red-500">Dashboard 聚合数据加载失败：{overviewError}</div>}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <Card key={kpi.label} className="bg-white border border-gray-200 rounded-lg shadow-sm">
            <CardContent className="p-4">
              <h3 className="text-[10px] font-medium text-gray-500 mb-1 italic font-serif">
                {kpi.label}
              </h3>
              <p className={cn("text-2xl font-mono font-bold tracking-tight pb-1", kpi.color)}>{kpi.value}</p>
              <div className={cn("text-[10px] font-medium group cursor-pointer", kpi.trendColor)}>
                {kpi.trend}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Daily Flow */}
      <DailyFlow />

      {/* Today's Tasks */}
      <TodayTasks tasks={overview?.tasks} />

      {/* Hot Stocks Summary Card — collapsed by default */}
      <Card className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <CardContent className="p-0">
          <button
            type="button"
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50/80 transition-colors"
            onClick={() => setHotStocksExpanded((open) => !open)}
            aria-expanded={hotStocksExpanded}
          >
            <div className="flex min-w-0 items-center gap-2">
              <Flame className="h-4 w-4 shrink-0 text-orange-500" />
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-gray-900">热门股票</h3>
                <p className="text-[10px] text-gray-400 uppercase tracking-widest font-mono truncate">
                  {hotSummary?.tradeDate
                    ? `${hotSummary.tradeDate} · ${hotSummary.source} · ${hotSummary.items.length} 只`
                    : '暂无快照 · 点击前往热门股页刷新'}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="hidden sm:inline text-[10px] text-gray-400">
                {hotStocksExpanded ? '收起' : `展开 Top ${HOT_STOCKS_PREVIEW_COUNT}+`}
              </span>
              <ChevronDown
                className={cn(
                  'h-4 w-4 text-gray-400 transition-transform duration-200',
                  hotStocksExpanded && 'rotate-180',
                )}
              />
            </div>
          </button>

          {!hotStocksExpanded && (hotSummary?.items.length ?? 0) > 0 && (
            <div className="border-t border-gray-100 px-4 py-3">
              <div className="flex flex-wrap gap-2">
                {hotSummary!.items.slice(0, HOT_STOCKS_PREVIEW_COUNT).map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[10px] hover:border-blue-200 hover:bg-blue-50 transition-colors"
                    onClick={() => navigate('/hot-stocks')}
                  >
                    <span className="font-mono text-red-600">#{item.rank}</span>
                    <span className="font-bold text-gray-800 max-w-[5rem] truncate">{item.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {hotStocksExpanded && (
            <div className="border-t border-gray-100 px-4 pb-4 pt-3 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-gray-500">共 {hotSummary?.items.length ?? 0} 只 · 点击进入详情页</p>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-[10px] font-bold"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate('/hot-stocks');
                  }}
                >
                  查看全部
                </Button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 max-h-[420px] overflow-y-auto pr-1">
                {(hotSummary?.items ?? []).map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    className="text-left rounded border border-gray-100 bg-gray-50 px-3 py-2 hover:border-blue-200 hover:bg-blue-50 transition-colors"
                    onClick={() => navigate('/hot-stocks')}
                  >
                    <div className="text-[10px] font-mono text-red-600">#{item.rank}</div>
                    <div className="text-xs font-bold text-gray-900 truncate">{item.name}</div>
                    <div className="text-[10px] font-mono text-gray-400">{item.code}</div>
                  </button>
                ))}
                {(hotSummary?.items ?? []).length === 0 && (
                  <button
                    type="button"
                    className="col-span-full text-left rounded border border-dashed border-gray-200 bg-gray-50 px-3 py-3 text-xs text-gray-500 hover:border-blue-200 hover:bg-blue-50"
                    onClick={() => navigate('/hot-stocks')}
                  >
                    暂无热门股快照，进入热门股票页刷新。
                  </button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Main Monitoring Table */}
        <MonitoringTable />

        {/* System Logs Panel */}
        <Card className="lg:col-span-1 bg-[#1A1C1E] border border-gray-800 rounded-lg shadow-sm flex flex-col text-white overflow-hidden">
          <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-400">系统运行日志</h4>
            <span className="text-[9px] bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded font-mono">LIVE</span>
          </div>
          <CardContent className="p-4 flex-1 font-mono text-[11px] space-y-4 overflow-y-auto max-h-[350px]">
            {logsError && <div className="text-red-400">{logsError}</div>}
            {!logsError && logs.length === 0 && <div className="text-gray-500">暂无系统日志</div>}
            {!logsError && logs.map((log) => (
              <div key={log.id} className="flex space-x-2 border-b border-white/5 pb-2 last:border-0">
                <span className="text-gray-500 tabular-nums shrink-0">[{formatTime(log.time).substring(0, 8)}]</span>
                <span className={cn(
                  "font-bold shrink-0 text-[10px]",
                  log.level === 'SUCCESS' ? "text-green-400" : 
                  log.level === 'ERROR' ? "text-red-400" :
                  log.level === 'WARN' ? "text-amber-400" : "text-blue-400"
                )}>
                  {logLevelLabel(log.level).substring(0, 4)}
                </span>
                <span className="flex-1 text-gray-300 leading-tight">{log.event}: {log.detail}</span>
              </div>
            ))}
          </CardContent>
          <button className="m-4 py-2 border border-white/20 rounded text-[10px] uppercase font-bold text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
            进入交易日志控制台
          </button>
        </Card>
      </div>

      {/* Quick Tool Bottom Footer style (internal bar) */}
      <Card className="bg-white border border-gray-200 p-4 flex items-center space-x-4 shadow-sm rounded-lg">
        <label className="text-[10px] font-bold uppercase text-gray-500 w-24 shrink-0 tracking-widest">快速股票研究:</label>
        <div className="relative flex-1 max-w-sm">
          <Input 
            placeholder="请输入 A 股代码 (e.g. 600036)" 
            value={quickCode}
            onChange={(event) => setQuickCode(event.target.value)}
            maxLength={6}
            className="w-full bg-gray-100 border border-gray-200 rounded px-3 h-8 text-xs focus-visible:ring-blue-500"
          />
        </div>
        <Button size="sm" onClick={startQuickResearch} className="bg-blue-600 text-white text-[10px] font-bold rounded shadow-lg shadow-blue-100 hover:bg-blue-700 h-8 px-4 uppercase tracking-wider">
          开始 AI 研究分析
        </Button>
        <div className="flex-1"></div>
        <div className="hidden md:flex space-x-4 text-[10px] font-bold uppercase tracking-wider">
          <div className="flex items-center text-gray-500">
            <span className="w-2 h-2 rounded-full bg-blue-500 mr-2"></span>
            已完成研究: {overview?.quickResearchStats.completedResearchCount ?? '-'}
          </div>
          <div className="flex items-center text-gray-500">
            <span className="w-2 h-2 rounded-full bg-gray-300 mr-2"></span>
            待处理任务: {overview?.quickResearchStats.pendingTaskCount ?? '-'}
          </div>
        </div>
      </Card>
    </div>
  );
}
