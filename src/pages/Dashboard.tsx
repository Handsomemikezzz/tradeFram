/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
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
  ArrowDownRight
} from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TodayTasks } from '@/components/dashboard/TodayTasks';
import { MonitoringTable } from '@/components/dashboard/MonitoringTable';
import { MOCK_DATA_SOURCES, MOCK_RESEARCH_RECORDS, MOCK_LOGS } from '@/services/mockData';
import { LogLevel } from '@/types';
import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';

export default function Dashboard() {
  const kpis = [
    { label: '观察池监控', value: 24, icon: Eye, color: 'text-[#1A1C1E]', trend: '+3 今日新增', trendColor: 'text-blue-500' },
    { label: '今日信号 (Signals)', value: 8, icon: Terminal, color: 'text-red-600', trend: '5 买入 / 3 卖出', trendColor: 'text-gray-400' },
    { label: '风控拦截', value: 2, icon: ShieldAlert, color: 'text-amber-600', trend: '查看拦截详情', trendColor: 'text-amber-600 underline' },
    { label: '模拟账户净值', value: '¥1,024,530', icon: TrendingUp, color: 'text-green-600', trend: '+2.45% 本月收益', trendColor: 'text-green-600' },
  ];

  return (
    <div className="space-y-4">
      {/* Risk Warning Banner */}
      <div className="p-2 bg-amber-50 border border-amber-200 rounded flex items-center shadow-sm">
        <span className="text-amber-600 mr-2 text-sm">⚠️</span>
        <p className="text-[11px] text-amber-800 font-medium">
          风险提示：本系统仅用于研究学习和模拟交易，不构成投资建议。所有交易结果均为模拟数据，请知悉。
        </p>
      </div>

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

      {/* Today's Tasks */}
      <TodayTasks />

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
            {MOCK_LOGS.map((log) => (
              <div key={log.id} className="flex space-x-2 border-b border-white/5 pb-2 last:border-0">
                <span className="text-gray-500 tabular-nums shrink-0">[{log.time.split(' ')[1].substring(0, 8)}]</span>
                <span className={cn(
                  "font-bold shrink-0 text-[10px]",
                  log.level === LogLevel.SUCCESS ? "text-green-400" : 
                  log.level === LogLevel.ERROR ? "text-red-400" :
                  log.level === LogLevel.WARN ? "text-amber-400" : "text-blue-400"
                )}>
                  {log.level.substring(0, 4)}
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
            className="w-full bg-gray-100 border border-gray-200 rounded px-3 h-8 text-xs focus-visible:ring-blue-500"
          />
        </div>
        <Button size="sm" className="bg-blue-600 text-white text-[10px] font-bold rounded shadow-lg shadow-blue-100 hover:bg-blue-700 h-8 px-4 uppercase tracking-wider">
          开始 AI 研究分析
        </Button>
        <div className="flex-1"></div>
        <div className="hidden md:flex space-x-4 text-[10px] font-bold uppercase tracking-wider">
          <div className="flex items-center text-gray-500">
            <span className="w-2 h-2 rounded-full bg-blue-500 mr-2"></span>
            已完成研究: 124
          </div>
          <div className="flex items-center text-gray-500">
            <span className="w-2 h-2 rounded-full bg-gray-300 mr-2"></span>
            待处理任务: 0
          </div>
        </div>
      </Card>
    </div>
  );
}
