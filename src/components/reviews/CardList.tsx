import React from 'react';
import { Loader2, Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { StockReviewCardResponse } from '@/services/api';
import { stockReviewStatusLabel } from './reviewLabels';

interface CardListProps {
  cards: StockReviewCardResponse[];
  selectedId: string | null;
  loadingCardId?: string | null;
  onSelect: (id: string) => void;
  onRequestAddEvent?: (id: string) => void;
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

export const CardList = ({ cards, selectedId, loadingCardId, onSelect, onRequestAddEvent }: CardListProps) => (
  <div className="space-y-2">
    {cards.length === 0 && (
      <Card className="rounded-lg border-gray-200 bg-white">
        <CardContent className="p-6 text-center text-[12px] text-gray-400">暂无标的复盘卡片。</CardContent>
      </Card>
    )}

    {cards.map((card) => {
      const latestEvent = card.events?.[card.events.length - 1];
      const selected = selectedId === card.id;
      const loading = loadingCardId === card.id;

      // 如果选中了，按钮常驻；如果未选中，当鼠标悬浮在 class="group" 的容器上时，按钮从 h-0 平滑展开并显现
      const buttonTransitionClass = selected
        ? 'mt-1.5 h-7 opacity-100'
        : 'mt-0 h-0 opacity-0 group-hover:mt-1.5 group-hover:h-7 group-hover:opacity-100';

      return (
        <button key={card.id} type="button" onClick={() => onSelect(card.id)} className="group block w-full rounded-lg text-left focus:outline-none focus:ring-2 focus:ring-blue-100">
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

              <div className="flex min-h-5 items-center justify-between gap-3 text-[10px] text-gray-400">
                <span>{card.startDate}{card.endDate ? ` - ${card.endDate}` : ''}</span>
                <span className="shrink-0">{durationDays(card)} 天</span>
              </div>

              {latestEvent ? (
                <p className="truncate text-[10px] text-gray-500">最近：{latestEvent.eventDate} / {latestEvent.title}</p>
              ) : (
                <p className="text-[10px] text-gray-300">暂无过程记录</p>
              )}

              {card.status === 'CLOSED' && (
                <div className="flex min-h-5 items-center justify-between gap-3 text-[10px] text-gray-500">
                  <span className="truncate">{card.pnlText || '未填盈亏'}</span>
                  <span className="shrink-0">纪律 {card.disciplineScore ?? '-'}</span>
                </div>
              )}

              {card.status === 'CLOSED' && onRequestAddEvent && (
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onRequestAddEvent(card.id);
                  }}
                  className={`w-full overflow-hidden transition-all duration-200 gap-1 text-[9px] font-bold uppercase tracking-wide ${buttonTransitionClass}`}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin text-slate-400" />
                      <span>正在加载...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="h-3 w-3" />
                      追加卖出后跟盘/反思
                    </>
                  )}
                </Button>
              )}
            </CardContent>
          </Card>
        </button>
      );
    })}
  </div>
);
