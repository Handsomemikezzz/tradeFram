import React, { useEffect, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { StockReviewCardCloseRequest, StockReviewCardResponse, StockReviewEventRequest } from '@/services/api';
import { EventForm } from './EventForm';
import { EventTimeline } from './EventTimeline';
import { MultiTagInput } from './MultiTagInput';
import { followedPlanLabel, problemPresets, reviewPlanStatusLabel, stockReviewInitialActionLabel, stockReviewStatusLabel } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const textareaClass = 'min-h-16 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

interface CardDetailProps {
  card: StockReviewCardResponse | null;
  onAddEvent: (payload: StockReviewEventRequest) => Promise<void>;
  onClose: (payload: StockReviewCardCloseRequest) => Promise<void>;
  onReopen: () => Promise<void>;
}

const displayName = (card: StockReviewCardResponse) => card.name || card.sectorTags.join(' / ') || '-';

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

export const CardDetail = ({ card, onAddEvent, onClose, onReopen }: CardDetailProps) => {
  const [reopening, setReopening] = useState(false);
  const [reopenError, setReopenError] = useState<string | null>(null);

  useEffect(() => {
    setReopenError(null);
  }, [card?.id]);

  if (!card) {
    return (
      <Card className="rounded-lg border-gray-200 bg-white">
        <CardContent className="p-8 text-center text-[12px] text-gray-400">选择左侧复盘卡片查看详情。</CardContent>
      </Card>
    );
  }

  const reopen = async () => {
    setReopenError(null);
    setReopening(true);
    try {
      await onReopen();
    } catch (err) {
      setReopenError(err instanceof Error ? err.message : '重新打开失败');
    } finally {
      setReopening(false);
    }
  };

  return (
    <div className="space-y-3">
      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="break-words text-lg">
                <span className="font-mono">{card.code || '-'}</span>
                <span className="ml-2 text-gray-700">{displayName(card)}</span>
              </CardTitle>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge variant="secondary" className="text-[9px]">{stockReviewStatusLabel[card.status] || card.status}</Badge>
                <Badge variant="secondary" className="bg-gray-100 text-[9px] text-gray-600">{stockReviewInitialActionLabel[card.initialAction] || card.initialAction}</Badge>
                <Badge variant="secondary" className="bg-gray-100 text-[9px] text-gray-600">{reviewPlanStatusLabel[card.initialPlanStatus] || card.initialPlanStatus}</Badge>
              </div>
            </div>
            <div className="text-right text-[10px] text-gray-400">
              <div>开始 {card.startDate}</div>
              {card.endDate && <div>结束 {card.endDate}</div>}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-3">
            <TextBlock label="初始理由" value={card.initialReasonText} />
            <TextBlock label="预期走势" value={card.expectedMoveText} />
            <TextBlock label="原始计划" value={card.originalPlanText} />
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">事件时间线</CardTitle></CardHeader>
        <CardContent><EventTimeline events={card.events} /></CardContent>
      </Card>

      {card.status === 'OPEN' && (
        <>
          <Card className="rounded-lg border-gray-200 bg-white">
            <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">添加过程事件</CardTitle></CardHeader>
            <CardContent><EventForm onSubmit={onAddEvent} /></CardContent>
          </Card>

          <Card className="rounded-lg border-gray-200 bg-white">
            <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">结束复盘卡片</CardTitle></CardHeader>
            <CardContent><CloseForm cardId={card.id} onSubmit={onClose} /></CardContent>
          </Card>
        </>
      )}

      {card.status === 'CLOSED' && (
        <Card className="rounded-lg border-gray-200 bg-white">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle className="text-[10px] uppercase tracking-widest">结束记录</CardTitle>
              <Button type="button" variant="outline" disabled={reopening} onClick={reopen} className="h-8 gap-1.5 text-[10px] font-bold uppercase tracking-widest">
                <RotateCcw className="h-3.5 w-3.5" />
                {reopening ? '打开中' : '重新打开'}
              </Button>
            </div>
            {reopenError && <div className="text-[11px] text-red-600">{reopenError}</div>}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <TextBlock label="结束日期" value={card.endDate} />
              <TextBlock label="盈亏结果" value={card.pnlText} />
              <TextBlock label="纪律分" value={card.disciplineScore == null ? null : String(card.disciplineScore)} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <TextBlock label="是否按计划" value={card.followedPlan == null ? null : followedPlanLabel[String(card.followedPlan)]} />
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase text-gray-400">问题标签</div>
                <div className="min-h-14 rounded border border-gray-100 bg-gray-50 px-3 py-2"><TagList tags={card.problemTags} /></div>
              </div>
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-3">
              <TextBlock label="卖出理由" value={card.sellReasonText} />
              <TextBlock label="做得好" value={card.didWellText} />
              <TextBlock label="做错了" value={card.didWrongText} />
              <TextBlock label="反思" value={card.reflectionText} />
              <TextBlock label="规则沉淀" value={card.ruleText} />
            </div>
          </CardContent>
        </Card>
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
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '结束卡片失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">结束日期</span>
          <Input type="date" value={endDate} max={today()} onChange={(event) => setEndDate(event.target.value)} className="h-8 text-[11px]" required />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">盈亏结果</span>
          <Input value={pnlText} placeholder="例：+6.5%" onChange={(event) => setPnlText(event.target.value)} className="h-8 text-[11px]" required />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">是否按计划</span>
          <select value={String(followedPlan)} onChange={(event) => setFollowedPlan(event.target.value === 'true')} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]">
            <option value="true">按计划</option>
            <option value="false">偏离计划</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">纪律分</span>
          <Input type="number" min={1} max={5} value={disciplineScore} onChange={(event) => setDisciplineScore(Number(event.target.value))} className="h-8 text-[11px]" required />
        </label>
      </div>

      <div className="space-y-1">
        <span className="text-[10px] font-bold uppercase text-gray-500">问题标签</span>
        <MultiTagInput value={problemTags} presets={problemPresets} placeholder="输入结束问题标签" onChange={setProblemTags} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">卖出/结束理由</span>
          <textarea className={textareaClass} value={sellReasonText} onChange={(event) => setSellReasonText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">做得好</span>
          <textarea className={textareaClass} value={didWellText} onChange={(event) => setDidWellText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">做错了</span>
          <textarea className={textareaClass} value={didWrongText} onChange={(event) => setDidWrongText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">反思</span>
          <textarea className={textareaClass} value={reflectionText} onChange={(event) => setReflectionText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col lg:col-span-2">
          <span className="text-[10px] font-bold uppercase text-gray-500">规则沉淀</span>
          <textarea className={textareaClass} value={ruleText} onChange={(event) => setRuleText(event.target.value)} required />
        </label>
      </div>

      <div className="flex justify-end">
        {error && <div className="mr-auto self-center text-[11px] text-red-600">{error}</div>}
        <Button type="submit" disabled={submitting} className="h-8 text-[10px] font-bold uppercase tracking-widest bg-gray-900 hover:bg-gray-800">
          {submitting ? '结束中...' : '结束卡片'}
        </Button>
      </div>
    </form>
  );
};
