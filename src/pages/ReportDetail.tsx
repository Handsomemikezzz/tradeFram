/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowUpRight, ArrowDownRight, BarChart3, Clock, Database, Globe, Newspaper, RefreshCw, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner';
import { dataApi, formatDateTime, monitoringApi, newsTypeLabel, researchApi, ResearchReportResponse, StockDataStatusResponse } from '@/services/api';

export default function ReportDetail() {
  const { code } = useParams();
  const [report, setReport] = useState<ResearchReportResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<StockDataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    let cancelled = false;
    setLoading(true);
    researchApi.getReportByCode(code)
      .then(async (data) => {
        if (cancelled) return;
        setReport(data);
        try {
          const status = await dataApi.getStockStatus(data.code, data.dataMeta.provider);
          if (!cancelled) setDataStatus(status);
        } catch {
          if (!cancelled) setDataStatus(null);
        }
        setError(null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  const addWatchlist = async () => {
    if (!report) return;
    try {
      await monitoringApi.addWatchlistItem({ code: report.code, source: 'RESEARCH_REPORT', reportId: report.reportId });
      toast.success('已加入观察池');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入观察池失败');
    }
  };

  const addMonitoring = async () => {
    if (!report) return;
    try {
      await monitoringApi.addMonitoringItem({ code: report.code, enabled: true, source: 'RESEARCH_REPORT', reportId: report.reportId });
      toast.success('已加入监控池');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入监控池失败');
    }
  };

  const refreshData = async () => {
    if (!report) return;
    setRefreshing(true);
    try {
      await dataApi.refreshStock(report.code, report.dataMeta.provider);
      const [nextReport, nextStatus] = await Promise.all([
        researchApi.getReportByCode(report.code),
        dataApi.getStockStatus(report.code, report.dataMeta.provider),
      ]);
      setReport(nextReport);
      setDataStatus(nextStatus);
      toast.success('数据刷新完成');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '数据刷新失败，已保留本地缓存');
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-400">正在加载研究报告...</div>;
  }

  if (error || !report) {
    return <div className="p-8 text-center text-red-500">{error || '研究报告不存在'}</div>;
  }

  const isPositive = report.quote.change >= 0;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between border-b border-gray-200 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 bg-gray-900 text-white text-[10px] font-bold rounded uppercase tracking-tighter">Symbol: {report.symbol}</span>
            <h1 className="text-2xl font-bold tracking-tight text-[#1A1C1E]">{report.name} 研究报告</h1>
          </div>
          <div className="flex items-center gap-4 text-[10px] text-gray-500 font-bold uppercase tracking-widest">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              生成时间: {formatDateTime(report.generatedAt)}
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-blue-500" />
              当前价格: <span className="font-mono text-gray-900">{report.quote.price.toFixed(2)}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={refreshData} disabled={refreshing}>
            <RefreshCw className={cn('w-3 h-3 mr-1', refreshing && 'animate-spin')} />刷新数据
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={addWatchlist}>加入观察池</Button>
          <Button size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700" onClick={addMonitoring}>监控此股</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Card className="bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden">
          <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
            <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-500 italic font-serif">当前行情 (Real-time)</CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="flex flex-col">
              <span className="text-3xl font-bold font-mono tracking-tighter tabular-nums leading-none">{report.quote.price.toFixed(2)}</span>
              <div className={cn("flex items-center text-[11px] font-bold mt-2", isPositive ? "text-red-600" : "text-green-600")}>
                {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                <span>{isPositive ? '+' : ''}{report.quote.change.toFixed(2)} ({isPositive ? '+' : ''}{report.quote.changePercent.toFixed(2)}%)</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-50 mt-2">
              <div className="flex flex-col">
                <span className="text-[9px] text-gray-400 uppercase font-bold font-mono mb-1">成交量 (Vol)</span>
                <span className="text-xs font-bold tabular-nums">{(report.quote.volume / 10000).toFixed(2)}w</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-gray-400 uppercase font-bold font-mono mb-1">成交额 (Val)</span>
                <span className="text-xs font-bold tabular-nums">{(report.quote.amount / 100000000).toFixed(2)}亿</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3 bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden flex flex-col">
          <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100 flex justify-between items-center h-auto">
             <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-500 flex items-center gap-2 italic font-serif">
                <TrendingUp className="w-3.5 h-3.5 text-blue-500" /> 近 7 日走势预览 (Trend)
             </CardTitle>
          </CardHeader>
          <CardContent className="p-4 h-[160px]">
             <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={report.trend.map((item) => ({ name: item.date.slice(5), price: item.price }))}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={isPositive ? "#ef4444" : "#22c55e"} stopOpacity={0.1}/>
                      <stop offset="95%" stopColor={isPositive ? "#ef4444" : "#22c55e"} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f1f1" />
                  <XAxis dataKey="name" hide />
                  <YAxis hide domain={['dataMin - 10', 'dataMax + 10']} />
                  <Tooltip />
                  <Area type="monotone" dataKey="price" stroke={isPositive ? "#ef4444" : "#22c55e"} strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
                </AreaChart>
             </ResponsiveContainer>
          </CardContent>
        </Card>

        <div className="lg:col-span-4 mt-2">
          <Card className="border border-blue-100 bg-blue-50/40 shadow-sm rounded-lg mb-4">
            <CardContent className="p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 text-[10px]">
              <div><div className="text-gray-500 font-bold uppercase">Provider</div><div className="font-mono text-gray-900">{dataStatus?.provider || report.dataMeta.provider}</div></div>
              <div><div className="text-gray-500 font-bold uppercase">数据更新时间</div><div className="font-mono text-gray-900">{formatDateTime(dataStatus?.lastFetchedAt || report.dataUpdatedAt)}</div></div>
              <div><div className="text-gray-500 font-bold uppercase">完整度</div><div className="font-mono text-gray-900">{Math.round((dataStatus?.dataCompleteness ?? report.dataMeta.dataCompleteness) * 100)}%</div></div>
              <div><div className="text-gray-500 font-bold uppercase">缓存命中</div><div className="font-mono text-gray-900">{(dataStatus?.cacheHit ?? report.dataMeta.usedCache) ? '是' : '否'}</div></div>
              <div><div className="text-gray-500 font-bold uppercase">过期缓存</div><div className={cn('font-mono', (dataStatus?.dataStale ?? report.dataMeta.dataStale) ? 'text-orange-600' : 'text-gray-900')}>{(dataStatus?.dataStale ?? report.dataMeta.dataStale) ? '是' : '否'}</div></div>
              <div><div className="text-gray-500 font-bold uppercase">日线数量</div><div className="font-mono text-gray-900">{dataStatus?.priceBarCount ?? '-'}</div></div>
              <div><div className="text-gray-500 font-bold uppercase">最近错误</div><div className="font-medium text-red-600 truncate" title={dataStatus?.lastError || report.dataMeta.lastError || undefined}>{dataStatus?.lastError || report.dataMeta.lastError || '无'}</div></div>
            </CardContent>
          </Card>
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList className="bg-white border border-gray-200 rounded-lg p-1 h-auto inline-flex shadow-sm">
              <TabsTrigger value="overview" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest data-[state=active]:bg-gray-100 border-none">结论摘要</TabsTrigger>
              <TabsTrigger value="business" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest data-[state=active]:bg-gray-100 border-none">主营业务</TabsTrigger>
              <TabsTrigger value="financial" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest data-[state=active]:bg-gray-100 border-none">财务概览</TabsTrigger>
              <TabsTrigger value="news" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest data-[state=active]:bg-gray-100 border-none">新闻公告</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-white border border-gray-200 shadow-sm rounded-lg">
                  <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
                    <CardTitle className="text-[10px] font-bold flex items-center gap-2 uppercase tracking-wider italic font-serif">
                      <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                      AI 核心结论 (Abstract)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-4">
                    <p className="text-[11px] text-gray-700 leading-relaxed font-medium">{report.report.overview}</p>
                    <div className="bg-blue-50 border border-blue-100 p-3 rounded italic text-blue-900 border-l-4 border-l-blue-500">
                      <h4 className="text-[10px] font-bold mb-2 flex items-center gap-1 uppercase tracking-tight">Key Insights:</h4>
                      <ul className="text-[10px] space-y-1.5 list-disc list-inside">
                        {report.report.keyInsights.map((insight) => <li key={insight}>{insight}</li>)}
                      </ul>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-4 text-[10px]">
                      <div className="bg-gray-100 p-2 rounded"><span className="text-gray-500">值得继续研究:</span><span className="font-bold ml-1 text-green-700">{report.report.worthFurtherResearch ? '是' : '否'}</span></div>
                      <div className="bg-gray-100 p-2 rounded"><span className="text-gray-500">AI 置信度:</span><span className="font-bold ml-1 text-blue-700">{Math.round(report.report.aiConfidence * 100)}%</span></div>
                      <div className="bg-gray-100 p-2 rounded"><span className="text-gray-500">数据完整度:</span><span className="font-bold ml-1 text-blue-700">{Math.round(report.report.dataCompleteness * 100)}%</span></div>
                    </div>
                    <div className="text-[9px] text-gray-400 mt-2 italic">AI 局限性说明：{report.report.aiDisclaimer}</div>
                  </CardContent>
                </Card>

                <Card className="bg-white border border-gray-200 shadow-sm rounded-lg">
                  <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
                    <CardTitle className="text-[10px] font-bold flex items-center gap-2 text-red-600 uppercase tracking-wider italic font-serif">
                      <ShieldAlert className="w-3.5 h-3.5" /> 风险提示 (Warnings)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {report.report.risks.length === 0 && <div className="text-[11px] text-gray-400">暂无风险提示</div>}
                    {report.report.risks.map(r => (
                      <div key={r.title} className="flex gap-3 border-b border-gray-50 pb-2 last:border-0 last:pb-0">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0" />
                        <div><h5 className="text-[11px] font-bold text-gray-900">{r.title}</h5><p className="text-[10px] text-gray-500 font-medium">{r.description}</p></div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="financial">
              <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader><CardTitle className="text-base font-bold flex items-center gap-2"><BarChart3 className="w-5 h-5 text-indigo-500" />财务摘要 (12-Month Trailing)</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
                    {[
                      { label: '营业收入', value: report.financialSnapshot.revenue },
                      { label: '净利润', value: report.financialSnapshot.profit },
                      { label: '毛利率', value: `${report.financialSnapshot.grossMargin}%` },
                      { label: '净利率', value: `${report.financialSnapshot.netMargin}%` },
                      { label: 'ROE', value: `${report.financialSnapshot.roe}%` },
                      { label: '静态市盈率', value: `${report.financialSnapshot.pe}x` }
                    ].map(item => <div key={item.label} className="flex flex-col group"><span className="text-[10px] uppercase font-bold text-muted-foreground mb-1 group-hover:text-primary transition-colors">{item.label}</span><span className="text-lg font-bold tracking-tight">{item.value}</span></div>)}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="business">
               <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader><CardTitle className="text-base font-bold flex items-center gap-2"><Globe className="w-5 h-5 text-blue-500" />主营构成分析</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  {report.report.businessSegments.map((segment) => (
                    <div className="space-y-2" key={segment.name}>
                      <div className="flex justify-between text-xs mb-1"><span className="font-bold">{segment.name}</span><span className="font-mono">{segment.percent}%</span></div>
                      <div className="h-2 bg-zinc-100 rounded-full overflow-hidden"><div className="h-full bg-red-600" style={{ width: `${segment.percent}%` }} /></div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="news">
               <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader><CardTitle className="text-base font-bold flex items-center gap-2"><Newspaper className="w-5 h-5 text-slate-600" />近期相关咨讯</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  {report.report.newsItems.map(n => (
                    <div key={n.id} className="flex items-center justify-between p-3 border rounded-xl hover:bg-zinc-50 cursor-pointer transition-colors group">
                      <div className="flex items-center gap-3"><Badge variant="outline" className="text-[10px] px-1.5 h-5 bg-zinc-50 group-hover:bg-white">{newsTypeLabel(n.type)}</Badge><span className="text-xs font-bold">{n.title}</span></div>
                      <span className="text-[10px] text-muted-foreground font-mono">{n.date}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
        
        <div className="lg:col-span-4 border-t pt-6 flex items-center justify-between text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
           <div className="flex items-center gap-4">
             <div className="flex items-center gap-1.5"><Database className="w-3 h-3" /><span>Provider：{report.dataMeta.provider}</span></div>
             <div className="flex items-center gap-1.5"><Database className="w-3 h-3" /><span>数据更新时间：{formatDateTime(report.dataUpdatedAt)}</span></div>
             <div className="flex items-center gap-1.5"><Database className="w-3 h-3" /><span>缓存：{report.dataMeta.usedCache ? (report.dataMeta.dataStale ? '使用过期缓存' : '命中缓存') : '实时刷新'}</span></div>
             <div className="flex items-center gap-1.5"><TrendingUp className="w-3 h-3" /><span>更新频率：{report.updateFrequency}/次</span></div>
           </div>
           <div className="flex items-center gap-1.5"><ShieldAlert className="w-3 h-3" /><span>研究基期：{report.researchBasePeriod}</span></div>
        </div>
      </div>
    </div>
  );
}
