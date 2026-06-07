/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Loader2, FileSearch } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { STEPS, ResearchStepper } from '@/components/research/ResearchStepper';
import { useNavigate } from 'react-router-dom';
import { formatDateTime, monitoringApi, reportStatusLabel, researchApi, ResearchRecordResponse, ResearchStatsResponse, ResearchTaskResponse, researchStepIndex } from '@/services/api';

const sleep = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms));

export default function Research() {
  const navigate = useNavigate();
  const [stockCode, setStockCode] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [step, setStep] = useState(0);
  const [records, setRecords] = useState<ResearchRecordResponse[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(true);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [stats, setStats] = useState<ResearchStatsResponse | null>(null);

  const loadStats = () => {
    researchApi.getStats()
      .then(setStats)
      .catch(() => setStats(null));
  };

  const loadRecords = () => {
    setRecordsLoading(true);
    researchApi.getRecords({ pageSize: 50 })
      .then((page) => {
        setRecords(page.items);
        setRecordsError(null);
      })
      .catch((err: Error) => setRecordsError(err.message))
      .finally(() => setRecordsLoading(false));
  };

  useEffect(() => {
    loadRecords();
    loadStats();
  }, []);

  const startResearch = async () => {
    if (!stockCode || stockCode.length < 6) {
      toast.error('请输入有效的 6 位 A 股代码');
      return;
    }
    setIsResearching(true);
    setStep(0);

    try {
      const created = await researchApi.createTask({ code: stockCode, source: 'FRONTEND' });
      setStep(Math.min(researchStepIndex(created.currentStep), STEPS.length - 1));
      const latest = await pollResearchTask(created);
      toast.success('研究报告已生成，点击查看！');
      setStockCode('');
      loadRecords();
      loadStats();
      navigate(`/research/${latest.code}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '研究任务创建失败');
    } finally {
      setIsResearching(false);
    }
  };

  const pollResearchTask = async (initialTask: ResearchTaskResponse) => {
    let latest = initialTask;
    for (let attempt = 0; attempt < 300; attempt += 1) {
      if (latest.status === 'COMPLETED') return latest;
      if (latest.status === 'FAILED') {
        throw new Error(latest.errorMessage || 'TradingAgents 研究任务失败');
      }
      await sleep(2000);
      latest = await researchApi.getTask(initialTask.taskId);
      setStep(Math.min(researchStepIndex(latest.currentStep), STEPS.length - 1));
    }
    throw new Error('TradingAgents 研究任务超时，请稍后在研究记录中查看结果');
  };

  const addWatchlist = async (record: ResearchRecordResponse) => {
    try {
      await monitoringApi.addWatchlistItem({ code: record.code, source: 'RESEARCH_RECORD', reportId: record.reportId });
      toast.success('已加入观察池');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入观察池失败');
    }
  };

  const deleteRecord = async (record: ResearchRecordResponse) => {
    if (record.status !== 'FAILED' && record.status !== 'COMPLETED') return;
    const confirmMessage = record.status === 'COMPLETED'
      ? `确认删除 ${record.name}（${record.code}）的已完成研究记录？关联报告将一并删除，此操作不可恢复。`
      : `确认删除 ${record.name}（${record.code}）的失败研究记录？`;
    if (!window.confirm(confirmMessage)) return;
    try {
      await researchApi.deleteTask(record.taskId);
      toast.success('研究记录已删除');
      loadRecords();
      loadStats();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除研究记录失败');
    }
  };

  const addMonitoring = async (record: ResearchRecordResponse) => {
    try {
      await monitoringApi.addMonitoringItem({ code: record.code, enabled: true, source: 'RESEARCH_RECORD', reportId: record.reportId });
      toast.success('已加入交易监控池');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入交易监控池失败');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold tracking-tight">股票深度研究</h2>
        <p className="text-muted-foreground">输入代码，让系统协助您完成公司基本面与技术面深度分析。</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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

            {isResearching && <ResearchStepper step={step} />}
          </CardContent>
        </Card>

        <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <CardHeader>
            <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-700 italic font-serif">研究概况 (研究统计)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500 font-bold uppercase font-mono">本月研究总数</span>
              <span className="text-xl font-bold font-mono text-[#1A1C1E]">{stats?.researchCount ?? records.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500 font-bold uppercase font-mono">成功转化观察池</span>
              <span className="text-xl font-bold font-mono text-blue-600">{stats?.watchlistConvertedCount ?? '-'}</span>
            </div>
            <div className="h-px bg-gray-100" />
            <div className="space-y-3">
              <span className="text-[10px] text-gray-500 font-bold uppercase font-mono tracking-widest leading-none">常用板块</span>
              <div className="flex flex-wrap gap-2 pt-1">
                {(stats?.popularIndustries.length ? stats.popularIndustries : ['白酒', '新能源', '医疗器械', '半导体', '互联网']).map(tag => (
                  <Badge key={tag} variant="secondary" className="text-[9px] bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors border-none uppercase font-bold tracking-tighter">{tag}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

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
                {recordsLoading && <TableRow><TableCell colSpan={5} className="px-4 py-8 text-center text-gray-400">正在加载研究记录...</TableCell></TableRow>}
                {!recordsLoading && recordsError && <TableRow><TableCell colSpan={5} className="px-4 py-8 text-center text-red-500">{recordsError}</TableCell></TableRow>}
                {!recordsLoading && !recordsError && records.length === 0 && <TableRow><TableCell colSpan={5} className="px-4 py-8 text-center text-gray-400">暂无研究记录，请输入股票代码发起 AI 研究。</TableCell></TableRow>}
                {!recordsLoading && !recordsError && records.map((record) => (
                  <TableRow key={record.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                    <TableCell className="px-4 py-3 border-b border-gray-50 font-mono text-[11px] text-gray-600">{record.code}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 font-sans font-medium text-[11px] text-gray-900">{record.name}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-[11px] text-gray-400 font-mono">{formatDateTime(record.researchTime)}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                      <span className={cn(
                        "px-1.5 py-0.5 rounded border font-bold text-[9px] uppercase",
                        record.status === 'COMPLETED'
                          ? "bg-blue-50 text-blue-600 border-blue-100"
                          : record.status === 'FAILED' ? "bg-red-50 text-red-600 border-red-100" : "bg-gray-100 text-gray-400 border-gray-200"
                      )}>
                        {reportStatusLabel(record.status)}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                      <div className="flex justify-end gap-3 text-[10px] font-bold uppercase tracking-widest text-blue-600">
                        <button className="hover:underline" onClick={() => navigate(`/research/${record.code}`)}>查看报告</button>
                        <button className="text-gray-400 hover:text-blue-500" onClick={() => addWatchlist(record)}>加入观察池</button>
                        <button className="text-gray-400 hover:text-orange-500" onClick={() => addMonitoring(record)}>加入交易监控池</button>
                        {(record.status === 'FAILED' || record.status === 'COMPLETED') && (
                          <button className="text-gray-400 hover:text-red-500" onClick={() => deleteRecord(record)}>删除</button>
                        )}
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
