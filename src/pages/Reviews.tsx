import React, { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { BookOpenCheck, ChevronDown, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardDetail } from '@/components/reviews/CardDetail';
import { CardForm } from '@/components/reviews/CardForm';
import { CardList } from '@/components/reviews/CardList';
import { DojoWorkspace } from '@/components/reviews/DojoWorkspace';
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

type ReviewStatusFilter = 'OPEN' | 'CLOSED' | 'FOLLOWED' | 'DEVIATED' | 'ALL';

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
  const location = useLocation();
  const prefillData = location.state?.prefill;
  const [cards, setCards] = useState<StockReviewCardResponse[]>([]);
  const [summary, setSummary] = useState<StockReviewCardSummaryResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<StockReviewCardResponse | null>(null);
  const [status, setStatus] = useState<ReviewStatusFilter>('OPEN');
  const [keyword, setKeyword] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [openEventForm, setOpenEventForm] = useState(false);
  const [loadingCardId, setLoadingCardId] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'CARDS' | 'DOJO'>('CARDS');

  useEffect(() => {
    if (prefillData) {
      setCreateOpen(true);
    }
  }, [prefillData]);

  const load = async (preferredSelectedId = selectedId, statusFilter = status) => {
    let apiStatus: StockReviewCardStatus | 'ALL' | undefined;
    let followedPlan: boolean | undefined;

    if (statusFilter === 'OPEN') {
      apiStatus = 'OPEN';
    } else if (statusFilter === 'CLOSED') {
      apiStatus = 'CLOSED';
    } else if (statusFilter === 'FOLLOWED') {
      apiStatus = 'CLOSED';
      followedPlan = true;
    } else if (statusFilter === 'DEVIATED') {
      apiStatus = 'CLOSED';
      followedPlan = false;
    } else {
      apiStatus = 'ALL';
    }

    const [page, summaryData] = await Promise.all([
      reviewCardApi.getCards({ status: apiStatus, followedPlan, keyword: keyword || undefined, pageSize: 50 }),
      reviewCardApi.getSummary(),
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
    if (activeTab === 'CARDS') {
      load().catch((err: Error) => toast.error(err.message));
    }
  }, [status, activeTab]);

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

  const selectCard = async (id: string, options?: { openEventForm?: boolean }) => {
    if (!options?.openEventForm) {
      setOpenEventForm(false);
    }
    setLoadingCardId(id);
    try {
      const detail = await reviewCardApi.getCard(id);
      setSelectedId(id);
      setSelectedCard(detail);
      if (options?.openEventForm) {
        setOpenEventForm(true);
      }
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        await handleMissingCard();
        return;
      }
      toast.error(err instanceof Error ? err.message : '加载卡片详情失败');
    } finally {
      setLoadingCardId(null);
    }
  };

  const selectCardAndOpenEventForm = (id: string) => selectCard(id, { openEventForm: true });

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
            <BookOpenCheck className="w-6 h-6 animate-pulse" />
            交易复盘
          </h2>
          <p className="text-muted-foreground text-sm mt-1">记录买入逻辑、持有过程、交易心法、遵守纪律和深度反思。</p>
        </div>
      </div>

      {/* Premium Tab Bar Selector */}
      <div className="flex border-b border-slate-200">
        <button
          type="button"
          onClick={() => setActiveTab('CARDS')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'CARDS'
              ? 'border-blue-600 text-blue-600 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
          }`}
        >
          标的个案复盘 (Stock Case Reviews)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('DOJO')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'DOJO'
              ? 'border-blue-600 text-blue-600 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
          }`}
        >
          <span>心法与交易纪律 (Trader's Dojo)</span>
          <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700 ring-1 ring-inset ring-blue-700/10">
            修炼
          </span>
        </button>
      </div>

      {activeTab === 'CARDS' ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 animate-in fade-in slide-in-from-top-2 duration-300">
            <Metric
              label="进行中"
              value={summary?.openCount ?? 0}
              tone="sky"
              active={status === 'OPEN'}
              onClick={() => setStatus('OPEN')}
            />
            <Metric
              label="已结束"
              value={summary?.closedCount ?? 0}
              tone="slate"
              active={status === 'CLOSED'}
              onClick={() => setStatus('CLOSED')}
            />
            <Metric
              label="遵守计划"
              value={summary?.followedPlanCount ?? 0}
              tone="emerald"
              active={status === 'FOLLOWED'}
              onClick={() => setStatus('FOLLOWED')}
            />
            <Metric
              label="偏离计划"
              value={summary?.deviatedPlanCount ?? 0}
              tone="amber"
              active={status === 'DEVIATED'}
              onClick={() => setStatus('DEVIATED')}
            />
          </div>

          <Card className="rounded-lg border-slate-200 bg-white shadow-sm animate-in fade-in duration-300">
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
                <CardForm onSubmit={createCard} prefill={prefillData} />
              </CardContent>
            )}
          </Card>

          <div className="flex flex-wrap items-center gap-2">
            <select value={status} onChange={(event) => setStatus(event.target.value as ReviewStatusFilter)} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]">
              <option value="OPEN">进行中</option>
              <option value="CLOSED">已结束</option>
              <option value="FOLLOWED">遵守计划 (已结束)</option>
              <option value="DEVIATED">偏离计划 (已结束)</option>
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

          <div className="grid grid-cols-1 xl:grid-cols-[minmax(260px,360px)_1fr] gap-4 items-start animate-in fade-in duration-300">
            <CardList
              cards={cards}
              selectedId={selectedId}
              loadingCardId={loadingCardId}
              onSelect={selectCard}
              onRequestAddEvent={selectCardAndOpenEventForm}
            />
            <CardDetail
              card={selectedCard}
              openEventForm={openEventForm}
              onEventFormConsumed={() => setOpenEventForm(false)}
              onAddEvent={addEvent}
              onClose={closeCard}
              onReopen={reopenCard}
              onDelete={deleteCard}
            />
          </div>
        </>
      ) : (
        <div className="animate-in fade-in duration-300">
          <DojoWorkspace />
        </div>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  active,
  onClick,
}: {
  label: string;
  value: number;
  tone: 'sky' | 'emerald' | 'slate' | 'amber';
  active: boolean;
  onClick?: () => void;
}) {
  const toneClass = {
    sky: 'bg-sky-50 text-sky-700 ring-sky-100',
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    slate: 'bg-slate-100 text-slate-700 ring-slate-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  }[tone];

  const activeBorder = {
    sky: 'border-sky-500 ring-2 ring-sky-100/50 shadow-sm',
    emerald: 'border-emerald-500 ring-2 ring-emerald-100/50 shadow-sm',
    slate: 'border-slate-500 ring-2 ring-slate-200 shadow-sm',
    amber: 'border-amber-500 ring-2 ring-amber-100/50 shadow-sm',
  }[tone];

  return (
    <Card
      onClick={onClick}
      className={`rounded-lg bg-white cursor-pointer transition-all hover:shadow-md hover:-translate-y-[2px] active:scale-[0.98] ${
        active ? `${activeBorder} border-transparent` : 'border-slate-200 hover:border-slate-300'
      }`}
    >
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
