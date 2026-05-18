import React, { useState } from 'react';
import { CalendarDays, CheckCircle2, Layers3, LineChart, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ReviewPlanStatus, StockReviewCardRequest, StockReviewInitialAction } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { emotionPresets, sectorPresets } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const fieldClass = 'h-10 rounded-md border-slate-200 bg-white px-3 text-[13px] text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:ring-3 focus:ring-sky-100';
const selectClass = `${fieldClass} appearance-auto`;
const textareaClass = 'min-h-24 rounded-md border border-slate-200 bg-white px-3 py-2.5 text-[13px] leading-5 text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:ring-3 focus:ring-sky-100';

interface CardFormProps {
  onSubmit: (payload: StockReviewCardRequest) => Promise<void>;
}

const SectionTitle = ({ icon: Icon, title }: { icon: React.ElementType; title: string }) => (
  <div className="flex items-start gap-3">
    <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-md bg-slate-900 text-white shadow-sm">
      <Icon className="h-4 w-4" />
    </div>
    <div>
      <div className="text-[13px] font-semibold text-slate-900">{title}</div>
    </div>
  </div>
);

const Field = ({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) => (
  <label className={`space-y-1.5 ${className}`}>
    <span className="text-[12px] font-medium text-slate-600">{label}</span>
    {children}
  </label>
);

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
    <form className="space-y-4" onSubmit={submit}>
      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <SectionTitle icon={LineChart} title="标的与周期" />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Field label="股票代码" className="lg:col-span-3">
            <Input value={code} maxLength={6} placeholder="600519" onChange={(event) => setCode(event.target.value)} className={fieldClass} />
          </Field>
          <Field label="股票名称 / 主题" className="lg:col-span-5">
            <Input value={name} placeholder="航天电子，或商业航天观察" onChange={(event) => setName(event.target.value)} className={fieldClass} />
          </Field>
          <Field label="开始日期" className="lg:col-span-4">
            <div className="relative">
              <CalendarDays className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input type="date" value={startDate} max={today()} onChange={(event) => setStartDate(event.target.value)} className={`${fieldClass} pr-10`} />
            </div>
          </Field>
          <Field label="初始动作" className="lg:col-span-4">
            <select className={selectClass} value={initialAction} onChange={(event) => setInitialAction(event.target.value as StockReviewInitialAction)}>
              <option value="BUY">买入建仓</option>
              <option value="WATCH">开始关注</option>
              <option value="PLAN_BUY">计划买入</option>
            </select>
          </Field>
          <Field label="初始仓位" className="lg:col-span-4">
            <select className={selectClass} value={initialPositionContext} onChange={(event) => setInitialPositionContext(event.target.value)}>
              <option value="EMPTY">空仓</option>
              <option value="LIGHT">轻仓</option>
              <option value="HALF">半仓</option>
              <option value="HEAVY">重仓</option>
              <option value="FULL">满仓</option>
              <option value="HOLDING">持有中</option>
            </select>
          </Field>
          <Field label="计划状态" className="lg:col-span-4">
            <select className={selectClass} value={initialPlanStatus} onChange={(event) => setInitialPlanStatus(event.target.value as ReviewPlanStatus)}>
              <option value="PLANNED">计划内</option>
              <option value="UNPLANNED">计划外</option>
              <option value="INTRADAY_ADJUSTMENT">临盘调整</option>
              <option value="OBSERVED_ONLY">观察未执行</option>
            </select>
          </Field>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3">
            <SectionTitle icon={Layers3} title="板块 / 题材" />
          </div>
          <MultiTagInput value={sectorTags} presets={sectorPresets} placeholder="输入板块，例如商业航天" onChange={setSectorTags} />
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3">
            <SectionTitle icon={Sparkles} title="建卡情绪" />
          </div>
          <MultiTagInput value={initialEmotionTags} presets={emotionPresets} placeholder="输入情绪，例如冷静" onChange={setInitialEmotionTags} />
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4">
          <SectionTitle icon={CheckCircle2} title="交易假设" />
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <Field label="买入 / 关注理由">
            <textarea className={textareaClass} value={initialReasonText} placeholder="例：计划内低吸，题材强度仍在。" onChange={(event) => setInitialReasonText(event.target.value)} required />
          </Field>
          <Field label="预期逻辑">
            <textarea className={textareaClass} value={expectedMoveText} placeholder="例：预期放量突破后继续走强。" onChange={(event) => setExpectedMoveText(event.target.value)} />
          </Field>
          <Field label="原计划">
            <textarea className={textareaClass} value={originalPlanText} placeholder="例：跌破五日线离场；冲高不封板减仓。" onChange={(event) => setOriginalPlanText(event.target.value)} />
          </Field>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
        {error && <div className="mr-auto text-[13px] font-medium text-red-600">{error}</div>}
        <Button type="submit" disabled={submitting} className="h-10 rounded-md bg-slate-950 px-5 text-[13px] font-semibold text-white shadow-sm hover:bg-slate-800">
          {submitting ? '保存中...' : '新建标的复盘'}
        </Button>
      </div>
    </form>
  );
};
