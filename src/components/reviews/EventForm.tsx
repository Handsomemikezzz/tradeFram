import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StockReviewEventRequest, StockReviewEventType } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { emotionPresets, problemPresets, stockReviewEventTypeLabel } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const selectClass = 'h-8 rounded border border-gray-200 bg-white px-2 text-[11px]';
const textareaClass = 'min-h-16 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

interface EventFormProps {
  onSubmit: (payload: StockReviewEventRequest) => Promise<void>;
}

export const EventForm = ({ onSubmit }: EventFormProps) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [eventDate, setEventDate] = useState(today());
  const [eventType, setEventType] = useState<StockReviewEventType>('HOLD');
  const [title, setTitle] = useState('');
  const [reasonText, setReasonText] = useState('');
  const [positionSnapshot, setPositionSnapshot] = useState('');
  const [deviatedFromPlan, setDeviatedFromPlan] = useState(false);
  const [emotionTags, setEmotionTags] = useState<string[]>([]);
  const [problemTags, setProblemTags] = useState<string[]>([]);

  const reset = () => {
    setEventDate(today());
    setEventType('HOLD');
    setTitle('');
    setReasonText('');
    setPositionSnapshot('');
    setDeviatedFromPlan(false);
    setEmotionTags([]);
    setProblemTags([]);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({
        eventDate,
        eventType,
        title,
        reasonText,
        positionSnapshot: positionSnapshot.trim() || null,
        deviatedFromPlan,
        emotionTags,
        problemTags,
      });
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存事件失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">日期</span>
          <Input type="date" value={eventDate} max={today()} onChange={(event) => setEventDate(event.target.value)} className="h-8 text-[11px]" required />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">类型</span>
          <select className={selectClass} value={eventType} onChange={(event) => setEventType(event.target.value as StockReviewEventType)}>
            {Object.entries(stockReviewEventTypeLabel).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="space-y-1 md:col-span-2">
          <span className="text-[10px] font-bold uppercase text-gray-500">标题</span>
          <Input value={title} placeholder="例：冲高未封板减仓" onChange={(event) => setTitle(event.target.value)} className="h-8 text-[11px]" required />
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <label className="space-y-1 flex flex-col lg:col-span-2">
          <span className="text-[10px] font-bold uppercase text-gray-500">记录理由</span>
          <textarea className={textareaClass} value={reasonText} placeholder="说明当时观察、动作和判断依据。" onChange={(event) => setReasonText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">仓位快照</span>
          <textarea className={textareaClass} value={positionSnapshot} placeholder="例：半仓持有，浮盈 3%。" onChange={(event) => setPositionSnapshot(event.target.value)} />
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">情绪标签</span>
          <MultiTagInput value={emotionTags} presets={emotionPresets} placeholder="输入情绪标签" onChange={setEmotionTags} />
        </div>
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">问题标签</span>
          <MultiTagInput value={problemTags} presets={problemPresets} placeholder="输入问题标签" onChange={setProblemTags} />
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="inline-flex items-center gap-2 text-[11px] text-gray-600">
          <input type="checkbox" checked={deviatedFromPlan} onChange={(event) => setDeviatedFromPlan(event.target.checked)} className="h-3.5 w-3.5 rounded border-gray-300" />
          偏离原计划
        </label>
        {error && <div className="text-[11px] text-red-600">{error}</div>}
        <Button type="submit" disabled={submitting} className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700">
          {submitting ? '保存中...' : '添加事件'}
        </Button>
      </div>
    </form>
  );
};
