import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StockReviewEventRequest, StockReviewEventType } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { MultiImageUpload } from './MultiImageUpload';
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
  const [reasonText, setReasonText] = useState('');
  const [positionSnapshot, setPositionSnapshot] = useState('');
  const [deviatedFromPlan, setDeviatedFromPlan] = useState(false);
  const [emotionTags, setEmotionTags] = useState<string[]>([]);
  const [problemTags, setProblemTags] = useState<string[]>([]);
  const [images, setImages] = useState<string[]>([]);

  const reset = () => {
    setEventDate(today());
    setEventType('HOLD');
    setReasonText('');
    setPositionSnapshot('');
    setDeviatedFromPlan(false);
    setEmotionTags([]);
    setProblemTags([]);
    setImages([]);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({
        eventDate,
        eventType,
        title: stockReviewEventTypeLabel[eventType] || eventType,
        reasonText,
        positionSnapshot: positionSnapshot.trim() || null,
        deviatedFromPlan,
        emotionTags,
        problemTags,
        images,
      });
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存事件失败');
    } finally {
      setSubmitting(false);
    }
  };

  const typeConfigs: Record<StockReviewEventType, { label: string; activeClass: string; color: string }> = {
    HOLD: { label: '继续持有', color: 'slate', activeClass: 'bg-slate-100 border-slate-500 text-slate-800 ring-2 ring-slate-200/50' },
    ADD: { label: '加仓', color: 'emerald', activeClass: 'bg-emerald-50/80 border-emerald-500 text-emerald-700 ring-2 ring-emerald-100' },
    REDUCE: { label: '减仓', color: 'amber', activeClass: 'bg-amber-50/80 border-amber-400 text-amber-700 ring-2 ring-amber-100' },
    SELL: { label: '卖出', color: 'rose', activeClass: 'bg-rose-50/80 border-rose-500 text-rose-700 ring-2 ring-rose-100' },
    DO_T: { label: '做 T', color: 'indigo', activeClass: 'bg-indigo-50/80 border-indigo-500 text-indigo-700 ring-2 ring-indigo-100' },
    PLAN_CHANGE: { label: '计划变化', color: 'blue', activeClass: 'bg-blue-50/80 border-blue-500 text-blue-700 ring-2 ring-blue-100' },
    EMOTION: { label: '情绪波动', color: 'orange', activeClass: 'bg-orange-50/80 border-orange-500 text-orange-700 ring-2 ring-orange-100' },
    OBSERVATION: { label: '观察记录', color: 'violet', activeClass: 'bg-violet-50/80 border-violet-500 text-violet-700 ring-2 ring-violet-100' },
  };

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end bg-slate-50/30 p-4 rounded-xl border border-slate-100">
        <label className="space-y-1.5 md:col-span-3 flex flex-col">
          <span className="text-[11px] font-bold text-slate-500">记录日期</span>
          <Input 
            type="date" 
            value={eventDate} 
            max={today()} 
            onChange={(event) => setEventDate(event.target.value)} 
            className="h-10 text-[13px] rounded-lg border-slate-200 bg-white px-3 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all outline-none" 
            required 
          />
        </label>
        
        <div className="flex flex-col space-y-1.5 md:col-span-9">
          <span className="text-[11px] font-bold text-slate-500">事件类型</span>
          <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-1.5">
            {Object.entries(stockReviewEventTypeLabel).map(([value, label]) => {
              const itemValue = value as StockReviewEventType;
              const active = eventType === itemValue;
              const config = typeConfigs[itemValue] || { label, activeClass: 'bg-slate-100 border-slate-500 text-slate-800' };
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setEventType(itemValue)}
                  className={`py-2 px-1 rounded-lg border text-center text-[12px] font-semibold transition-all duration-200 ${
                    active 
                      ? config.activeClass 
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
                  }`}
                >
                  {config.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100 lg:col-span-2">
          <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
              过程记录理由 <span className="text-[10px] text-rose-500 font-bold">*</span>
            </span>
            <span className="text-[9px] text-slate-400 font-mono tracking-wider uppercase">REASON / MEMO</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-20 resize-none leading-relaxed"
            value={reasonText}
            placeholder="请详尽说明当时市场环境、个股走势、你的情绪状态以及买入/加仓/观察的依据。"
            onChange={(event) => setReasonText(event.target.value)}
            required
          />
        </div>

        <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
          <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              仓位快照
            </span>
            <span className="text-[9px] text-slate-400 font-mono tracking-wider uppercase">SNAPSHOT</span>
          </div>
          <textarea
            className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-20 resize-none leading-relaxed"
            value={positionSnapshot}
            placeholder="例：半仓持有，浮盈 3%，持仓成本线位于支撑位上方。"
            onChange={(event) => setPositionSnapshot(event.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800">过程情绪</span>
            <span className="text-[9px] text-slate-400 font-mono">EMOTIONS</span>
          </div>
          <MultiTagInput value={emotionTags} presets={emotionPresets} placeholder="输入情绪标签" onChange={setEmotionTags} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-[12px] font-semibold text-slate-800">发现问题</span>
            <span className="text-[9px] text-slate-400 font-mono">PROBLEMS</span>
          </div>
          <MultiTagInput value={problemTags} presets={problemPresets} placeholder="输入发现的问题标签" onChange={setProblemTags} />
        </div>
      </div>

      <div className="pt-3 border-t border-slate-100">
        <MultiImageUpload images={images} onChange={setImages} label="过程走势图表 (支持拖拽/多图上传)" />
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-3 border-t border-slate-100">
        <div className="w-full sm:max-w-md">
          <div 
            onClick={() => setDeviatedFromPlan(!deviatedFromPlan)}
            className={`flex items-center justify-between p-3 rounded-xl border-2 transition-all duration-300 cursor-pointer select-none ${
              deviatedFromPlan 
                ? 'bg-rose-50 border-rose-400 text-rose-800 shadow-sm ring-2 ring-rose-100' 
                : 'bg-slate-50/50 border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className={`h-2 w-2 rounded-full ${deviatedFromPlan ? 'bg-rose-500 animate-pulse' : 'bg-slate-400'}`} />
              <div>
                <div className="text-[12px] font-bold">是否偏离原计划</div>
                <div className="text-[9px] text-slate-400 mt-0.5">偏离买入时设定的止损止盈或操作节奏</div>
              </div>
            </div>
            <div className="flex items-center">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                deviatedFromPlan ? 'bg-rose-600 text-white' : 'bg-slate-200 text-slate-600'
              }`}>
                {deviatedFromPlan ? '⚠️ 偏离计划' : '✅ 遵守计划'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 w-full sm:w-auto">
          {error && <div className="text-[12px] font-semibold text-rose-600 mr-2">{error}</div>}
          <Button 
            type="submit" 
            disabled={submitting} 
            className="h-10 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[12px] font-bold px-6 shadow-md transition-all hover:scale-[1.02] active:scale-[0.98] w-full sm:w-auto"
          >
            {submitting ? '保存中...' : '记录过程事件'}
          </Button>
        </div>
      </div>
    </form>
  );
};
