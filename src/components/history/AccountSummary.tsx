
import React from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export const AccountSummary = () => {
  const summary = [
    { label: '总资产', value: '1,250,300.00' },
    { label: '可用现金', value: '350,000.00' },
    { label: '持仓市值', value: '900,300.00' },
    { label: '今日盈亏', value: '+12,400.00', color: 'text-red-600' },
    { label: '仓位比例', value: '72.0%' }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {summary.map(item => (
        <Card key={item.label} className="bg-white border border-gray-200 shadow-sm rounded-lg p-4">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{item.label}</span>
          <div className={cn("text-lg font-bold font-mono mt-1", item.color || "text-gray-900")}>{item.value}</div>
        </Card>
      ))}
    </div>
  );
};
