import React, { useEffect, useMemo, useState } from 'react';
import { BookOpenCheck, ChevronDown, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardDetail } from '@/components/reviews/CardDetail';
import { CardForm } from '@/components/reviews/CardForm';
import { CardList } from '@/components/reviews/CardList';
import {
  ApiClientError,
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
  const [createOpen, setCreateOpen] = useState(false);
  const [weekStart, setWeekStart] = useState(mondayOf(isoToday()));
  const weekEnd = useMemo(() => sundayOf(weekStart), [weekStart]);

  const load = async (preferredSelectedId = selectedId, statusFilter = status) => {
    const [page, summaryData] = await Promise.all([
      reviewCardApi.getCards({ status: statusFilter, keyword: keyword || undefined, pageSize: 50 }),
      reviewCardApi.getSummary({ startDate: weekStart, endDate: weekEnd }),
    ]);
    let nextId = nextSelectedId(page.items, preferredSelectedId);
    let nextCard: StockReviewCardResponse | null = null;

    if (nextId) {
      try {
        nextCard = await reviewCardApi.getCard(nextId);
      } catch (err) {
        if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
          nextId = page.items[0]?.id ?? null;
          nextCard = nextId ? await reviewCardApi.getCard(nextId) : null;
        } else {
          throw err;
        }
      }
    }

    setCards(page.items);
    setSummary(summaryData);
    setSelectedId(nextId);
    setSelectedCard(nextCard);
  };

  useEffect(() => {
    load().catch((err: Error) => toast.error(err.message));
  }, [status, weekStart]);

  useEffect(() => {
    if (!selectedCard) return;
    if (!cards.some((item) => item.id === selectedCard.id)) {
      setSelectedCard(null);
      setSelectedId(null);
    }
  }, [cards, selectedCard]);

  const createCard = async (payload: StockReviewCardRequest) => {
    const created = await reviewCardApi.createCard(payload);
    toast.success('标的复盘卡片已建立');
    setCreateOpen(false);
    setStatus('OPEN');
    await load(created.id, 'OPEN');
  };

  const handleMissingCard = async () => {
    toast.error('该复盘卡片已不存在，请重新选择或新建');
    setSelectedId(null);
    setSelectedCard(null);
    await load();
  };

  const selectCard = async (id: string) => {
    try {
      const detail = await reviewCardApi.getCard(id);
      setSelectedId(id);
      setSelectedCard(detail);
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        await handleMissingCard();
        return;
      }
      toast.error(err instanceof Error ? err.message : '加载卡片详情失败');
    }
  };

  const addEvent = async (cardId: string, payload: StockReviewEventRequest) => {
    try {
      await reviewCardApi.addEvent(cardId, payload);
      toast.success('过程事件已添加');
      await load(cardId);
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        await handleMissingCard();
      }
      throw err;
    }
  };

  const closeCard = async (cardId: string, payload: StockReviewCardCloseRequest) => {
    try {
      const closed = await reviewCardApi.closeCard(cardId, payload);
      toast.success('复盘卡片已结束');
      setStatus('ALL');
      await load(closed.id, 'ALL');
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        await handleMissingCard();
      }
      throw err;
    }
  };

  const reopenCard = async (cardId: string) => {
    try {
      const reopened = await reviewCardApi.reopenCard(cardId);
      toast.success('复盘卡片已重新打开');
      setStatus('ALL');
      await load(reopened.id, 'ALL');
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        await handleMissingCard();
      }
      throw err;
    }
  };

  const deleteCard = async (cardId: string) => {
    try {
      await reviewCardApi.deleteCard(cardId);
      toast.success('复盘卡片已删除');
      setSelectedId(null);
      setSelectedCard(null);
      await load();
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        await handleMissingCard();
        return;
      }
      throw err;
    }
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

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Metric label="进行中" value={summary?.openCount ?? 0} tone="sky" />
        <Metric label="本周新建" value={summary?.createdInRangeCount ?? 0} tone="emerald" />
        <Metric label="本周结束" value={summary?.closedInRangeCount ?? 0} tone="slate" />
        <Metric label="低纪律结束" value={summary?.lowDisciplineClosedCount ?? 0} tone="amber" />
      </div>

      <Card className="rounded-lg border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-[14px] font-semibold text-slate-950">新建标的复盘</CardTitle>
            </div>
            <button
              type="button"
              onClick={() => setCreateOpen((open) => !open)}
              className={createOpen
                ? 'inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-4 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50'
                : 'inline-flex h-10 items-center gap-2 rounded-md bg-slate-950 px-4 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-800'}
            >
              {createOpen ? <ChevronDown className="h-4 w-4 rotate-180 transition-transform" /> : <Plus className="h-4 w-4" />}
              {createOpen ? '收起' : '创建新复盘'}
            </button>
          </div>
        </CardHeader>
        {createOpen && (
          <CardContent className="border-t border-slate-100 bg-slate-50/40 pt-4">
            <CardForm onSubmit={createCard} />
          </CardContent>
        )}
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
        <CardDetail card={selectedCard} onAddEvent={addEvent} onClose={closeCard} onReopen={reopenCard} onDelete={deleteCard} />
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: 'sky' | 'emerald' | 'slate' | 'amber' }) {
  const toneClass = {
    sky: 'bg-sky-50 text-sky-700 ring-sky-100',
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    slate: 'bg-slate-100 text-slate-700 ring-slate-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  }[tone];

  return (
    <Card className="rounded-lg border-slate-200 bg-white shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="text-[12px] font-medium text-slate-500">{label}</div>
          <div className={`h-2.5 w-2.5 rounded-full ring-4 ${toneClass}`} />
        </div>
        <div className="mt-2 font-mono text-2xl font-semibold text-slate-950">{value}</div>
      </CardContent>
    </Card>
  );
}
