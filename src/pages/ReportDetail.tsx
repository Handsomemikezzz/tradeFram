/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, ArrowUpRight, ArrowDownRight, BarChart3, Clock, Copy, Database, Download, Globe, Newspaper, RefreshCw, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { dataApi, formatDateTime, monitoringApi, newsTypeLabel, researchApi, ResearchReportResponse, StockDataStatusResponse } from '@/services/api';
import { copyResearchReportMarkdown, downloadResearchReportMarkdown } from '@/lib/researchReportExport';

const ratingTone = (rating?: string) => {
  const normalized = (rating || '').toLowerCase();
  if (['buy', 'overweight'].includes(normalized)) return 'text-red-700 bg-red-50 border-red-100';
  if (['sell', 'underweight'].includes(normalized)) return 'text-green-700 bg-green-50 border-green-100';
  return 'text-blue-700 bg-blue-50 border-blue-100';
};

const agentSectionLabels: Array<[keyof NonNullable<ResearchReportResponse['tradingAgentsSections']>, string]> = [
  ['market', 'Market Analyst'],
  ['sentiment', 'Sentiment Analyst'],
  ['news', 'News Analyst'],
  ['fundamentals', 'Fundamentals Analyst'],
  ['researchTeam', 'Research Team'],
  ['trader', 'Trader'],
  ['portfolioManager', 'Portfolio Manager'],
];

const MarkdownBlock = ({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      h1: ({ children }) => <h1 className="mt-2 mb-4 text-xl font-black tracking-tight text-gray-950">{children}</h1>,
      h2: ({ children }) => <h2 className="mt-6 mb-3 border-b border-gray-100 pb-2 text-base font-black text-gray-900">{children}</h2>,
      h3: ({ children }) => <h3 className="mt-5 mb-2 text-sm font-bold text-gray-900">{children}</h3>,
      h4: ({ children }) => <h4 className="mt-4 mb-2 text-xs font-bold uppercase tracking-wider text-gray-600">{children}</h4>,
      p: ({ children }) => <p className="my-3 text-[12px] leading-6 text-gray-700">{children}</p>,
      strong: ({ children }) => <strong className="font-black text-gray-900">{children}</strong>,
      ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5 text-[12px] leading-6 text-gray-700">{children}</ul>,
      ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-5 text-[12px] leading-6 text-gray-700">{children}</ol>,
      li: ({ children }) => <li className="pl-1">{children}</li>,
      hr: () => <hr className="my-6 border-gray-100" />,
      table: ({ children }) => (
        <div className="my-4 overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full border-collapse text-[11px]">{children}</table>
        </div>
      ),
      thead: ({ children }) => <thead className="bg-gray-50 text-gray-600">{children}</thead>,
      th: ({ children }) => <th className="border-b border-gray-200 px-3 py-2 text-left font-black">{children}</th>,
      td: ({ children }) => <td className="border-b border-gray-100 px-3 py-2 align-top text-gray-700">{children}</td>,
      code: ({ children }) => <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[11px] text-gray-900">{children}</code>,
      pre: ({ children }) => <pre className="my-4 overflow-x-auto rounded-lg bg-gray-950 p-4 text-[11px] leading-5 text-gray-100">{children}</pre>,
      blockquote: ({ children }) => <blockquote className="my-4 border-l-4 border-blue-200 bg-blue-50/50 px-4 py-2 text-gray-700">{children}</blockquote>,
    }}
  >
    {content}
  </ReactMarkdown>
);

export default function ReportDetail() {
  const navigate = useNavigate();
  const { code } = useParams();
  const [report, setReport] = useState<ResearchReportResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<StockDataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
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

  const copyReport = async () => {
    if (!report) return;
    setExporting(true);
    try {
      await copyResearchReportMarkdown(report);
      toast.success('研究报告已复制到剪贴板');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '复制研究报告失败');
    } finally {
      setExporting(false);
    }
  };

  const exportReport = () => {
    if (!report) return;
    try {
      downloadResearchReportMarkdown(report);
      toast.success('研究报告已导出为 Markdown 文件');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '导出研究报告失败');
    }
  };

  const goBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate('/research');
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={goBack}>
          <ArrowLeft className="w-3 h-3 mr-1" />返回
        </Button>
        <div className="p-8 text-center text-gray-400">正在加载研究报告...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={goBack}>
          <ArrowLeft className="w-3 h-3 mr-1" />返回
        </Button>
        <div className="p-8 text-center text-red-500">{error || '研究报告不存在'}</div>
      </div>
    );
  }

  const isPositive = report.quote.change >= 0;
  const aiConfidenceLabel = report.report.aiConfidence === null ? '暂无' : `${Math.round(report.report.aiConfidence * 100)}%`;
  const decision = report.tradingAgentsDecision;
  const agentSections = agentSectionLabels
    .map(([key, label]) => ({ key, label, content: report.tradingAgentsSections?.[key] || '' }))
    .filter(section => section.content.trim().length > 0);
  const financialItems = report.financialSnapshot
    ? [
        { label: '营业收入', value: report.financialSnapshot.revenue },
        { label: '净利润', value: report.financialSnapshot.profit },
        { label: '毛利率', value: `${report.financialSnapshot.grossMargin}%` },
        { label: '净利率', value: `${report.financialSnapshot.netMargin}%` },
        { label: 'ROE', value: `${report.financialSnapshot.roe}%` },
        { label: '静态市盈率', value: `${report.financialSnapshot.pe}x` },
      ]
    : [];

  return (
    <div className="space-y-4">
      <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={goBack}>
        <ArrowLeft className="w-3 h-3 mr-1" />返回
      </Button>
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
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={copyReport} disabled={exporting}>
            <Copy className="w-3 h-3 mr-1" />复制报告
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={exportReport}>
            <Download className="w-3 h-3 mr-1" />导出 Markdown
          </Button>
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
             {report.trend.length > 0 ? <ResponsiveContainer width="100%" height="100%">
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
             </ResponsiveContainer> : <div className="flex h-full items-center justify-center text-[11px] text-gray-400">暂无可用日线走势</div>}
          </CardContent>
        </Card>

        {decision && (
          <Card className="lg:col-span-4 border border-blue-100 bg-white shadow-sm rounded-lg overflow-hidden">
            <CardHeader className="px-4 py-3 bg-blue-50/60 border-b border-blue-100">
              <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-blue-700 flex items-center gap-2 italic font-serif">
                <Sparkles className="w-3.5 h-3.5" /> TradingAgents Decision
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className={cn('rounded border p-3', ratingTone(decision.rating))}>
                  <div className="text-[9px] font-bold uppercase tracking-widest">Rating</div>
                  <div className="text-lg font-black font-mono mt-1">{decision.rating}</div>
                </div>
                <div className="rounded border border-gray-100 bg-gray-50 p-3">
                  <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest">Price Target</div>
                  <div className="text-lg font-black font-mono mt-1">{decision.priceTarget || '-'}</div>
                </div>
                <div className="rounded border border-gray-100 bg-gray-50 p-3">
                  <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest">Time Horizon</div>
                  <div className="text-lg font-black font-mono mt-1">{decision.timeHorizon || '-'}</div>
                </div>
                <div className="rounded border border-gray-100 bg-gray-50 p-3">
                  <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest">Yahoo Ticker</div>
                  <div className="text-lg font-black font-mono mt-1">{decision.yahooTicker}</div>
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Executive Summary</div>
                  <p className="text-[12px] leading-relaxed text-gray-800 whitespace-pre-wrap">{decision.executiveSummary}</p>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Investment Thesis</div>
                  <p className="text-[12px] leading-relaxed text-gray-800 whitespace-pre-wrap">{decision.investmentThesis || '暂无完整投资论点。'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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
              <TabsTrigger value="agents" className="text-[10px] font-bold px-6 h-8 uppercase tracking-widest data-[state=active]:bg-gray-100 border-none">Agent 辩论</TabsTrigger>
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
                      <div className="bg-gray-100 p-2 rounded"><span className="text-gray-500">AI 置信度:</span><span className="font-bold ml-1 text-blue-700">{aiConfidenceLabel}</span></div>
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
                  {financialItems.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
                      {financialItems.map(item => <div key={item.label} className="flex flex-col group"><span className="text-[10px] uppercase font-bold text-muted-foreground mb-1 group-hover:text-primary transition-colors">{item.label}</span><span className="text-lg font-bold tracking-tight">{item.value}</span></div>)}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-400">AkShare 当前未返回可用财务摘要。</div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="business">
               <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader><CardTitle className="text-base font-bold flex items-center gap-2"><Globe className="w-5 h-5 text-blue-500" />主营构成分析</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  {report.report.businessSegments.length === 0 && <div className="text-sm text-gray-400">暂无真实主营构成数据。</div>}
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
                  {report.report.newsItems.length === 0 && <div className="text-sm text-gray-400">暂无真实新闻公告数据。</div>}
                  {report.report.newsItems.map(n => (
                    <div key={n.id} className="flex items-center justify-between p-3 border rounded-xl hover:bg-zinc-50 cursor-pointer transition-colors group">
                      <div className="flex items-center gap-3"><Badge variant="outline" className="text-[10px] px-1.5 h-5 bg-zinc-50 group-hover:bg-white">{newsTypeLabel(n.type)}</Badge><span className="text-xs font-bold">{n.title}</span></div>
                      <span className="text-[10px] text-muted-foreground font-mono">{n.date}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="agents" className="space-y-4">
              {agentSections.length === 0 && (
                <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                  <CardContent className="p-6 text-sm text-gray-400">暂无 TradingAgents 原始分析内容。</CardContent>
                </Card>
              )}
              {agentSections.map(section => (
                <Card key={section.key} className="border border-gray-200 shadow-sm rounded-lg overflow-hidden">
                  <CardHeader className="px-4 py-3 bg-gray-50/70 border-b border-gray-100">
                    <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-600 italic font-serif">{section.label}</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <MarkdownBlock content={section.content} />
                  </CardContent>
                </Card>
              ))}
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
