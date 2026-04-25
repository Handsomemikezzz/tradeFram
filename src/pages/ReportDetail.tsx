/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  ArrowLeft, 
  RefreshCw, 
  Database, 
  TrendingUp, 
  Info, 
  ShieldAlert, 
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Globe,
  Newspaper,
  Clock
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MOCK_STOCKS } from '@/services/mockData';
import { cn } from '@/lib/utils';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner';

const CHART_DATA = [
  { name: '05-13', price: 1610 },
  { name: '05-14', price: 1620 },
  { name: '05-15', price: 1590 },
  { name: '05-16', price: 1630 },
  { name: '05-17', price: 1645 },
  { name: '05-18', price: 1635 },
  { name: '05-19', price: 1650 },
];

export default function ReportDetail() {
  const { code } = useParams();
  const navigate = useNavigate();
  const stock = MOCK_STOCKS[code || '600519'] || MOCK_STOCKS['600519'];

  const isPositive = stock.change >= 0;

  return (
    <div className="space-y-4">
      {/* Header Info */}
      <div className="flex items-end justify-between border-b border-gray-200 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 bg-gray-900 text-white text-[10px] font-bold rounded uppercase tracking-tighter">Symbol: {stock.code}</span>
            <h1 className="text-2xl font-bold tracking-tight text-[#1A1C1E]">{stock.name} 研究报告</h1>
          </div>
          <div className="flex items-center gap-4 text-[10px] text-gray-500 font-bold uppercase tracking-widest">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              生成时间: {stock.updateTime}
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-blue-500" />
              当前价格: <span className="font-mono text-gray-900">{stock.price.toFixed(2)}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-white border-gray-300" onClick={() => toast.success('已加入观察池')}>加入观察池</Button>
          <Button size="sm" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700" onClick={() => toast.success('已加入监控池')}>监控此股</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Real-time Market Card */}
        <Card className="bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden">
          <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
            <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-500 italic font-serif">当前行情 (Real-time)</CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="flex flex-col">
              <span className="text-3xl font-bold font-mono tracking-tighter tabular-nums leading-none">{stock.price.toFixed(2)}</span>
              <div className={cn("flex items-center text-[11px] font-bold mt-2", isPositive ? "text-red-600" : "text-green-600")}>
                {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                <span>{isPositive ? '+' : ''}{stock.change.toFixed(2)} ({isPositive ? '+' : ''}{stock.changePercent.toFixed(2)}%)</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-50 mt-2">
              <div className="flex flex-col">
                <span className="text-[9px] text-gray-400 uppercase font-bold font-mono mb-1">成交量 (Vol)</span>
                <span className="text-xs font-bold tabular-nums">{(stock.volume / 10000).toFixed(2)}w</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-gray-400 uppercase font-bold font-mono mb-1">成交额 (Val)</span>
                <span className="text-xs font-bold tabular-nums">{(stock.amount / 100000000).toFixed(2)}亿</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Chart Area */}
        <Card className="lg:col-span-3 bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden flex flex-col">
          <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100 flex justify-between items-center h-auto py-3">
             <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-gray-500 flex items-center gap-2 italic font-serif">
                <TrendingUp className="w-3.5 h-3.5 text-blue-500" /> 近 7 日走势预览 (Trend)
             </CardTitle>
          </CardHeader>
          <CardContent className="p-4 h-[160px]">
             <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={CHART_DATA}>
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
                  <Area 
                    type="monotone" 
                    dataKey="price" 
                    stroke={isPositive ? "#ef4444" : "#22c55e"} 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorPrice)" 
                  />
                </AreaChart>
             </ResponsiveContainer>
          </CardContent>
        </Card>

        <div className="lg:col-span-4 mt-2">
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
                    <p className="text-[11px] text-gray-700 leading-relaxed font-medium">
                      {stock.name}作为{stock.industry}板块的龙头企业，展现了极强的定价权和市场地位。当前估值倍数 PE 为 {stock.pe}x，处于历史中位区间。近期的财务数据显示营收稳健增长，利润率保持行业领先水平。
                    </p>
                    <div className="bg-blue-50 border border-blue-100 p-3 rounded italic text-blue-900 border-l-4 border-l-blue-500">
                      <h4 className="text-[10px] font-bold mb-2 flex items-center gap-1 uppercase tracking-tight">Key Insights:</h4>
                      <ul className="text-[10px] space-y-1.5 list-disc list-inside">
                        <li>品牌护城河：深厚历史底蕴，社交属性带来的消费粘性。</li>
                        <li>直销占比提升：渠道改革成效显著，利润率进一步优化。</li>
                        <li>产能扩张：公司正在推进产线扩充计划，支撑未来 2-3 年增长潜力。</li>
                      </ul>
                    </div>
                    {/* New Fields */}
                    <div className="grid grid-cols-2 gap-2 mt-4 text-[10px]">
                      <div className="bg-gray-100 p-2 rounded">
                        <span className="text-gray-500">值得继续研究:</span>
                        <span className="font-bold ml-1 text-green-700">是</span>
                      </div>
                      <div className="bg-gray-100 p-2 rounded">
                        <span className="text-gray-500">AI 置信度:</span>
                        <span className="font-bold ml-1 text-blue-700">92%</span>
                      </div>
                      <div className="bg-gray-100 p-2 rounded">
                        <span className="text-gray-500">数据完整度:</span>
                        <span className="font-bold ml-1 text-blue-700">98%</span>
                      </div>
                    </div>
                    <div className="text-[9px] text-gray-400 mt-2 italic">
                      AI 局限性说明：本报告由算法模型生成，仅供参考，不构成投资建议。
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-white border border-gray-200 shadow-sm rounded-lg">
                  <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
                    <CardTitle className="text-[10px] font-bold flex items-center gap-2 text-red-600 uppercase tracking-wider italic font-serif">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      风险提示 (Warnings)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {[
                      { title: '政策风险', desc: '行业监管政策收紧可能影响估值水平。' },
                      { title: '消费疲软', desc: '经济波动导致的终端消费力下降风险。' },
                      { title: '产能瓶颈', desc: '项目扩建进度如不及预期可能压制业绩增速。' }
                    ].map(r => (
                      <div key={r.title} className="flex gap-3 border-b border-gray-50 pb-2 last:border-0 last:pb-0">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0" />
                        <div>
                          <h5 className="text-[11px] font-bold text-gray-900">{r.title}</h5>
                          <p className="text-[10px] text-gray-500 font-medium">{r.desc}</p>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="financial">
              <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader>
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-indigo-500" />
                    财务摘要 (12-Month Trailing)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
                    {[
                      { label: '营业收入', value: stock.revenue },
                      { label: '净利润', value: stock.profit },
                      { label: '毛利率', value: `${stock.grossMargin}%` },
                      { label: '净利率', value: `${stock.netMargin}%` },
                      { label: 'ROE', value: `${stock.roe}%` },
                      { label: '静态市盈率', value: `${stock.pe}x` }
                    ].map(item => (
                      <div key={item.label} className="flex flex-col group">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground mb-1 group-hover:text-primary transition-colors">{item.label}</span>
                        <span className="text-lg font-bold tracking-tight">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="business">
               <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader>
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <Globe className="w-5 h-5 text-blue-500" />
                    主营构成分析
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-bold">茅台酒</span>
                      <span className="font-mono">88%</span>
                    </div>
                    <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                      <div className="h-full bg-red-600" style={{ width: '88%' }} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-bold">系列酒</span>
                      <span className="font-mono">11.5%</span>
                    </div>
                    <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                      <div className="h-full bg-orange-500" style={{ width: '11.5%' }} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-bold">其他业务</span>
                      <span className="font-mono">0.5%</span>
                    </div>
                    <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                      <div className="h-full bg-zinc-400" style={{ width: '0.5%' }} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="news">
               <Card className="border-none shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]">
                <CardHeader>
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <Newspaper className="w-5 h-5 text-slate-600" />
                    近期相关咨讯
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {[
                    { title: '贵州茅台：关于分红派息的公告', date: '2024-05-18', type: '公告' },
                    { title: '多家券商发布深度研究报告，看好公司渠道改革潜力', date: '2024-05-15', type: '动态' },
                    { title: '公司 2024 年一季度生产经营数据简报', date: '2024-05-10', type: '财务' }
                  ].map(n => (
                    <div key={n.title} className="flex items-center justify-between p-3 border rounded-xl hover:bg-zinc-50 cursor-pointer transition-colors group">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="text-[10px] px-1.5 h-5 bg-zinc-50 group-hover:bg-white">{n.type}</Badge>
                        <span className="text-xs font-bold">{n.title}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground font-mono">{n.date}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
        
        {/* Data Footer */}
        <div className="lg:col-span-4 border-t pt-6 flex items-center justify-between text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
           <div className="flex items-center gap-4">
             <div className="flex items-center gap-1.5">
               <Database className="w-3 h-3" />
               <span>数据源：Tushare / AkShare API</span>
             </div>
             <div className="flex items-center gap-1.5">
               <TrendingUp className="w-3 h-3" />
               <span>更新频率：10min/次</span>
             </div>
           </div>
           <div className="flex items-center gap-1.5">
             <ShieldAlert className="w-3 h-3" />
             <span>研究基期：2024-Q1</span>
           </div>
        </div>
      </div>
    </div>
  );
}
