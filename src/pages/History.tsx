/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { 
  Briefcase, 
  ScrollText, 
  ShieldX, 
  Terminal, 
  ArrowUpRight, 
  ArrowDownRight,
  Search,
  Filter,
  CheckCircle2
} from 'lucide-react';
import { 
  MOCK_HOLDINGS, 
  MOCK_ORDERS, 
  MOCK_RISK_RECORDS, 
  MOCK_LOGS 
} from '@/services/mockData';
import { OrderStatus, LogLevel } from '@/types';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { AccountSummary } from '@/components/history/AccountSummary';

export default function HistoryPage() {
  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#1A1C1E]">持仓与日志审计</h2>
          <p className="text-gray-500 text-xs font-medium uppercase tracking-widest mt-1">资产状态与系统日志审计</p>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="relative group w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
            <Input className="pl-9 h-8 text-[11px] bg-white border-gray-200 rounded focus-visible:ring-blue-500" placeholder="搜索股票代码或订单 ID..." />
          </div>
          <Button variant="outline" size="icon" className="h-8 w-8 bg-white border-gray-200"><Filter className="w-3.5 h-3.5" /></Button>
        </div>
      </div>

      {/* Account Summary */}
      <AccountSummary />

      <Tabs defaultValue="holdings" className="space-y-4">
        <TabsList className="bg-white border border-gray-200 rounded-lg p-1 h-auto inline-flex shadow-sm">
          <TabsTrigger value="holdings" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest gap-2 data-[state=active]:bg-gray-100 border-none">
            <Briefcase className="w-3.5 h-3.5" /> 模拟持仓
          </TabsTrigger>
          <TabsTrigger value="orders" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest gap-2 data-[state=active]:bg-gray-100 border-none">
            <ScrollText className="w-3.5 h-3.5" /> 订单记录
          </TabsTrigger>
          <TabsTrigger value="risk" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest gap-2 data-[state=active]:bg-gray-100 border-none">
            <ShieldX className="w-3.5 h-3.5" /> 风控审计
          </TabsTrigger>
          <TabsTrigger value="logs" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest gap-2 data-[state=active]:bg-gray-100 border-none">
            <Terminal className="w-3.5 h-3.5" /> 系统日志
          </TabsTrigger>
        </TabsList>

        {/* Holdings Tab */}
        <TabsContent value="holdings">
          <Card className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
            <CardContent className="p-0">
               <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">股票信息</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">持仓/可卖</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">成本/现价</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">总市值</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">浮动盈亏</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">更新时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="text-xs font-mono">
                  {MOCK_HOLDINGS.map((h) => {
                    const isProfit = h.profitProgress >= 0;
                    return (
                      <TableRow key={h.code} className="hover:bg-blue-50 transition-colors border-gray-50">
                        <TableCell className="px-4 py-3 border-b border-gray-50">
                          <div className="flex flex-col">
                            <span className="text-[11px] font-bold text-gray-900">{h.name}</span>
                            <span className="text-[10px] text-gray-400 font-mono tracking-tight">{h.code}</span>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                          <div className="flex flex-col">
                            <span className="text-[11px] font-bold tabular-nums text-gray-900">{h.quantity}</span>
                            <span className="text-[10px] text-gray-400 tabular-nums">可用: {h.available}</span>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                          <div className="flex flex-col">
                            <span className="text-[11px] font-bold tabular-nums text-gray-900">{h.costPrice.toFixed(2)}</span>
                            <span className="text-[10px] text-gray-400 tabular-nums">当前价: {h.currentPrice.toFixed(2)}</span>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                          <span className="text-[11px] font-bold tabular-nums text-gray-900">¥{h.marketValue.toLocaleString()}</span>
                        </TableCell>
                        <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                           <div className={cn("flex items-center justify-end font-bold text-[11px] tabular-nums", isProfit ? "text-red-600" : "text-green-600")}>
                             {isProfit ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                             {isProfit ? '+' : ''}{h.profitProgress.toFixed(2)}%
                           </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 border-b border-gray-50 text-right text-[10px] text-gray-400 font-mono italic">{h.updateTime.split(' ')[1]}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Orders Tab */}
        <TabsContent value="orders">
           <Card className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
            <CardContent className="p-0">
               <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">订单 ID / 时间</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">股票</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">方向/类型</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">委托(价/量)</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">成交(价/量)</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="text-xs font-mono">
                  {MOCK_ORDERS.map((o) => (
                    <TableRow key={o.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                      <TableCell className="px-4 py-3 border-b border-gray-50">
                        <div className="flex flex-col">
                          <span className="text-[10px] font-mono font-bold text-gray-900">{o.id}</span>
                          <span className="text-[10px] text-gray-400 uppercase tracking-tighter">{o.createTime}</span>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50">
                        <div className="flex flex-col">
                          <span className="text-[11px] font-bold text-gray-900">{o.name}</span>
                          <span className="text-[10px] text-gray-400 font-mono tracking-tight">{o.code}</span>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <span className={cn("text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-tighter", o.type === '买入' ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600")}>买入</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-bold uppercase tracking-tighter border border-gray-200">{o.orderType}</span>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                        <div className="flex flex-col">
                          <span className="text-[11px] font-bold tabular-nums text-gray-900">{o.price.toFixed(2)}</span>
                          <span className="text-[10px] text-gray-400 tabular-nums">{o.quantity}股</span>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                        <div className="flex flex-col">
                          <span className="text-[11px] font-bold tabular-nums text-gray-900">{o.avgPrice.toFixed(2)}</span>
                          <span className="text-[10px] text-gray-400 tabular-nums">{o.filledQuantity}股</span>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                         <div className="flex flex-col items-center gap-1">
                            <span 
                             className={cn(
                               "text-[10px] px-2 py-0.5 rounded uppercase font-bold tracking-widest border",
                               o.status === OrderStatus.FILLED ? "bg-green-50 text-green-700 border-green-200" :
                               o.status === OrderStatus.REJECTED ? "bg-red-50 text-red-700 border-red-200" : "bg-gray-50 text-gray-500 border-gray-200"
                             )}
                           >
                            {o.status}
                          </span>
                          {o.rejectReason && <span className="text-[9px] text-red-500 max-w-[120px] leading-tight text-center italic">{o.rejectReason}</span>}
                         </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk Tab */}
        <TabsContent value="risk">
          <Card className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
            <CardContent className="p-0">
               <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">检查时间</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">标的</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">信号</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">检查规则</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">结果</TableHead>
                    <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">详细说明</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="text-xs font-mono">
                  {MOCK_RISK_RECORDS.map((r) => (
                    <TableRow key={r.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-[10px] text-gray-400">{r.time}</TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 font-bold text-gray-900">{r.code}</TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                         <span className="text-[10px] px-1 py-0.5 rounded bg-gray-100 text-gray-500 font-bold border border-gray-200">{r.signal}</span>
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-[10px] font-bold uppercase tracking-tight text-gray-600">{r.rule}</TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                        {r.passed ? 
                          <span className="text-[10px] font-bold text-green-600 flex items-center justify-center gap-1 uppercase tracking-tighter"><CheckCircle2 className="w-2.5 h-2.5" /> PASSED</span> : 
                          <span className="text-[10px] font-bold text-red-600 flex items-center justify-center gap-1 uppercase tracking-tighter"><ShieldX className="w-2.5 h-2.5" /> BLOCKED</span>
                        }
                      </TableCell>
                      <TableCell className="px-4 py-3 border-b border-gray-50 text-[11px] text-gray-500 italic">{r.reason}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs">
           <Card className="bg-[#151619] border border-gray-800 rounded-lg shadow-sm overflow-hidden">
            <CardContent className="p-0">
               <div className="p-6 min-h-[500px] font-mono text-[11px] space-y-4">
                  {MOCK_LOGS.concat(MOCK_LOGS).map((log, idx) => (
                    <div key={`${log.id}-${idx}`} className="flex gap-4 items-start group">
                      <span className="text-gray-600 group-hover:text-gray-400 transition-colors shrink-0">[{log.time}]</span>
                      <span className={cn(
                        "font-bold uppercase tracking-widest shrink-0 w-16",
                        log.level === LogLevel.SUCCESS ? "text-green-500" :
                        log.level === LogLevel.ERROR ? "text-red-500" :
                        log.level === LogLevel.WARN ? "text-amber-500" : "text-blue-500"
                      )}>{log.level}</span>
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 bg-white/5 rounded text-gray-400 font-bold tracking-tighter uppercase text-[10px]">@{log.module}</span>
                          <span className="text-white font-bold">{log.event}</span>
                          {log.code && <span className="text-blue-400 font-bold">#{log.code}</span>}
                        </div>
                        <p className="text-gray-500 leading-relaxed max-w-2xl italic">{log.detail}</p>
                      </div>
                    </div>
                  ))}
               </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
