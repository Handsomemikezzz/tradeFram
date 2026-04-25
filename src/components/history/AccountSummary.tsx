import React from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { AccountSummaryResponse, formatCurrency } from '@/services/api';

interface AccountSummaryProps {
  summary: AccountSummaryResponse | null;
  loading?: boolean;
  error?: string | null;
}

export const AccountSummary = ({ summary, loading, error }: AccountSummaryProps) => {
  const items = summary ? [
    { label: '总资产', value: formatCurrency(summary.totalAssets) },
    { label: '可用现金', value: formatCurrency(summary.availableCash) },
    { label: '持仓市值', value: formatCurrency(summary.positionMarketValue) },
    { label: '今日盈亏', value: `${summary.todayPnl >= 0 ? '+' : ''}${formatCurrency(summary.todayPnl)}`, color: summary.todayPnl >= 0 ? 'text-red-600' : 'text-green-600' },
    { label: '仓位比例', value: `${summary.positionRatio.toFixed(1)}%` }
  ] : [];

  if (loading) {
    return <Card className="bg-white border border-gray-200 shadow-sm rounded-lg p-4 text-xs text-gray-400">正在加载账户摘要...</Card>;
  }

  if (error) {
    return <Card className="bg-white border border-gray-200 shadow-sm rounded-lg p-4 text-xs text-red-500">{error}</Card>;
  }

  if (!summary) {
    return <Card className="bg-white border border-gray-200 shadow-sm rounded-lg p-4 text-xs text-gray-400">暂无账户摘要</Card>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {items.map(item => (
        <Card key={item.label} className="bg-white border border-gray-200 shadow-sm rounded-lg p-4">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{item.label}</span>
          <div className={cn("text-lg font-bold font-mono mt-1", item.color || "text-gray-900")}>{item.value}</div>
        </Card>
      ))}
    </div>
  );
};
