import React, { useEffect, useMemo, useState } from 'react';
import { BookOpenCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EntryForm } from '@/components/reviews/EntryForm';
import { EntryList } from '@/components/reviews/EntryList';
import { StatsOverview } from '@/components/reviews/StatsOverview';
import { WeeklyWorkbench } from '@/components/reviews/WeeklyWorkbench';
import { reviewApi, ReviewEntryRequest, ReviewEntryResponse, ReviewStatsResponse, WeeklyReviewRequest, WeeklyWorkbenchResponse } from '@/services/api';

function isoToday() {
  return new Date().toISOString().slice(0, 10);
}

function mondayOf(dateText: string) {
  const date = new Date(`${dateText}T00:00:00`);
  const day = date.getDay() || 7;
  date.setDate(date.getDate() - day + 1);
  return date.toISOString().slice(0, 10);
}

function sundayOf(weekStart: string) {
  const date = new Date(`${weekStart}T00:00:00`);
  date.setDate(date.getDate() + 6);
  return date.toISOString().slice(0, 10);
}

export default function Reviews() {
  const [entries, setEntries] = useState<ReviewEntryResponse[]>([]);
  const [stats, setStats] = useState<ReviewStatsResponse | null>(null);
  const [workbench, setWorkbench] = useState<WeeklyWorkbenchResponse | null>(null);
  const [weekStart, setWeekStart] = useState(mondayOf(isoToday()));
  const weekEnd = useMemo(() => sundayOf(weekStart), [weekStart]);

  const load = async () => {
    const [entryPage, statsData, weekData] = await Promise.all([
      reviewApi.getEntries({ startDate: weekStart, endDate: weekEnd, pageSize: 50 }),
      reviewApi.getStats({ startDate: weekStart, endDate: weekEnd }),
      reviewApi.getWeek(weekStart),
    ]);
    setEntries(entryPage.items);
    setStats(statsData);
    setWorkbench(weekData);
  };

  useEffect(() => {
    load().catch((err: Error) => toast.error(err.message));
  }, [weekStart]);

  const createEntry = async (payload: ReviewEntryRequest) => {
    await reviewApi.createEntry(payload);
    toast.success('复盘记录已保存');
    await load();
  };

  const saveWeek = async (payload: WeeklyReviewRequest) => {
    await reviewApi.saveWeek(weekStart, payload);
    toast.success('周复盘已保存');
    await load();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BookOpenCheck className="w-6 h-6" />
            交易复盘
          </h2>
          <p className="text-muted-foreground text-sm mt-1">把交易行为和观察决策沉淀成可统计、可周复盘的样本库。</p>
        </div>
        <label className="space-y-1">
          <span className="block text-[10px] uppercase tracking-widest text-gray-400 font-bold">周起始</span>
          <input type="date" value={weekStart} onChange={(event) => setWeekStart(mondayOf(event.target.value))} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" />
        </label>
      </div>

      <StatsOverview stats={stats} />

      <Tabs defaultValue="entries">
        <TabsList>
          <TabsTrigger value="entries">复盘记录</TabsTrigger>
          <TabsTrigger value="weekly">周复盘工作台</TabsTrigger>
        </TabsList>
        <TabsContent value="entries" className="space-y-4">
          <Card className="rounded-lg border-gray-200 bg-white">
            <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">新增复盘记录</CardTitle></CardHeader>
            <CardContent><EntryForm onSubmit={createEntry} /></CardContent>
          </Card>
          <EntryList entries={entries} />
        </TabsContent>
        <TabsContent value="weekly">
          <WeeklyWorkbench data={workbench} onSave={saveWeek} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
