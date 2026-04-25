/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { 
  Search, 
  Loader2, 
  CheckCircle2, 
  History, 
  ArrowRight,
  TrendingUp,
  FileSearch,
  Plus
} from 'lucide-react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { MOCK_RESEARCH_RECORDS } from '@/services/mockData';
import { ReportStatus } from '@/types';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { STEPS, ResearchStepper } from '@/components/research/ResearchStepper';
import { useNavigate } from 'react-router-dom';

export default function Research() {
  const navigate = useNavigate();
  const [stockCode, setStockCode] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [step, setStep] = useState(0);

  const startResearch = () => {
    if (!stockCode || stockCode.length < 6) {
      toast.error('请输入有效的 6 位 A 股代码');
      return;
    }
    
    setIsResearching(true);
    setStep(0);
    
    // Simulate research process
    const interval = setInterval(() => {
      setStep(prev => {
        if (prev >= STEPS.length - 1) {
          clearInterval(interval);
          setTimeout(() => {
            setIsResearching(false);
            setStockCode('');
            toast.success('研究报告已生成，点击查看！');
            navigate('/research/600519'); // Just mock navigation to茅台
          }, 1000);
          return prev;
        }
        return prev + 1;
      });
    }, 1200);
  };

  const handleAction = (action: string) => {
    toast.success(`已加入${action}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold tracking-tight">股票深度研究</h2>
        <p className="text-muted-foreground">输入代码，让系统协助您完成公司基本面与技术面深度分析。</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Research Input */}
        <Card className="lg:col-span-2 bg-white border border-gray-200 rounded-lg shadow-sm">
          <CardHeader>
            <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-700 italic font-serif">发起研究任务</CardTitle>
            <CardDescription className="text-[10px] uppercase text-gray-400 font-mono">SH/SZ/BJ Market Support</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pb-6">
            <div className="flex gap-3">
              <div className="relative flex-1 group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-blue-500 transition-colors" />
                <Input 
                  placeholder="请输入 A 股代码，例如 600519" 
                  value={stockCode}
                  onChange={(e) => setStockCode(e.target.value)}
                  className="pl-10 h-10 bg-gray-50 border-gray-200 focus-visible:ring-blue-500"
                  maxLength={6}
                />
              </div>
              <Button 
                onClick={startResearch} 
                disabled={isResearching}
                className="h-10 px-8 font-bold gap-2 bg-blue-600 hover:bg-blue-700 text-xs uppercase tracking-wider"
              >
                {isResearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSearch className="w-4 h-4" />}
                开始 AI 研究
              </Button>
            </div>

            {isResearching && (
              <ResearchStepper step={step} />
            )}
          </CardContent>
        </Card>

        {/* Stats Summary */}
        <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <CardHeader>
            <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-700 italic font-serif">研究概况 (研究统计)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500 font-bold uppercase font-mono">本月研究总数</span>
              <span className="text-xl font-bold font-mono text-[#1A1C1E]">142</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500 font-bold uppercase font-mono">成功转化观察池</span>
              <span className="text-xl font-bold font-mono text-blue-600">38</span>
            </div>
            <div className="h-px bg-gray-100" />
            <div className="space-y-3">
              <span className="text-[10px] text-gray-500 font-bold uppercase font-mono tracking-widest leading-none">常用板块</span>
              <div className="flex flex-wrap gap-2 pt-1">
                {['白酒', '新能源', '医疗器械', '半导体', '互联网'].map(tag => (
                  <Badge key={tag} variant="secondary" className="text-[9px] bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors border-none uppercase font-bold tracking-tighter">{tag}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Research Table */}
        <Card className="lg:col-span-3 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-700">全库研究记录 (研究记录)</h4>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-7 text-[9px] font-bold uppercase tracking-widest bg-gray-100 border-gray-300">Export CSV</Button>
              <Button variant="outline" size="sm" className="h-7 text-[9px] font-bold uppercase tracking-widest bg-gray-100 border-gray-300">Clean Logs</Button>
            </div>
          </div>
          <CardContent className="p-0">
             <Table>
              <TableHeader>
                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">股票代码</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">股票名称</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">研究时间</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">状态</TableHead>
                  <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MOCK_RESEARCH_RECORDS.map((record) => (
                  <TableRow key={record.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                    <TableCell className="px-4 py-3 border-b border-gray-50 font-mono text-[11px] text-gray-600">{record.code}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 font-sans font-medium text-[11px] text-gray-900">{record.name}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-[11px] text-gray-400 font-mono">{record.researchTime}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                      <span className={cn(
                        "px-1.5 py-0.5 rounded border font-bold text-[9px] uppercase",
                        record.status === ReportStatus.COMPLETED 
                          ? "bg-blue-50 text-blue-600 border-blue-100" 
                          : record.status === ReportStatus.FAILED ? "bg-red-50 text-red-600 border-red-100" : "bg-gray-100 text-gray-400 border-gray-200"
                      )}>
                        {record.status}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                      <div className="flex justify-end gap-3 text-[10px] font-bold uppercase tracking-widest text-blue-600">
                        <button className="hover:underline" onClick={() => navigate(`/research/${record.code}`)}>查看报告</button>
                        <button className="text-gray-400 hover:text-blue-500" onClick={() => handleAction('加入观察池')}>加入观察池</button>
                        <button className="text-gray-400 hover:text-orange-500" onClick={() => handleAction('加入交易监控池')}>加入交易监控池</button>
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
