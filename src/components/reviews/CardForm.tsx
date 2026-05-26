import React, { useState } from 'react';
import { CalendarDays, CheckCircle2, Layers3, LineChart, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ReviewPlanStatus, StockReviewCardRequest, StockReviewInitialAction } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { MultiImageUpload } from './MultiImageUpload';
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
  const [initialImages, setInitialImages] = useState<string[]>([]);

  // Professional Trading Audit Fields
  const [strategyType, setStrategyType] = useState<string | null>(null);
  const [expectedRrRatio, setExpectedRrRatio] = useState('');
  const [stopLossTarget, setStopLossTarget] = useState('');

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
        initialImages,
        
        // Professional Trading Audit Fields
        strategyType,
        expectedRrRatio: expectedRrRatio.trim() || null,
        stopLossTarget: stopLossTarget.trim() || null,
      });
      setCode('');
      setName('');
      setSectorTags([]);
      setInitialEmotionTags([]);
      setInitialReasonText('');
      setExpectedMoveText('');
      setOriginalPlanText('');
      setInitialImages([]);
      
      setStrategyType(null);
      setExpectedRrRatio('');
      setStopLossTarget('');
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-3">
          <SectionTitle icon={LineChart} title="标的与周期" />
          <span className="text-[11px] text-slate-400 font-medium">Target & Cycle Configuration</span>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Field label="股票代码" className="lg:col-span-3">
            <Input 
              value={code} 
              maxLength={6} 
              placeholder="600519" 
              onChange={(event) => setCode(event.target.value)} 
              className="h-10 rounded-lg border-slate-200 bg-white px-3 text-[13px] text-slate-900 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all placeholder:text-slate-400 outline-none" 
            />
          </Field>
          <Field label="股票名称 / 主题" className="lg:col-span-5">
            <Input 
              value={name} 
              placeholder="航天电子，或商业航天观察" 
              onChange={(event) => setName(event.target.value)} 
              className="h-10 rounded-lg border-slate-200 bg-white px-3 text-[13px] text-slate-900 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all placeholder:text-slate-400 outline-none" 
            />
          </Field>
          <Field label="开始日期" className="lg:col-span-4">
            <div className="relative">
              <CalendarDays className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input 
                type="date" 
                value={startDate} 
                max={today()} 
                onChange={(event) => setStartDate(event.target.value)} 
                className="h-10 rounded-lg border-slate-200 bg-white pl-3 pr-10 text-[13px] text-slate-900 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all outline-none" 
              />
            </div>
          </Field>

          {/* Interactive Button groups replacing standard <select> */}
          <div className="flex flex-col space-y-1.5 lg:col-span-4">
            <span className="text-[12px] font-semibold text-slate-700">初始动作</span>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 'BUY', label: '买入建仓', desc: '新入场多头', color: 'emerald' },
                { value: 'WATCH', label: '开始关注', desc: '列入监控池', color: 'slate' },
                { value: 'PLAN_BUY', label: '计划买入', desc: '设定买点', color: 'amber' },
              ].map((item) => {
                const active = initialAction === item.value;
                const activeClasses = 
                  item.value === 'BUY' ? 'bg-emerald-50/80 border-emerald-500 text-emerald-700 ring-2 ring-emerald-100 shadow-sm' :
                  item.value === 'WATCH' ? 'bg-slate-100 border-slate-500 text-slate-800 ring-2 ring-slate-200/50 shadow-sm' :
                  'bg-amber-50/80 border-amber-500 text-amber-700 ring-2 ring-amber-100 shadow-sm';
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setInitialAction(item.value as StockReviewInitialAction)}
                    className={`flex flex-col items-center justify-center p-2 rounded-xl border text-center transition-all duration-200 ${
                      active 
                        ? activeClasses 
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
                    }`}
                  >
                    <span className="text-[13px] font-semibold">{item.label}</span>
                    <span className={`text-[10px] ${active ? 'opacity-85' : 'text-slate-400'} mt-0.5`}>{item.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col space-y-1.5 lg:col-span-4">
            <span className="text-[12px] font-semibold text-slate-700">初始仓位</span>
            <div className="grid grid-cols-6 gap-1">
              {[
                { value: 'EMPTY', label: '空仓', pct: '0%', activeClass: 'bg-slate-50 border-slate-400 text-slate-800 ring-2 ring-slate-100 shadow-sm' },
                { value: 'LIGHT', label: '轻仓', pct: '20%', activeClass: 'bg-emerald-50/80 border-emerald-400 text-emerald-700 ring-2 ring-emerald-100 shadow-sm' },
                { value: 'HALF', label: '半仓', pct: '50%', activeClass: 'bg-amber-50/80 border-amber-400 text-amber-700 ring-2 ring-amber-100 shadow-sm' },
                { value: 'HEAVY', label: '重仓', pct: '80%', activeClass: 'bg-orange-50/80 border-orange-400 text-orange-700 ring-2 ring-orange-100 shadow-sm' },
                { value: 'FULL', label: '满仓', pct: '100%', activeClass: 'bg-rose-50/80 border-rose-400 text-rose-700 ring-2 ring-rose-100 shadow-sm' },
                { value: 'HOLDING', label: '持有', pct: '🔄', activeClass: 'bg-indigo-50/80 border-indigo-400 text-indigo-700 ring-2 ring-indigo-100 shadow-sm' },
              ].map((item) => {
                const active = initialPositionContext === item.value;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setInitialPositionContext(item.value)}
                    className={`flex flex-col items-center justify-center py-2 px-0.5 rounded-lg border text-center transition-all duration-200 ${
                      active 
                        ? item.activeClass
                        : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
                    }`}
                  >
                    <span className="text-[12px] font-bold">{item.label}</span>
                    <span className="text-[9px] font-mono opacity-80 mt-0.5">{item.pct}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col space-y-1.5 lg:col-span-4">
            <span className="text-[12px] font-semibold text-slate-700">计划状态</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { value: 'PLANNED', label: '计划内', activeClass: 'bg-emerald-600 border-emerald-600 text-white shadow-sm ring-2 ring-emerald-100 hover:bg-emerald-700' },
                { value: 'UNPLANNED', label: '计划外', activeClass: 'bg-rose-600 border-rose-600 text-white shadow-sm ring-2 ring-rose-100 hover:bg-rose-700' },
                { value: 'INTRADAY_ADJUSTMENT', label: '临盘调整', activeClass: 'bg-amber-600 border-amber-600 text-white shadow-sm ring-2 ring-amber-100 hover:bg-amber-700' },
                { value: 'OBSERVED_ONLY', label: '仅观察', activeClass: 'bg-blue-600 border-blue-600 text-white shadow-sm ring-2 ring-blue-100 hover:bg-blue-700' },
              ].map((item) => {
                const active = initialPlanStatus === item.value;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setInitialPlanStatus(item.value as ReviewPlanStatus)}
                    className={`flex items-center justify-center py-2 px-1 rounded-xl border text-center text-[12px] font-semibold transition-all duration-200 ${
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

          {/* Divider */}
          <div className="w-full h-px bg-slate-200/60 my-2 lg:col-span-12" />

          {/* Professional Strategy Setup & Risk Control Row */}
          <div className="flex flex-col space-y-1.5 lg:col-span-6">
            <span className="text-[12px] font-semibold text-slate-700 flex items-center gap-1.5">
              交易策略 / 模式
              <span className="text-[10px] text-slate-400 font-mono font-medium bg-slate-100 px-1.5 py-0.5 rounded">Setup</span>
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-1.5">
              {[
                { value: 'MOMENTUM_BREAKOUT', label: '动量突破', activeClass: 'bg-rose-50 border-rose-400 text-rose-700 ring-2 ring-rose-100 shadow-sm' },
                { value: 'MEAN_REVERSION', label: '分歧低吸', activeClass: 'bg-emerald-50 border-emerald-400 text-emerald-700 ring-2 ring-emerald-100 shadow-sm' },
                { value: 'TREND_FOLLOWING', label: '趋势追踪', activeClass: 'bg-indigo-50 border-indigo-400 text-indigo-700 ring-2 ring-indigo-100 shadow-sm' },
                { value: 'EVENT_DRIVEN', label: '事件驱动', activeClass: 'bg-purple-50 border-purple-400 text-purple-700 ring-2 ring-purple-100 shadow-sm' },
                { value: 'VOLATILITY_GRID', label: '网格震荡', activeClass: 'bg-slate-100 border-slate-400 text-slate-800 ring-2 ring-slate-200 shadow-sm' },
              ].map((item) => {
                const active = strategyType === item.value;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setStrategyType(active ? null : item.value)}
                    className={`py-2 px-0.5 rounded-xl border text-center text-[12px] font-semibold transition-all duration-200 ${
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

          <div className="grid grid-cols-2 gap-4 lg:col-span-6">
            <Field label="预期盈亏比 (E.g. 3:1)">
              <Input 
                value={expectedRrRatio} 
                placeholder="3:1" 
                onChange={(event) => setExpectedRrRatio(event.target.value)} 
                className="h-10 rounded-lg border-slate-200 bg-white px-3 text-[13px] text-slate-900 shadow-sm focus:border-slate-800 focus:ring-4 focus:ring-slate-100 transition-all placeholder:text-slate-400 outline-none" 
              />
            </Field>
            
            <Field label="硬性核反应止损位">
              <div className="relative">
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-rose-500 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100 select-none">STOP</span>
                <Input 
                  value={stopLossTarget} 
                  placeholder="例：-5% 或 18.50元" 
                  onChange={(event) => setStopLossTarget(event.target.value)} 
                  className="h-10 rounded-lg border-slate-200 bg-white pl-3 pr-14 text-[13px] text-slate-900 shadow-sm focus:border-rose-500 focus:ring-4 focus:ring-rose-50 transition-all placeholder:text-slate-400 outline-none" 
                />
              </div>
            </Field>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="mb-3.5 flex items-center justify-between border-b border-slate-100 pb-2">
            <SectionTitle icon={Layers3} title="板块 / 题材" />
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">Sectors</span>
          </div>
          <MultiTagInput value={sectorTags} presets={sectorPresets} placeholder="输入板块，例如商业航天" onChange={setSectorTags} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="mb-3.5 flex items-center justify-between border-b border-slate-100 pb-2">
            <SectionTitle icon={Sparkles} title="建仓情绪" />
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">Emotions</span>
          </div>
          <MultiTagInput value={initialEmotionTags} presets={emotionPresets} placeholder="输入情绪，例如冷静" onChange={setInitialEmotionTags} />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
        <div className="mb-2 flex items-center justify-between">
          <SectionTitle icon={CheckCircle2} title="交易假设 & 核心逻辑" />
          <span className="text-[11px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100 font-medium">Strategic Planning</span>
        </div>
        
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {/* Buy Reason */}
          <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
            <div className="mb-2.5 flex items-center justify-between border-b border-slate-100 pb-1.5">
              <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                买入 / 关注理由 <span className="text-[10px] text-rose-500 font-bold">*</span>
              </span>
              <span className="text-[9px] text-slate-400 font-mono tracking-wider uppercase">REASON</span>
            </div>
            <textarea
              className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-24 resize-none leading-relaxed"
              value={initialReasonText}
              placeholder="例：计划内低吸，题材强度仍在，承接盘力量强。"
              onChange={(event) => setInitialReasonText(event.target.value)}
              required
            />
          </div>

          {/* Expected Logic */}
          <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
            <div className="mb-2.5 flex items-center justify-between border-b border-slate-100 pb-1.5">
              <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                预期逻辑
              </span>
              <span className="text-[9px] text-slate-400 font-mono tracking-wider uppercase">EXPECTATION</span>
            </div>
            <textarea
              className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-24 resize-none leading-relaxed"
              value={expectedMoveText}
              placeholder="例：预期放量突破前高，回踩确认后继续走强。"
              onChange={(event) => setExpectedMoveText(event.target.value)}
            />
          </div>

          {/* Original Plan */}
          <div className="group rounded-xl border border-slate-200 bg-slate-50/30 p-4 transition-all duration-300 hover:shadow-md hover:bg-white focus-within:border-slate-800 focus-within:ring-4 focus-within:ring-slate-100">
            <div className="mb-2.5 flex items-center justify-between border-b border-slate-100 pb-1.5">
              <span className="text-[12px] font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                原计划
              </span>
              <span className="text-[9px] text-slate-400 font-mono tracking-wider uppercase">PLAN</span>
            </div>
            <textarea
              className="w-full bg-transparent border-0 p-0 text-[13px] text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none min-h-24 resize-none leading-relaxed"
              value={originalPlanText}
              placeholder="例：跌破五日均线离场；冲高拉稀无量分时背离减仓。"
              onChange={(event) => setOriginalPlanText(event.target.value)}
            />
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-100">
          <MultiImageUpload images={initialImages} onChange={setInitialImages} label="建仓走势图表 (支持拖拽/多图上传)" />
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        {error && <div className="mr-auto text-[13px] font-semibold text-rose-600">{error}</div>}
        <Button 
          type="submit" 
          disabled={submitting} 
          className="h-10 rounded-lg bg-slate-900 px-6 text-[13px] font-semibold text-white shadow-sm hover:bg-slate-800 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          {submitting ? '保存中...' : '新建标的复盘'}
        </Button>
      </div>
    </form>
  );
};
