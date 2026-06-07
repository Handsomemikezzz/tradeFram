/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { CalendarDays, Filter } from 'lucide-react';
import { PatternATab } from '@/components/screener/PatternATab';
import { UptrendTab } from '@/components/screener/UptrendTab';
import { Input } from '@/components/ui/input';
import LimitUpBreakMonitor from '@/pages/LimitUpBreakMonitor';
import { cn } from '@/lib/utils';

type TabKey = 'pattern_a' | 'limit_up_break' | 'uptrend';

function todayText(): string {
  const now = new Date();
  return `${now.getFullYear()}-${`${now.getMonth() + 1}`.padStart(2, '0')}-${`${now.getDate()}`.padStart(2, '0')}`;
}

export default function Screeners() {
  const [tab, setTab] = useState<TabKey>('pattern_a');
  const [tradeDate, setTradeDate] = useState('');

  return (
    <div className="space-y-5">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-[#1A1C1E]">
            <Filter className="w-6 h-6 text-blue-600" />
            选股
          </h2>
          <p className="text-gray-500 text-xs font-medium uppercase tracking-widest mt-1">盘后日 K 策略筛选</p>
        </div>
        <div className="flex items-center gap-2 bg-white p-2 rounded-lg border border-gray-200 shadow-sm">
          <div className="relative">
            <CalendarDays className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <Input
              type="date"
              value={tradeDate}
              onChange={(event) => setTradeDate(event.target.value)}
              className="h-8 pl-8 w-[150px] text-[11px] bg-white border-gray-200 rounded"
              placeholder={todayText()}
            />
          </div>
        </div>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        <TabButton active={tab === 'pattern_a'} onClick={() => setTab('pattern_a')}>走势 A</TabButton>
        <TabButton active={tab === 'limit_up_break'} onClick={() => setTab('limit_up_break')}>断板</TabButton>
        <TabButton active={tab === 'uptrend'} onClick={() => setTab('uptrend')}>上行趋势</TabButton>
      </div>

      {tab === 'pattern_a' && <PatternATab tradeDate={tradeDate} />}
      {tab === 'limit_up_break' && <LimitUpBreakMonitor embedded tradeDate={tradeDate} onTradeDateChange={setTradeDate} />}
      {tab === 'uptrend' && <UptrendTab tradeDate={tradeDate} />}
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'px-4 py-2 text-sm font-bold border-b-2 -mb-px transition-colors',
        active ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-800',
      )}
    >
      {children}
    </button>
  );
}
