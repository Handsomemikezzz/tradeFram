import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { MOCK_RESEARCH_RECORDS } from '@/services/mockData';
import { cn } from '@/lib/utils';

export const MonitoringTable = () => {
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
                {MOCK_RESEARCH_RECORDS.slice(0, 4).map((record) => (
                  <TableRow key={record.id} className="hover:bg-blue-50 transition-colors border-gray-50">
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-gray-600">{record.code}.SH</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 font-sans font-medium text-gray-900">{record.name}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right text-gray-400">{record.researchTime.split(' ')[1]}</TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-center">
                      <span className={cn(
                        "px-1.5 py-0.5 rounded border font-bold text-[9px] uppercase",
                        record.status === '已完成' 
                          ? "bg-blue-50 text-blue-600 border-blue-100" 
                          : "bg-gray-50 text-gray-400 border-gray-200"
                      )}>
                        {record.status}
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 border-b border-gray-50 text-right">
                      <button className="text-[10px] font-bold text-blue-600 hover:underline uppercase">Detail</button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="p-3 bg-gray-50 text-[10px] text-gray-400 italic text-right">
              * 所有操作均为模拟下单，数据每 5s 轮询更新一次
            </div>
          </CardContent>
        </Card>
    );
};
