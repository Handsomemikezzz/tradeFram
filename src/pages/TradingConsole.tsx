/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { 
  Play, 
  RotateCcw, 
  Activity, 
  Clock,
  Zap,
  History
} from 'lucide-react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { MOCK_MONITORING_POOL } from '@/services/mockData';
import { SignalType } from '@/types';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { RiskStatusCard } from '@/components/trading/RiskStatusCard';
import { TraceStepper } from '@/components/trading/TraceStepper';

export default function TradingConsole() {
  const [isBotActive, setIsBotActive] = useState(false);
  const [isRunningCheck, setIsRunningCheck] = useState(false);

  const runTradeCheck = () => {
    setIsRunningCheck(true);
    toast.info('正在扫描行情并执行自动交易检查...');
    
    setTimeout(() => {
      setIsRunningCheck(false);
      toast.success('检查报告已生成', {
        description: (
          <div className="text-[10px] space-y-1 mt-2">
            <p>本次扫描股票: 120 只</p>
            <p>生成有效信号: 3 条</p>
            <p>风控检查通过: 2 条</p>
            <p>风控拦截拦截: 1 条</p>
            <p>创建模拟订单: 2 笔</p>
            <p>模拟成交: 1 笔</p>
            <p className="font-bold">耗时: 1.2s</p>
          </div>
        )
      });
    }, 2000);
  };

  return (
    <div className="space-y-6">
      {/* Console Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-[#1A1C1E]">
            自动交易控制台
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] font-bold rounded uppercase tracking-tighter">Paper Trading Only</span>
          </h2>
          <p className="text-gray-500 text-xs font-medium uppercase tracking-widest mt-1">审计与执行界面</p>
        </div>
        
        <div className="flex items-center gap-3 bg-white p-2 rounded-lg border border-gray-200 shadow-sm">
           <div className="flex items-center gap-2 px-3 border-r border-gray-100">
             <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">模拟交易系统开关</span>
             <Switch 
               checked={isBotActive} 
               onCheckedChange={(checked) => {
                 setIsBotActive(checked);
                 toast(checked ? '系统已启动' : '系统已停止', {
                   description: checked ? '交易引擎已进入自动轮询状态' : '已断开与模拟下单服务的连接'
                 });
               }} 
               className="data-[state=checked]:bg-blue-600"
             />
           </div>
           <Button 
            size="sm" 
            variant="ghost" 
            className="gap-2 font-bold text-[10px] uppercase tracking-widest hover:bg-gray-100" 
            disabled={isRunningCheck}
            onClick={runTradeCheck}
           >
             {isRunningCheck ? <RotateCcw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
             手动巡检一次
           </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Risk Status Cards */}
        <div className="lg:col-span-1 space-y-4">
          <RiskStatusCard />
          <TraceStepper />
        </div>

        {/* Monitoring Pool Table */}
        <Card className="lg:col-span-3 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
            <div>
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-700 italic font-serif">交易监控池 (实时交易审计)</h4>
              <p className="text-[9px] text-gray-400 font-mono mt-0.5">主动策略监控</p>
            </div>
            <div className="flex gap-2 items-center">
               <span className="text-[9px] font-mono text-gray-400 mr-2 flex items-center gap-1 uppercase no-wrap">
                 <Clock className="w-2.5 h-2.5" />
                 Refresh: 15:00:25
               </span>
               <Button size="sm" variant="outline" className="h-7 text-[9px] font-bold uppercase tracking-widest bg-gray-100 border-gray-300">
                 <Zap className="w-2.5 h-2.5 mr-1" /> 批量启用
               </Button>
            </div>
          </div>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                  <TableHead className="w-12 px-4"></TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">股票代码</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">策略名称</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">最新信号</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">风控检测</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">最近订单</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="text-xs font-mono">
                {MOCK_MONITORING_POOL.map((item) => (
                  <TableRow key={item.code} className={cn("hover:bg-blue-50 transition-colors border-gray-50", !item.enabled && "opacity-60")}>
                    <TableCell className="px-4">
                      <Switch checked={item.enabled} size="sm" className="scale-75 data-[state=checked]:bg-blue-600" />
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50">
                      <div className="flex flex-col">
                        <span className="text-[11px] font-bold text-gray-900">{item.name}</span>
                        <span className="text-[10px] text-gray-400 font-mono tracking-tight">{item.code}</span>
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50">
                      <Badge variant="outline" className="text-[9px] bg-gray-50 border-gray-200 text-gray-500 font-bold uppercase tracking-tighter">{item.strategy}</Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                       <TooltipProvider>
                         <Tooltip>
                           <TooltipTrigger>
                              <Badge 
                                className={cn(
                                  "text-[10px] px-1.5 py-0.5 rounded border font-bold uppercase tracking-widest cursor-help",
                                  item.lastSignal === SignalType.BUY ? "bg-red-50 text-red-600 border-red-100" :
                                  item.lastSignal === SignalType.SELL ? "bg-green-50 text-green-600 border-green-100" :
                                  "bg-gray-100 text-gray-400 border-gray-200"
                                )}
                              >
                                {item.lastSignal}
                              </Badge>
                           </TooltipTrigger>
                           <TooltipContent className="text-[10px] max-w-[200px]">{item.signalReason}</TooltipContent>
                         </Tooltip>
                       </TooltipProvider>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50">
                      <div className="flex items-center gap-1.5">
                        <div className={cn("w-1.5 h-1.5 rounded-full", item.riskStatus === '通过' ? "bg-green-500" : "bg-orange-500")} />
                        <span className="text-[11px] font-medium text-gray-600">{item.riskStatus}</span>
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right text-[10px] font-mono text-gray-400">{item.lastOrder}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-gray-400 hover:text-blue-500"><Activity className="w-3.5 h-3.5" /></Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-gray-400 hover:text-red-500"><History className="w-3.5 h-3.5" /></Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
