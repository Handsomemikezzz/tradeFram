import React, { useEffect, useState } from 'react';
import { 
  Award, 
  BookOpen, 
  CheckCircle, 
  ChevronDown, 
  Flame, 
  Image as ImageIcon, 
  Plus, 
  RotateCcw, 
  SquareCheckBig, 
  Trash2, 
  TrendingDown, 
  TrendingUp, 
  AlertTriangle,
  Star
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ApiClientError, StockReviewCardCloseRequest, StockReviewCardResponse, StockReviewEventRequest } from '@/services/api';
import { EventForm } from './EventForm';
import { EventTimeline } from './EventTimeline';
import { MultiTagInput } from './MultiTagInput';
import { MultiImageUpload, resolveImageUrl } from './MultiImageUpload';
import { ImageLightbox } from './ImageLightbox';
import { followedPlanLabel, problemPresets, reviewPlanStatusLabel, stockReviewInitialActionLabel, stockReviewStatusLabel } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const textareaClass = 'min-h-16 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

interface CardDetailProps {
  card: StockReviewCardResponse | null;
  openEventForm?: boolean;
  onEventFormConsumed?: () => void;
  onAddEvent: (cardId: string, payload: StockReviewEventRequest) => Promise<void>;
  onClose: (cardId: string, payload: StockReviewCardCloseRequest) => Promise<void>;
  onReopen: (cardId: string) => Promise<void>;
  onDelete: (cardId: string) => Promise<void>;
}

const displayName = (card: StockReviewCardResponse) => card.name || card.sectorTags.join(' / ') || '-';

const strategyLabels: Record<string, string> = {
  MOMENTUM_BREAKOUT: '动量突破',
  MEAN_REVERSION: '分歧低吸',
  TREND_FOLLOWING: '趋势追踪',
  EVENT_DRIVEN: '事件驱动',
  VOLATILITY_GRID: '网格震荡',
};

const TextBlock = ({ label, value }: { label: string; value?: string | null }) => (
  <div className="space-y-1">
    <div className="text-[10px] font-bold uppercase text-gray-400">{label}</div>
    <div className="min-h-14 whitespace-pre-wrap break-words rounded border border-gray-100 bg-gray-50 px-3 py-2 text-[11px] leading-5 text-gray-700">{value || '未填写'}</div>
  </div>
);

const TagList = ({ tags }: { tags: string[] }) => {
  if (tags.length === 0) return <span className="text-[11px] text-gray-400">无</span>;

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="border border-amber-100 bg-amber-50 text-[9px] text-amber-700">{tag}</Badge>
      ))}
    </div>
  );
};

export const CardDetail = ({ card, openEventForm, onEventFormConsumed, onAddEvent, onClose, onReopen, onDelete }: CardDetailProps) => {
  const [reopening, setReopening] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [reopenError, setReopenError] = useState<string | null>(null);
  const [planExpanded, setPlanExpanded] = useState(false);
  const [activeForm, setActiveForm] = useState<'event' | 'close' | null>(null);
  const [closeRecordExpanded, setCloseRecordExpanded] = useState(true); // Open closed summary by default for a good PM report!

  // Lightbox State
  const [lightboxImages, setLightboxImages] = useState<string[] | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  useEffect(() => {
    setReopenError(null);
    setDeleteError(null);
    setDeleteArmed(false);
    setDeleteConfirmText('');
    setPlanExpanded(false);
    setActiveForm(null);
    setCloseRecordExpanded(true);
  }, [card?.id]);

  useEffect(() => {
    if (!openEventForm || !card) return;
    setActiveForm('event');
    onEventFormConsumed?.();
  }, [openEventForm, card?.id, onEventFormConsumed]);

  useEffect(() => {
    if (!deleteArmed) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setDeleteArmed(false);
        setDeleteConfirmText('');
        setDeleteError(null);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [deleteArmed]);

  if (!card) {
    return (
      <Card className="rounded-lg border-slate-200 bg-white shadow-sm">
        <CardContent className="p-8 text-center text-[12px] text-slate-400">选择左侧复盘卡片查看详情。</CardContent>
      </Card>
    );
  }

  const reopen = async () => {
    setReopenError(null);
    setReopening(true);
    try {
      await onReopen(card.id);
    } catch (err) {
      setReopenError(err instanceof Error ? err.message : '重新打开失败');
    } finally {
      setReopening(false);
    }
  };

  const addEvent = async (payload: StockReviewEventRequest) => {
    try {
      await onAddEvent(card.id, payload);
      setActiveForm(null);
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'REVIEW_CARD_NOT_FOUND') {
        setActiveForm(null);
      }
      throw err;
    }
  };

  const closeCard = async (payload: StockReviewCardCloseRequest) => {
    await onClose(card.id, payload);
    setActiveForm(null);
  };

  const deleteConfirmPhrase = (card.code || card.name || '确认删除').trim();
  const deleteConfirmMatches =
    deleteConfirmPhrase.length > 0 &&
    deleteConfirmText.trim().toLowerCase() === deleteConfirmPhrase.toLowerCase();

  const cancelDelete = () => {
    setDeleteArmed(false);
    setDeleteConfirmText('');
    setDeleteError(null);
  };

  const deleteCard = async () => {
    if (!deleteConfirmMatches) return;

    setDeleteError(null);
    setDeleting(true);
    try {
      await onDelete(card.id);
      cancelDelete();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeleting(false);
    }
  };

  const triggerLightbox = (imageList: string[], index: number) => {
    setLightboxImages(imageList);
    setLightboxIndex(index);
  };

  // Determine PnL characteristics
  const pnlText = card.pnlText || '';
  const isProfit = /^[+＋]|^[0-9.]+%?[盈利盈赚]/.test(pnlText.trim()) || pnlText.includes('盈') || pnlText.includes('赚');
  const isLoss = /^[-－]|^[0-9.]+%?[亏损亏]/.test(pnlText.trim()) || pnlText.includes('亏');

  return (
    <div className="space-y-4">
      {/* 1. Header & Main Overview Card */}
      <Card className="rounded-lg border-slate-200 bg-white shadow-sm overflow-hidden">
        {/* Colorful PnL indicator banner if closed */}
        {card.status === 'CLOSED' && (
          <div className={`h-1.5 w-full ${isProfit ? 'bg-emerald-500' : isLoss ? 'bg-rose-500' : 'bg-slate-400'}`} />
        )}
        
        <CardHeader className="space-y-3 p-5 pb-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <CardTitle className="break-words text-xl font-bold text-slate-950 flex items-center gap-2">
                <span className="font-mono text-slate-400 text-sm bg-slate-100 rounded px-1.5 py-0.5">{card.code || '代码'}</span>
                <span className="text-slate-800">{displayName(card)}</span>
              </CardTitle>
              
              {/* Main Metadata Tags */}
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                <Badge variant="outline" className="text-[9px] border-slate-200 bg-slate-50 text-slate-600 font-semibold px-2 py-0.5">
                  {stockReviewInitialActionLabel[card.initialAction] || card.initialAction}
                </Badge>
                <Badge variant="outline" className="text-[9px] border-slate-200 bg-slate-50 text-slate-600 font-semibold px-2 py-0.5">
                  {reviewPlanStatusLabel[card.initialPlanStatus] || card.initialPlanStatus}
                </Badge>
                {card.status === 'CLOSED' && (
                  <Badge className={`text-[9px] px-2 py-0.5 font-bold ${
                    card.followedPlan 
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}>
                    {card.followedPlan ? '遵守计划' : '偏离计划'}
                  </Badge>
                )}
                {card.strategyType && (
                  <Badge variant="outline" className="text-[9px] border-indigo-200 bg-indigo-50/50 text-indigo-700 font-bold px-2 py-0.5">
                    🎯 {strategyLabels[card.strategyType] || card.strategyType}
                  </Badge>
                )}
                {card.expectedRrRatio && (
                  <Badge variant="outline" className="text-[9px] border-amber-200 bg-amber-50/50 text-amber-700 font-bold px-2 py-0.5">
                    ⚖️ 盈亏比 {card.expectedRrRatio}
                  </Badge>
                )}
                {card.stopLossTarget && (
                  <Badge variant="outline" className="text-[9px] border-rose-200 bg-rose-50/50 text-rose-700 font-bold px-2 py-0.5">
                    🛑 止损位 {card.stopLossTarget}
                  </Badge>
                )}
              </div>
            </div>
            
            {/* Actions & Dates */}
            <div className="flex flex-col items-end gap-2 text-right">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className={`text-[9px] px-2 py-0.5 font-bold uppercase tracking-wider ${
                  card.status === 'OPEN' 
                    ? 'bg-sky-50 text-sky-700 border border-sky-100' 
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {stockReviewStatusLabel[card.status] || card.status}
                </Badge>
                
                {!deleteArmed ? (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={deleting}
                    title="删除复盘卡片（需二次确认）"
                    aria-label="删除复盘卡片"
                    onClick={() => {
                      setDeleteError(null);
                      setDeleteArmed(true);
                    }}
                    className="h-7 w-7 p-0 text-slate-300 hover:text-slate-400 hover:bg-slate-50 rounded"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={deleting}
                    onClick={cancelDelete}
                    className="h-7 px-2 text-[10px] text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded"
                  >
                    取消
                  </Button>
                )}
              </div>
              
              <div className="font-mono text-[10px] text-slate-400 leading-tight">
                <div>建仓: {card.startDate}</div>
                {card.endDate && <div className="mt-0.5 text-slate-500">平仓: {card.endDate}</div>}
              </div>
            </div>
          </div>

          {deleteArmed && (
            <div
              className="rounded-lg border border-rose-100 bg-rose-50/40 p-3 space-y-2"
              role="alertdialog"
              aria-labelledby="delete-card-title"
              aria-describedby="delete-card-desc"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500 mt-0.5" />
                <div className="min-w-0 flex-1 space-y-2">
                  <div>
                    <p id="delete-card-title" className="text-[11px] font-bold text-rose-800">
                      确认删除复盘卡片？
                    </p>
                    <p id="delete-card-desc" className="mt-1 text-[10px] leading-5 text-rose-700/90">
                      删除后不可恢复，关联的过程事件也会一并删除。请在下方输入
                      <span className="mx-1 font-mono font-bold text-rose-900">{deleteConfirmPhrase}</span>
                      以继续。
                    </p>
                  </div>
                  <Input
                    value={deleteConfirmText}
                    onChange={(e) => setDeleteConfirmText(e.target.value)}
                    placeholder={`输入 ${deleteConfirmPhrase}`}
                    autoFocus
                    disabled={deleting}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && deleteConfirmMatches && !deleting) {
                        e.preventDefault();
                        deleteCard();
                      }
                    }}
                    className="h-8 text-[11px] font-mono bg-white border-rose-200 focus-visible:ring-rose-200"
                    aria-label="删除确认输入"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      disabled={deleting}
                      onClick={cancelDelete}
                      className="h-7 text-[10px]"
                    >
                      取消
                    </Button>
                    <Button
                      type="button"
                      variant="destructive"
                      size="xs"
                      disabled={!deleteConfirmMatches || deleting}
                      onClick={deleteCard}
                      className="h-7 text-[10px]"
                    >
                      {deleting ? '删除中…' : '永久删除'}
                    </Button>
                  </div>
                  {deleteError && <p className="text-[10px] text-red-600">{deleteError}</p>}
                </div>
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="space-y-4 p-5 pt-0">
          {/* Initial Reasons Text Block */}
          <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-3.5 text-[12px] leading-6 text-slate-700 shadow-inner">
            <div className="flex items-center gap-1.5 mb-1.5 text-[11px] font-bold text-slate-500">
              <BookOpen className="h-3.5 w-3.5 text-slate-400" />
              <span>买入建仓核心逻辑：</span>
            </div>
            <span className="break-words font-medium">{card.initialReasonText}</span>
          </div>

          {/* Entry Images Gallery */}
          {card.initialImages && card.initialImages.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                <ImageIcon className="h-3 w-3" />
                <span>建仓走势图表 ({card.initialImages.length})</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {card.initialImages.map((imgUrl, imgIdx) => (
                  <div 
                    key={imgIdx} 
                    className="group relative h-16 w-24 overflow-hidden rounded border border-slate-200 cursor-pointer shadow-sm transition hover:border-sky-500 hover:scale-[1.03] active:scale-95 bg-slate-50"
                    onClick={() => triggerLightbox(card.initialImages!, imgIdx)}
                  >
                    <img src={resolveImageUrl(imgUrl)} alt={`Entry Chart ${imgIdx + 1}`} className="h-full w-full object-cover" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Toggle Expand for initial assumptions */}
          <div>
            <button
              type="button"
              onClick={() => setPlanExpanded((expanded) => !expanded)}
              className="inline-flex h-7 items-center gap-1.5 rounded border border-slate-200 bg-white px-2.5 text-[10px] font-bold uppercase tracking-widest text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition shadow-sm"
              aria-expanded={planExpanded}
            >
              <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform duration-150 ${planExpanded ? 'rotate-180' : ''}`} />
              {planExpanded ? '收起计划' : '查看预期假设与原始计划'}
            </button>
            
            {planExpanded && (
              <div className="mt-3 grid grid-cols-1 xl:grid-cols-2 gap-3 pt-3 border-t border-slate-100">
                <TextBlock label="预期走势" value={card.expectedMoveText} />
                <TextBlock label="原始计划" value={card.originalPlanText} />
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase text-gray-400">题材/板块</div>
                  <div className="min-h-14 rounded border border-gray-100 bg-gray-50 px-3 py-2"><TagList tags={card.sectorTags} /></div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase text-gray-400">建仓情绪</div>
                  <div className="min-h-14 rounded border border-gray-100 bg-gray-50 px-3 py-2"><TagList tags={card.initialEmotionTags} /></div>
                </div>
              </div>
            )}
          </div>

          {/* Form action buttons — always visible, no expand required */}
          {deleteError && <div className="text-[11px] text-red-600">{deleteError}</div>}
          {card.status === 'OPEN' && (
            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3.5">
              <Button
                type="button"
                variant={activeForm === 'event' ? 'default' : 'outline'}
                onClick={() => setActiveForm(activeForm === 'event' ? null : 'event')}
                className="h-8 gap-1.5 text-[10px] font-bold uppercase tracking-widest transition"
              >
                <Plus className="h-3.5 w-3.5" />
                追加事件记录
              </Button>
              <Button
                type="button"
                variant={activeForm === 'close' ? 'default' : 'outline'}
                onClick={() => setActiveForm(activeForm === 'close' ? null : 'close')}
                className="h-8 gap-1.5 text-[10px] font-bold uppercase tracking-widest transition"
              >
                <SquareCheckBig className="h-3.5 w-3.5" />
                平仓结束复盘
              </Button>
            </div>
          )}
          {card.status === 'CLOSED' && (
            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3.5">
              <Button
                type="button"
                variant={activeForm === 'event' ? 'default' : 'outline'}
                onClick={() => setActiveForm(activeForm === 'event' ? null : 'event')}
                className="h-8 gap-1.5 text-[10px] font-bold uppercase tracking-widest transition"
              >
                <Plus className="h-3.5 w-3.5" />
                {activeForm === 'event' ? '收起反思表单' : '追加卖出后跟盘/反思'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Interactive Forms */}
      {activeForm === 'event' && (
        <Card className="rounded-lg border-slate-200 bg-white shadow-sm overflow-hidden">
          <CardHeader className="bg-slate-50/50 p-4 border-b border-slate-100">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              {card.status === 'CLOSED' ? '追加卖出后跟盘 / 复盘反思记录' : '追加交易过程事件'}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <EventForm 
              onSubmit={addEvent} 
              defaultType={card.status === 'CLOSED' ? 'OBSERVATION' : 'HOLD'} 
              isClosedCard={card.status === 'CLOSED'}
            />
          </CardContent>
        </Card>
      )}

      {card.status === 'OPEN' && activeForm === 'close' && (
        <Card className="rounded-lg border-slate-200 bg-white shadow-sm overflow-hidden">
          <CardHeader className="bg-slate-50/50 p-4 border-b border-slate-100">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500">平仓并终极复盘</CardTitle>
          </CardHeader>
          <CardContent className="p-4"><CloseForm cardId={card.id} onSubmit={closeCard} /></CardContent>
        </Card>
      )}

      {/* 3. CASE-STUDY REPORT CARD (Only visible when status is CLOSED) */}
      {card.status === 'CLOSED' && (
        <Card className="rounded-lg border-slate-200 bg-white shadow-sm overflow-hidden">
          <CardHeader className="bg-slate-50/70 p-4 border-b border-slate-100">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center gap-1.5">
                <Award className="h-4 w-4 text-amber-500" />
                <span>平仓结案与自我诊断报告</span>
              </CardTitle>
              
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCloseRecordExpanded((expanded) => !expanded)}
                  className="h-7 px-2.5 gap-1.5 text-[9px] font-bold uppercase tracking-widest transition"
                >
                  <ChevronDown className={`h-3 w-3 text-slate-400 transition-transform duration-150 ${closeRecordExpanded ? 'rotate-180' : ''}`} />
                  {closeRecordExpanded ? '隐藏' : '展开'}
                </Button>
                <Button 
                  type="button" 
                  variant="outline" 
                  disabled={reopening} 
                  onClick={reopen} 
                  className="h-7 px-2.5 gap-1 text-[9px] font-bold uppercase tracking-widest hover:bg-slate-50 transition"
                >
                  <RotateCcw className="h-3 w-3 text-slate-500" />
                  {reopening ? '打开中' : '重新激活卡片'}
                </Button>
              </div>
            </div>
            {reopenError && <div className="mt-2 text-[11px] text-red-600">{reopenError}</div>}
          </CardHeader>

          {closeRecordExpanded && (
            <CardContent className="p-5 space-y-5">
              {/* Outcomes Section: PnL, Plan Compliance, Discipline Score */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                {/* 1. Profit/Loss Output Card */}
                <div className={`rounded-lg border p-3 flex flex-col justify-between ${
                  isProfit 
                    ? 'border-emerald-100 bg-emerald-50/40 text-emerald-900 shadow-sm' 
                    : isLoss 
                      ? 'border-rose-100 bg-rose-50/30 text-rose-900 shadow-sm' 
                      : 'border-slate-200 bg-slate-50/40'
                }`}>
                  <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">平仓盈亏结果</div>
                  <div className="mt-2 flex flex-col">
                    <div className="flex items-baseline gap-1">
                      <span className="font-mono text-2xl font-bold tracking-tight">{card.pnlText || '0.00%'}</span>
                      {isProfit && <TrendingUp className="h-4 w-4 text-emerald-500 shrink-0" />}
                      {isLoss && <TrendingDown className="h-4 w-4 text-rose-500 shrink-0" />}
                    </div>
                    {card.pnlAmount !== null && (
                      <span className="text-[11px] font-bold font-mono mt-0.5 opacity-90">
                        {card.pnlAmount >= 0 ? `+${card.pnlAmount}` : card.pnlAmount} 元
                      </span>
                    )}
                  </div>
                </div>

                {/* 2. R-Multiple Card */}
                <div className={`rounded-lg border p-3 flex flex-col justify-between ${
                  card.rMultiple !== null
                    ? card.rMultiple >= 0
                      ? 'border-emerald-100 bg-emerald-50/40 text-emerald-900 shadow-sm'
                      : 'border-rose-100 bg-rose-50/30 text-rose-900 shadow-sm'
                    : 'border-slate-200 bg-slate-50/40'
                }`}>
                  <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">风险标尺 R倍数</div>
                  <div className="mt-2 flex items-baseline gap-1 font-mono">
                    {card.rMultiple !== null ? (
                      <>
                        <span className="text-2xl font-bold tracking-tight">
                          {card.rMultiple >= 0 ? `+${card.rMultiple}` : card.rMultiple}R
                        </span>
                        <span className="text-[10px] opacity-80 ml-1.5 font-sans font-medium">
                          {card.rMultiple >= 0 ? '👍 盈亏风险比卓越' : '⚠️ 风险损耗'}
                        </span>
                      </>
                    ) : (
                      <span className="text-sm font-semibold text-slate-400">未记录 R 单元</span>
                    )}
                  </div>
                </div>

                {/* 3. Plan Adherence Output Card */}
                <div className={`rounded-lg border p-3 flex flex-col justify-between ${
                  card.followedPlan 
                    ? 'border-emerald-100 bg-emerald-50/40 text-emerald-900 shadow-sm' 
                    : 'border-amber-100 bg-amber-50/30 text-amber-900 shadow-sm'
                }`}>
                  <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">计划符合审计</div>
                  <div className="mt-2 flex items-center gap-1.5 font-sans text-base font-bold">
                    {card.followedPlan ? (
                      <>
                        <CheckCircle className="h-4.5 w-4.5 text-emerald-500 shrink-0" />
                        <span>完美遵守计划</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="h-4.5 w-4.5 text-amber-500 shrink-0" />
                        <span>存在偏离行为</span>
                      </>
                    )}
                  </div>
                </div>

                {/* 4. Discipline Score */}
                <div className="rounded-lg border border-slate-200 bg-slate-50/20 p-3 flex flex-col justify-between shadow-sm">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">纪律执行评分</div>
                  <div className="mt-2 flex items-center gap-0.5 font-mono text-xl font-bold text-slate-800">
                    <span className="text-2xl text-slate-900">{card.disciplineScore || '3'}</span>
                    <span className="text-xs text-slate-400">/ 5</span>
                    <span className="ml-2 flex gap-0.5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <div 
                          key={i} 
                          className={`h-2.5 w-2.5 rounded-full ${
                            i < (card.disciplineScore || 3) ? 'bg-amber-400' : 'bg-slate-200'
                          }`} 
                        />
                      ))}
                    </span>
                  </div>
                </div>
              </div>

              {/* Exit Logic and Problem Tags */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-3.5">
                <div className="md:col-span-8 space-y-1">
                  <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">平仓出局理由</div>
                  <div className="min-h-16 whitespace-pre-wrap break-words rounded-lg border border-slate-100 bg-slate-50/50 px-3.5 py-2.5 text-[12px] leading-6 text-slate-700 shadow-inner font-medium">
                    {card.sellReasonText || '未填写'}
                  </div>
                </div>
                
                <div className="md:col-span-4 space-y-1">
                  <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">诊断归因标签</div>
                  <div className="min-h-16 rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2.5 flex items-center">
                    <TagList tags={card.problemTags} />
                  </div>
                </div>
              </div>

              {/* Professional Audit: Market Regime and Exit Quality */}
              {(card.marketRegime || card.exitQuality) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 bg-slate-50/30 p-3.5 rounded-xl border border-slate-100 shadow-sm">
                  {card.marketRegime && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">平仓时大盘环境</div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg">
                          {card.marketRegime === 'BULL_STRENGTH' ? '📈' :
                           card.marketRegime === 'BEAR_WEAKNESS' ? '📉' :
                           card.marketRegime === 'CONSOLIDATION' ? '🔄' : '❄️'}
                        </span>
                        <span className="text-[12px] font-bold text-slate-700">
                          {card.marketRegime === 'BULL_STRENGTH' ? '多头主升排列' :
                           card.marketRegime === 'BEAR_WEAKNESS' ? '弱势空头探底' :
                           card.marketRegime === 'CONSOLIDATION' ? '缩量横盘整理' : '极端冰点退潮'}
                        </span>
                      </div>
                    </div>
                  )}
                  {card.exitQuality && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">平仓执行纪律评价</div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                          card.exitQuality === 'OPTIMAL_EXIT' ? 'bg-emerald-100 text-emerald-800' :
                          card.exitQuality === 'EARLY_EXIT_FOMO' ? 'bg-amber-100 text-amber-800' :
                          card.exitQuality === 'LATE_EXIT_HOPE' ? 'bg-rose-100 text-rose-800' : 'bg-indigo-100 text-indigo-800'
                        }`}>
                          {card.exitQuality === 'OPTIMAL_EXIT' ? '完美出局 🏆' :
                           card.exitQuality === 'EARLY_EXIT_FOMO' ? '卖早踏空 ⚠️' :
                           card.exitQuality === 'LATE_EXIT_HOPE' ? '迟缓割肉/情绪扛单 ❌' : '纪律止损 ✅'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Exit Images Gallery */}
              {card.closeImages && card.closeImages.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                    <ImageIcon className="h-3 w-3" />
                    <span>出局图表 ({card.closeImages.length})</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {card.closeImages.map((imgUrl, imgIdx) => (
                      <div 
                        key={imgIdx} 
                        className="group relative h-16 w-24 overflow-hidden rounded border border-slate-200 cursor-pointer shadow-sm transition hover:border-rose-500 hover:scale-[1.03] active:scale-95 bg-slate-50"
                        onClick={() => triggerLightbox(card.closeImages!, imgIdx)}
                      >
                        <img src={resolveImageUrl(imgUrl)} alt={`Exit Chart ${imgIdx + 1}`} className="h-full w-full object-cover" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Structured Reflections: What went well vs What went wrong */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-3.5">
                {/* 1. What Went Well */}
                <div className="rounded-lg border border-emerald-100 bg-emerald-50/10 p-3.5 relative overflow-hidden">
                  <div className="absolute right-3 top-3 text-emerald-200/50"><CheckCircle className="h-10 w-10 stroke-[1.5]" /></div>
                  <div className="text-[10px] font-bold uppercase text-emerald-700 tracking-wider flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    <span>做得对的地方 (Strengths)</span>
                  </div>
                  <p className="mt-2.5 whitespace-pre-wrap break-words text-[11px] leading-6 text-slate-600 font-medium">
                    {card.didWellText || '未填写'}
                  </p>
                </div>

                {/* 2. What Went Wrong */}
                <div className="rounded-lg border border-rose-100 bg-rose-50/10 p-3.5 relative overflow-hidden">
                  <div className="absolute right-3 top-3 text-rose-200/50"><AlertTriangle className="h-10 w-10 stroke-[1.5]" /></div>
                  <div className="text-[10px] font-bold uppercase text-rose-700 tracking-wider flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                    <span>做错/不足之处 (Weaknesses)</span>
                  </div>
                  <p className="mt-2.5 whitespace-pre-wrap break-words text-[11px] leading-6 text-slate-600 font-medium">
                    {card.didWrongText || '未填写'}
                  </p>
                </div>
              </div>

              {/* Reflection Narrative Text */}
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">深度反思与总结</div>
                <div className="whitespace-pre-wrap break-words rounded-lg border border-slate-100 bg-slate-50/30 px-3.5 py-3 text-[12px] leading-6 text-slate-600 font-medium">
                  {card.reflectionText || '未填写'}
                </div>
              </div>

              {/* discipline Rule block: ULTIMATE STRATEGIC ASSET */}
              <div className="rounded-lg border-2 border-dashed border-amber-300 bg-amber-50/30 p-4 relative overflow-hidden">
                <div className="absolute right-4 top-4 text-amber-400/20"><Flame className="h-12 w-12" /></div>
                <div className="text-[10px] font-bold uppercase text-amber-700 tracking-wider flex items-center gap-1">
                  <span>提炼出的终极交易铁律 (Summarized Iron Rule)</span>
                </div>
                <p className="mt-3 text-[14px] font-bold leading-relaxed text-slate-800 pr-10 font-sans tracking-wide">
                  {card.ruleText || '铁律还未归纳，每次复盘至少沉淀一条可以固化执行的交易规则。'}
                </p>
              </div>

            </CardContent>
          )}
        </Card>
      )}

      {/* 4. Events Timeline */}
      <Card className="rounded-lg border-slate-200 bg-white shadow-sm overflow-hidden">
        <CardHeader className="bg-slate-50/50 p-4 border-b border-slate-100">
          <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500">持股历程与过程跟踪时间轴</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <EventTimeline events={card.events} onImageClick={triggerLightbox} />
        </CardContent>
      </Card>

      {/* 5. Fullscreen Lightbox Overlay */}
      {lightboxImages && (
        <ImageLightbox
          images={lightboxImages}
          startIndex={lightboxIndex}
          onClose={() => setLightboxImages(null)}
        />
      )}
    </div>
  );
};

const CloseForm = ({ cardId, onSubmit }: { cardId: string; onSubmit: (payload: StockReviewCardCloseRequest) => Promise<void> }) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [endDate, setEndDate] = useState(today());
  const [pnlText, setPnlText] = useState('');
  const [followedPlan, setFollowedPlan] = useState(true);
  const [disciplineScore, setDisciplineScore] = useState(3);
  const [problemTags, setProblemTags] = useState<string[]>([]);
  const [sellReasonText, setSellReasonText] = useState('');
  const [didWellText, setDidWellText] = useState('');
  const [didWrongText, setDidWrongText] = useState('');
  const [reflectionText, setReflectionText] = useState('');
  const [ruleText, setRuleText] = useState('');
  const [closeImages, setCloseImages] = useState<string[]>([]);

  // Professional Trading Audit Fields
  const [pnlAmount, setPnlAmount] = useState('');
  const [rMultiple, setRMultiple] = useState('');
  const [marketRegime, setMarketRegime] = useState<string | null>(null);
  const [exitQuality, setExitQuality] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setEndDate(today());
    setPnlText('');
    setFollowedPlan(true);
    setDisciplineScore(3);
    setProblemTags([]);
    setSellReasonText('');
    setDidWellText('');
    setDidWrongText('');
    setReflectionText('');
    setRuleText('');
    setCloseImages([]);
    
    setPnlAmount('');
    setRMultiple('');
    setMarketRegime(null);
    setExitQuality(null);
  }, [cardId]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({
        endDate,
        pnlText,
        followedPlan,
        disciplineScore,
        problemTags,
        sellReasonText,
        didWellText,
        didWrongText,
        reflectionText,
        ruleText,
        closeImages,
        
        // Professional Trading Audit Fields
        pnlAmount: pnlAmount.trim() ? Number(pnlAmount) : null,
        rMultiple: rMultiple.trim() ? Number(rMultiple) : null,
        marketRegime,
        exitQuality,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '结束卡片失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50/50 p-4 rounded-xl border border-slate-100 mb-4">
        <label className="space-y-1.5 flex flex-col">
          <span className="text-[11px] font-bold text-slate-500">结束出局日期</span>
          <Input 
            type="date" 
            value={endDate} 
            max={today()} 
            onChange={(event) => setEndDate(event.target.value)} 
            className="h-10 text-[13px] rounded-lg border-slate-200 bg-white px-3 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all outline-none" 
            required 
          />
        </label>
        
        <label className="space-y-1.5 flex flex-col">
          <span className="text-[11px] font-bold text-slate-500">盈亏比例 (%) / 结果说明</span>
          <Input 
            value={pnlText} 
            placeholder="例：+6.5% 或 冲高回落微亏 1%" 
            onChange={(event) => setPnlText(event.target.value)} 
            className="h-10 text-[13px] rounded-lg border-slate-200 bg-white px-3 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all outline-none" 
            required 
          />
        </label>

        <label className="space-y-1.5 flex flex-col">
          <span className="text-[11px] font-bold text-slate-500">实收盈亏金额 (元)</span>
          <Input 
            type="number"
            step="any"
            value={pnlAmount} 
            placeholder="例：+1250 或 -340" 
            onChange={(event) => setPnlAmount(event.target.value)} 
            className="h-10 text-[13px] rounded-lg border-slate-200 bg-white px-3 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all outline-none" 
          />
        </label>

        <label className="space-y-1.5 flex flex-col">
          <span className="text-[11px] font-bold text-slate-500 flex items-center gap-1.5">
            风险标尺 R倍数
            <span className="text-[9px] text-slate-400 font-mono font-medium bg-slate-100 px-1 rounded select-none">R-Unit</span>
          </span>
          <Input 
            type="number"
            step="any"
            value={rMultiple} 
            placeholder="例：+3.5 或 -1.0" 
            onChange={(event) => setRMultiple(event.target.value)} 
            className="h-10 text-[13px] rounded-lg border-slate-200 bg-white px-3 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all placeholder:text-slate-400 outline-none" 
          />
        </label>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="md:col-span-2 flex flex-col space-y-1.5">
          <span className="text-[11px] font-bold text-slate-500">是否遵守计划</span>
          <div className="grid grid-cols-2 gap-3">
            {/* Adhered to plan */}
            <div 
              onClick={() => setFollowedPlan(true)}
              className={`flex flex-col p-3 rounded-xl border-2 transition-all duration-300 cursor-pointer select-none ${
                followedPlan 
                  ? 'bg-emerald-50 border-emerald-500 text-emerald-800 shadow-sm ring-4 ring-emerald-100' 
                  : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
              }`}
            >
              <span className="text-[13px] font-bold flex items-center gap-1.5">
                <CheckCircle className={`h-4 w-4 ${followedPlan ? 'text-emerald-600' : 'text-slate-400'}`} />
                遵守计划
              </span>
              <span className={`text-[10px] ${followedPlan ? 'text-emerald-600/85' : 'text-slate-400'} mt-1 leading-relaxed`}>
                严格执行买入时的止损/止盈及既定策略，克服市场诱惑与恐惧。
              </span>
            </div>

            {/* Deviated from plan */}
            <div 
              onClick={() => setFollowedPlan(false)}
              className={`flex flex-col p-3 rounded-xl border-2 transition-all duration-300 cursor-pointer select-none ${
                !followedPlan 
                  ? 'bg-rose-50 border-rose-500 text-rose-800 shadow-sm ring-4 ring-rose-100' 
                  : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
              }`}
            >
              <span className="text-[13px] font-bold flex items-center gap-1.5">
                <AlertTriangle className={`h-4 w-4 ${!followedPlan ? 'text-rose-600' : 'text-slate-400'}`} />
                偏离计划
              </span>
              <span className={`text-[10px] ${!followedPlan ? 'text-rose-600/85' : 'text-slate-400'} mt-1 leading-relaxed`}>
                盘中追高情绪化建仓、因贪婪未及时止盈或产生不合理的扛单行为。
              </span>
            </div>
          </div>
        </div>

        {/* 5-star discipline rating clicker */}
        <div className="flex flex-col space-y-1.5">
          <span className="text-[11px] font-bold text-slate-500">操作纪律评分</span>
          <div className="bg-slate-50/50 border border-slate-200 rounded-xl p-3 flex flex-col justify-center items-center h-[96px] shadow-sm">
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setDisciplineScore(star)}
                  className="transition-transform duration-150 active:scale-90 cursor-pointer focus:outline-none"
                >
                  <Star 
                    className={`h-6 w-6 transition-colors ${
                      star <= disciplineScore 
                        ? 'fill-amber-400 text-amber-500 scale-110 drop-shadow-sm animate-pulse' 
                        : 'text-slate-300 hover:text-amber-300'
                    }`} 
                  />
                </button>
              ))}
            </div>
            <span className="text-[11px] text-slate-600 mt-2 font-bold">
              {['破坏纪律 ❌', '纪律较差 ⚠️', '正常执行 👍', '纪律良好 ⭐️', '知行合一 🏆'][disciplineScore - 1]} ({disciplineScore}分)
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        {/* Market Regime */}
        <div className="md:col-span-2 flex flex-col space-y-1.5">
          <span className="text-[11px] font-bold text-slate-500">大盘/市场环境分类</span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { value: 'BULL_STRENGTH', label: '多头主升', emoji: '📈', desc: '指数多头排列/主升浪', activeClass: 'bg-emerald-50 border-emerald-500 text-emerald-800 ring-2 ring-emerald-100' },
              { value: 'BEAR_WEAKNESS', label: '弱势空头', emoji: '📉', desc: '指数空头排列/冰点探底', activeClass: 'bg-rose-50 border-rose-500 text-rose-800 ring-2 ring-rose-100' },
              { value: 'CONSOLIDATION', label: '缩量盘整', emoji: '🔄', desc: '指数横盘震荡/无方向', activeClass: 'bg-indigo-50 border-indigo-500 text-indigo-800 ring-2 ring-indigo-100' },
              { value: 'EXTREME_PANIC', label: '退潮冰点', emoji: '❄️', desc: '情绪退潮/极端放量杀跌', activeClass: 'bg-amber-50 border-amber-500 text-amber-800 ring-2 ring-amber-100' },
            ].map((item) => {
              const active = marketRegime === item.value;
              return (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setMarketRegime(active ? null : item.value)}
                  className={`flex flex-col items-center justify-center p-2 rounded-xl border text-center transition-all duration-200 select-none ${
                    active 
                      ? item.activeClass
                      : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
                  }`}
                >
                  <span className="text-[14px]">{item.emoji}</span>
                  <span className="text-[12px] font-bold mt-1">{item.label}</span>
                  <span className={`text-[8px] mt-0.5 leading-tight ${active ? 'opacity-85' : 'text-slate-400'}`}>{item.desc}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Exit Quality Toggle Badge List */}
        <div className="flex flex-col space-y-1.5">
          <span className="text-[11px] font-bold text-slate-500">平仓质量评价</span>
          <div className="bg-slate-50/50 border border-slate-200 rounded-xl p-3 flex flex-col justify-center items-center h-[96px] shadow-sm">
            <div className="grid grid-cols-2 gap-1.5 w-full">
              {[
                { value: 'OPTIMAL_EXIT', label: '完美出局 🏆', activeClass: 'bg-emerald-600 border-emerald-600 text-white shadow-sm ring-2 ring-emerald-100 hover:bg-emerald-700' },
                { value: 'EARLY_EXIT_FOMO', label: '卖早踏空 ⚠️', activeClass: 'bg-amber-600 border-amber-600 text-white shadow-sm ring-2 ring-amber-100 hover:bg-amber-700' },
                { value: 'LATE_EXIT_HOPE', label: '拖拉扛单 ❌', activeClass: 'bg-rose-600 border-rose-600 text-white shadow-sm ring-2 ring-rose-100 hover:bg-rose-700' },
                { value: 'DISCIPLINED_STOP', label: '纪律止损 ✅', activeClass: 'bg-indigo-600 border-indigo-600 text-white shadow-sm ring-2 ring-indigo-100 hover:bg-indigo-700' },
              ].map((item) => {
                const active = exitQuality === item.value;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setExitQuality(active ? null : item.value)}
                    className={`flex items-center justify-center py-1.5 px-0.5 rounded-lg border text-center text-[10px] font-bold transition-all duration-200 select-none ${
                      active 
                        ? item.activeClass
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
                    }`}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
        <div className="mb-2.5 flex items-center justify-between border-b border-slate-100 pb-1.5">
          <span className="text-[12px] font-semibold text-slate-800">出局发现问题</span>
          <span className="text-[9px] text-slate-400 font-mono">PROBLEM TAGS</span>
        </div>
        <MultiTagInput value={problemTags} presets={problemPresets} placeholder="选择出局时发现的问题标签" onChange={setProblemTags} />
      </div>

      <div className="pt-2.5 border-t border-slate-100">
        <MultiImageUpload images={closeImages} onChange={setCloseImages} label="出局走势图表 (支持拖拽/多图上传)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Sell Reason */}
        <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
          <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
              出局理由 / 盘后逻辑 <span className="text-[10px] text-rose-500 font-bold">*</span>
            </span>
            <span className="text-[9px] text-slate-400 font-mono uppercase">EXIT REASON</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-20 resize-none leading-relaxed"
            value={sellReasonText}
            placeholder="例：触发止盈/止损线；板块龙头走弱，个股跌破重要支撑线。"
            onChange={(event) => setSellReasonText(event.target.value)}
            required
          />
        </div>

        {/* Did Well */}
        <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
          <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              做得好 <span className="text-[10px] text-rose-500 font-bold">*</span>
            </span>
            <span className="text-[9px] text-slate-400 font-mono uppercase">WHAT WENT WELL</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-20 resize-none leading-relaxed"
            value={didWellText}
            placeholder="说明做得对的细节：例，止损坚决果断，没有产生无谓的幻想。"
            onChange={(event) => setDidWellText(event.target.value)}
            required
          />
        </div>

        {/* Did Wrong */}
        <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
          <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
              做错了 <span className="text-[10px] text-rose-500 font-bold">*</span>
            </span>
            <span className="text-[9px] text-slate-400 font-mono uppercase">WHAT WENT WRONG</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-20 resize-none leading-relaxed"
            value={didWrongText}
            placeholder="剖析错误或不完美的细节：例，建仓买点偏高，导致承受了不必要的洗盘痛苦。"
            onChange={(event) => setDidWrongText(event.target.value)}
            required
          />
        </div>

        {/* Reflection */}
        <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
          <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
              反思与复盘总结 <span className="text-[10px] text-rose-500 font-bold">*</span>
            </span>
            <span className="text-[9px] text-slate-400 font-mono uppercase">DEEPER REFLECTION</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-20 resize-none leading-relaxed"
            value={reflectionText}
            placeholder="总结心理活动与环境教训：例，对个股题材的想象空间高估了，之后需要结合大盘承接看强度。"
            onChange={(event) => setReflectionText(event.target.value)}
            required
          />
        </div>

        {/* Rule take-away - Dashed Golden Border highlight representing strategic assets */}
        <div className="group rounded-xl border border-dashed border-amber-300 bg-amber-50/5 p-4 transition-all duration-300 hover:shadow-lg hover:bg-amber-50/10 focus-within:border-amber-500 focus-within:ring-4 focus-within:ring-amber-100 lg:col-span-2">
          <div className="mb-2 flex items-center justify-between border-b border-amber-200 pb-1.5">
            <span className="text-[13px] font-bold text-amber-800 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping" />
              🏆 规则沉淀 (核心交易法则提取) <span className="text-[10px] text-rose-500 font-bold">*</span>
            </span>
            <span className="text-[10px] text-amber-600 font-mono font-bold tracking-widest uppercase">STRATEGIC RULE</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-500 focus:ring-0 focus:outline-none min-h-20 resize-none font-semibold leading-relaxed"
            value={ruleText}
            placeholder="🔥 请写下一条能被以后复用的确定性规则！例：缩量分歧市不买后排跟风股，只做确定性核心前排。"
            onChange={(event) => setRuleText(event.target.value)}
            required
          />
        </div>
      </div>

      <div className="flex justify-end pt-3 border-t border-slate-100">
        {error && <div className="mr-auto self-center text-[12px] font-semibold text-rose-600">{error}</div>}
        <Button 
          type="submit" 
          disabled={submitting} 
          className="h-10 rounded-lg bg-slate-900 px-6 text-[13px] font-semibold text-white shadow-md hover:bg-slate-800 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          {submitting ? '结束中...' : '确认结束复盘卡片'}
        </Button>
      </div>
    </form>
  );
};
