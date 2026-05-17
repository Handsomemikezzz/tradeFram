import React, { useEffect, useMemo, useState } from 'react';
import { BookOpenCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardDetail } from '@/components/reviews/CardDetail';
import { CardForm } from '@/components/reviews/CardForm';
import { CardList } from '@/components/reviews/CardList';
import {
  reviewCardApi,
  StockReviewCardCloseRequest,
  StockReviewCardRequest,
  StockReviewCardResponse,
  StockReviewCardStatus,
  StockReviewCardSummaryResponse,
  StockReviewEventRequest,
} from '@/services/api';

type ReviewStatusFilter = StockReviewCardStatus | 'ALL';

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

function nextSelectedId(cards: StockReviewCardResponse[], currentId: string | null) {
  if (currentId && cards.some((card) => card.id === currentId)) return currentId;
  return cards[0]?.id ?? null;
}

export default function Reviews() {
  const [cards, setCards] = useState<StockReviewCardResponse[]>([]);
  const [summary, setSummary] = useState<StockReviewCardSummaryResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<StockReviewCardResponse | null>(null);
  const [status, setStatus] = useState<ReviewStatusFilter>('OPEN');
  const [keyword, setKeyword] = useState('');
  const [weekStart, setWeekStart] = useState(mondayOf(isoToday()));
  const weekEnd = useMemo(() => sundayOf(weekStart), [weekStart]);

  const load = async (preferredSelectedId = selectedId, statusFilter = status) => {
    const [page, summaryData] = await Promise.all([
      reviewCardApi.getCards({ status: statusFilter, keyword: keyword || undefined, pageSize: 50 }),
      reviewCardApi.getSummary({ startDate: weekStart, endDate: weekEnd }),
    ]);
    const nextId = nextSelectedId(page.items, preferredSelectedId);
    const nextCard = nextId ? await reviewCardApi.getCard(nextId) : null;
    setCards(page.items);
    setSummary(summaryData);
    setSelectedId(nextId);
    setSelectedCard(nextCard);
  };

  useEffect(() => {
    load().catch((err: Error) => toast.error(err.message));
  }, [status, weekStart]);

  const createCard = async (payload: StockReviewCardRequest) => {
    const created = await reviewCardApi.createCard(payload);
    toast.success('标的复盘卡片已建立');
    setStatus('OPEN');
    await load(created.id, 'OPEN');
  };

  const selectCard = async (id: string) => {
    setSelectedId(id);
    try {
      setSelectedCard(await reviewCardApi.getCard(id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载卡片详情失败');
    }
  };

  const addEvent = async (payload: StockReviewEventRequest) => {
    if (!selectedId) return;
    await reviewCardApi.addEvent(selectedId, payload);
    toast.success('过程事件已添加');
    await load(selectedId);
  };

  const closeCard = async (payload: StockReviewCardCloseRequest) => {
    if (!selectedId) return;
    const closed = await reviewCardApi.closeCard(selectedId, payload);
    toast.success('复盘卡片已结束');
    setStatus('ALL');
    await load(closed.id, 'ALL');
  };

  const reopenCard = async () => {
    if (!selectedId) return;
    const reopened = await reviewCardApi.reopenCard(selectedId);
    toast.success('复盘卡片已重新打开');
    setStatus('ALL');
    await load(reopened.id, 'ALL');
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BookOpenCheck className="w-6 h-6" />
            交易复盘
          </h2>
          <p className="text-muted-foreground text-sm mt-1">为每只股票建立一张复盘卡片，记录买入逻辑、持有过程、卖出结果和纪律反思。</p>
        </div>
        <label className="space-y-1">
          <span className="block text-[10px] uppercase tracking-widest text-gray-400 font-bold">统计周起始</span>
          <input type="date" value={weekStart} onChange={(event) => setWeekStart(mondayOf(event.target.value))} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" />
        </label>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="进行中" value={summary?.openCount ?? 0} />
        <Metric label="本周新建" value={summary?.createdInRangeCount ?? 0} />
        <Metric label="本周结束" value={summary?.closedInRangeCount ?? 0} />
        <Metric label="低纪律结束" value={summary?.lowDisciplineClosedCount ?? 0} />
      </div>

      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">新建标的复盘</CardTitle></CardHeader>
        <CardContent><CardForm onSubmit={createCard} /></CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        <select value={status} onChange={(event) => setStatus(event.target.value as ReviewStatusFilter)} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]">
          <option value="OPEN">进行中</option>
          <option value="CLOSED">已结束</option>
          <option value="ALL">全部</option>
        </select>
        <input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') load().catch((err: Error) => toast.error(err.message));
          }}
          placeholder="搜索代码或名称"
          className="h-8 w-56 rounded border border-gray-200 bg-white px-2 text-[11px]"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(260px,360px)_1fr] gap-4 items-start">
        <CardList cards={cards} selectedId={selectedId} onSelect={selectCard} />
        <CardDetail card={selectedCard} onAddEvent={addEvent} onClose={closeCard} onReopen={reopenCard} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Card className="rounded-lg border-gray-200 bg-white">
      <CardContent className="p-4">
        <div className="text-[10px] font-bold uppercase text-gray-400">{label}</div>
        <div className="mt-1 font-mono text-2xl font-bold text-gray-900">{value}</div>
      </CardContent>
    </Card>
  );
}
