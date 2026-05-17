import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ReviewPlanStatus, StockReviewCardRequest, StockReviewInitialAction } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { emotionPresets, sectorPresets } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const selectClass = 'h-8 rounded border border-gray-200 bg-white px-2 text-[11px]';
const textareaClass = 'min-h-20 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

interface CardFormProps {
  onSubmit: (payload: StockReviewCardRequest) => Promise<void>;
}

export const CardForm = ({ onSubmit }: CardFormProps) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [sectorTags, setSectorTags] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(today());
  const [initialAction, setInitialAction] = useState<StockReviewInitialAction>('BUY');
  const [initialPositionContext, setInitialPositionContext] = useState('LIGHT');
  const [initialPlanStatus, setInitialPlanStatus] = useState<ReviewPlanStatus>('PLANNED');
  const [initialEmotionTags, setInitialEmotionTags] = useState<string[]>([]);
  const [initialReasonText, setInitialReasonText] = useState('');
  const [expectedMoveText, setExpectedMoveText] = useState('');
  const [originalPlanText, setOriginalPlanText] = useState('');

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!code.trim() && !name.trim()) {
      setError('请填写股票代码或股票名称/主题。');
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        code: code.trim() || null,
        name: name.trim() || null,
        sectorTags,
        startDate,
        initialAction,
        initialPositionContext,
        initialPlanStatus,
        initialEmotionTags,
        initialReasonText,
        expectedMoveText,
        originalPlanText,
      });
      setCode('');
      setName('');
      setSectorTags([]);
      setInitialEmotionTags([]);
      setInitialReasonText('');
      setExpectedMoveText('');
      setOriginalPlanText('');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-5" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">股票代码</span>
          <Input value={code} maxLength={6} placeholder="可为空，例如 600519" onChange={(event) => setCode(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">股票名称/主题</span>
          <Input value={name} placeholder="例如 航天电子，或 商业航天观察" onChange={(event) => setName(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">开始日期</span>
          <Input type="date" value={startDate} max={today()} onChange={(event) => setStartDate(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">初始动作</span>
          <select className={selectClass} value={initialAction} onChange={(event) => setInitialAction(event.target.value as StockReviewInitialAction)}>
            <option value="BUY">买入建仓</option>
            <option value="WATCH">开始关注</option>
            <option value="PLAN_BUY">计划买入</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">初始仓位</span>
          <select className={selectClass} value={initialPositionContext} onChange={(event) => setInitialPositionContext(event.target.value)}>
            <option value="EMPTY">空仓</option>
            <option value="LIGHT">轻仓</option>
            <option value="HALF">半仓</option>
            <option value="HEAVY">重仓</option>
            <option value="FULL">满仓</option>
            <option value="HOLDING">持有中</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">计划状态</span>
          <select className={selectClass} value={initialPlanStatus} onChange={(event) => setInitialPlanStatus(event.target.value as ReviewPlanStatus)}>
            <option value="PLANNED">计划内</option>
            <option value="UNPLANNED">计划外</option>
            <option value="INTRADAY_ADJUSTMENT">临盘调整</option>
            <option value="OBSERVED_ONLY">观察未执行</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">板块/题材</span>
          <MultiTagInput value={sectorTags} presets={sectorPresets} placeholder="输入板块，例如 商业航天" onChange={setSectorTags} />
        </div>
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">建卡情绪</span>
          <MultiTagInput value={initialEmotionTags} presets={emotionPresets} placeholder="输入情绪，例如 冷静" onChange={setInitialEmotionTags} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">买入/关注理由</span>
          <textarea className={textareaClass} value={initialReasonText} placeholder="例：计划内低吸，题材强度仍在。" onChange={(event) => setInitialReasonText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">预期逻辑</span>
          <textarea className={textareaClass} value={expectedMoveText} placeholder="例：预期放量突破后继续走强。" onChange={(event) => setExpectedMoveText(event.target.value)} />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">原计划</span>
          <textarea className={textareaClass} value={originalPlanText} placeholder="例：跌破五日线离场；冲高不封板减仓。" onChange={(event) => setOriginalPlanText(event.target.value)} />
        </label>
      </div>

      <div className="flex justify-end">
        {error && <div className="mr-auto self-center text-[11px] text-red-600">{error}</div>}
        <Button type="submit" disabled={submitting} className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700">
          {submitting ? '保存中...' : '新建标的复盘'}
        </Button>
      </div>
    </form>
  );
};
