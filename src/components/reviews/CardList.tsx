import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { StockReviewCardResponse } from '@/services/api';
import { reviewPlanStatusLabel, stockReviewInitialActionLabel, stockReviewStatusLabel } from './reviewLabels';

interface CardListProps {
  cards: StockReviewCardResponse[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function durationDays(card: StockReviewCardResponse) {
  const end = card.endDate || new Date().toISOString().slice(0, 10);
  const startTime = new Date(`${card.startDate}T00:00:00`).getTime();
  const endTime = new Date(`${end}T00:00:00`).getTime();
  return Math.max(1, Math.floor((endTime - startTime) / 86400000) + 1);
}

function displayName(card: StockReviewCardResponse) {
  return card.name || card.sectorTags.join(' / ') || '-';
}

export const CardList = ({ cards, selectedId, onSelect }: CardListProps) => (
  <div className="space-y-2">
    {cards.length === 0 && (
      <Card className="rounded-lg border-gray-200 bg-white">
        <CardContent className="p-6 text-center text-[12px] text-gray-400">暂无标的复盘卡片。</CardContent>
      </Card>
    )}

    {cards.map((card) => {
      const latestEvent = card.events?.[card.events.length - 1];
      const selected = selectedId === card.id;

      return (
        <button key={card.id} type="button" onClick={() => onSelect(card.id)} className="block w-full rounded-lg text-left focus:outline-none focus:ring-2 focus:ring-blue-100">
          <Card className={selected ? 'rounded-lg border-blue-300 bg-blue-50 py-3' : 'rounded-lg border-gray-200 bg-white py-3 hover:bg-gray-50'}>
            <CardContent className="p-3 space-y-2">
              <div className="flex min-h-10 items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-mono text-[12px] font-bold text-gray-900">{card.code || '-'}</div>
                  <div className="truncate text-[12px] text-gray-600">{displayName(card)}</div>
                </div>
                <Badge variant="secondary" className="shrink-0 text-[9px]">
                  {stockReviewStatusLabel[card.status] || card.status}
                </Badge>
              </div>

              <div className="flex min-h-6 flex-wrap gap-1">
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{stockReviewInitialActionLabel[card.initialAction] || card.initialAction}</Badge>
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{reviewPlanStatusLabel[card.initialPlanStatus] || card.initialPlanStatus}</Badge>
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{durationDays(card)} 天</Badge>
              </div>

              <p className="min-h-8 line-clamp-2 text-[11px] leading-4 text-gray-600">{card.initialReasonText}</p>

              {latestEvent ? (
                <p className="truncate text-[10px] text-gray-400">最近：{latestEvent.eventDate} / {latestEvent.title}</p>
              ) : (
                <p className="text-[10px] text-gray-300">暂无过程记录</p>
              )}

              {card.status === 'CLOSED' && (
                <div className="flex min-h-5 items-center justify-between gap-3 text-[10px] text-gray-500">
                  <span className="truncate">{card.pnlText || '未填盈亏'}</span>
                  <span className="shrink-0">纪律 {card.disciplineScore ?? '-'}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </button>
      );
    })}
  </div>
);
