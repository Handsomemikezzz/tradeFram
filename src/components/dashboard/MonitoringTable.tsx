import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { formatTime, MonitoringItemResponse, riskStatusLabel, signalLabel, systemApi } from '@/services/api';

export const MonitoringTable = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<MonitoringItemResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    systemApi.getDashboardMonitoringSummary(4)
      .then((page) => {
        if (cancelled) return;
        setItems(page.items);
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
  }, []);

  return (
    <Card className="lg:col-span-3 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-700">交易监控池 (实时)</h4>
        <button className="text-[10px] px-2 py-1 border border-gray-300 rounded hover:bg-white bg-gray-100 font-bold transition-colors">配置策略</button>
      </div>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
              <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">代码</TableHead>
              <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto">名称</TableHead>
              <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">时间</TableHead>
              <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-center">状态</TableHead>
              <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 italic font-serif h-auto text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="text-xs font-mono">
            {loading && (
              <TableRow><TableCell colSpan={5} className="px-4 py-8 text-center text-gray-400">正在加载监控池...</TableCell></TableRow>
            )}
            {!loading && error && (
              <TableRow><TableCell colSpan={5} className="px-4 py-8 text-center text-red-500">{error}</TableCell></TableRow>
            )}
            {!loading && !error && items.length === 0 && (
              <TableRow><TableCell colSpan={5} className="px-4 py-8 text-center text-gray-400">暂无交易监控股票，请先在研究页加入监控池。</TableCell></TableRow>
            )}
            {!loading && !error && items.map((item) => {
              const statusText = item.latestRiskCheck ? riskStatusLabel(item.latestRiskCheck.status, item.latestRiskCheck.passed) : signalLabel(item.latestSignal?.type);
              return (
                <TableRow key={item.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-gray-600">{item.symbol}</TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 font-sans font-medium text-gray-900">{item.name}</TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-right text-gray-400">{formatTime(item.latestSignal?.generatedAt || item.updatedAt)}</TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                    <span className={cn(
                      "px-1.5 py-0.5 rounded border font-bold text-[9px] uppercase",
                      item.latestRiskCheck?.passed ? "bg-blue-50 text-blue-600 border-blue-100" : "bg-gray-50 text-gray-400 border-gray-200"
                    )}>
                      {statusText}
                    </span>
                  </TableCell>
                  <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                    <button className="text-[10px] font-bold text-blue-600 hover:underline uppercase" onClick={() => navigate(`/research/${item.code}`)}>Detail</button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        <div className="p-3 bg-gray-50 text-[10px] text-gray-400 italic text-right">
          * 所有操作均为模拟下单，数据通过 FastAPI 后端读取
        </div>
      </CardContent>
    </Card>
  );
};
