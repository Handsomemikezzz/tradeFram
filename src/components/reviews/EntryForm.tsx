import React, { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ReviewEntryRequest, ReviewEntryType, ReviewPlanStatus } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { emotionPresets, problemPresets, sectorPresets } from './reviewLabels';

const PLACEHOLDERS = {
  reasonText: '例：看到神剑封板后，担心航天后排补涨，临盘追入航发中。',
  reflectionText: '这次主要是策略问题、判断问题、执行问题，还是情绪问题？',
  conclusionText: '例：计划外追后排，纪律评分偏低。',
  nextActionText: '写成一句未来可执行的话，例如：缩量反弹不加仓。',
  outcomeText: '例：次日低开，验证追高风险；或：暂未验证。',
};

const tradeActions = [
  ['BUY', '买入'],
  ['SELL', '卖出'],
  ['ADD', '加仓'],
  ['REDUCE', '减仓'],
  ['CLEAR', '清仓'],
  ['DO_T', '做 T'],
];

const observationActions = [
  ['WANTED_BUY', '想买未买'],
  ['WANTED_SELL', '想卖未卖'],
  ['CANCELLED_ORDER', '撤单'],
  ['HELD_BACK', '忍住没动'],
  ['PLAN_OBSERVE', '计划观察'],
];

const today = () => new Date().toISOString().slice(0, 10);

interface EntryFormProps {
  onSubmit: (payload: ReviewEntryRequest) => Promise<void>;
}

const selectClass = 'h-8 rounded border border-gray-200 bg-white px-2 text-[11px]';
const textareaClass = 'min-h-20 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

export const EntryForm = ({ onSubmit }: EntryFormProps) => {
  const [submitting, setSubmitting] = useState(false);
  const [entryType, setEntryType] = useState<ReviewEntryType>('TRADE_ACTION');
  const [actionType, setActionType] = useState('BUY');
  const [tradeDate, setTradeDate] = useState(today());
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [sectorTags, setSectorTags] = useState<string[]>([]);
  const [positionContext, setPositionContext] = useState('LIGHT');
  const [planStatus, setPlanStatus] = useState<ReviewPlanStatus>('PLANNED');
  const [emotionTags, setEmotionTags] = useState<string[]>([]);
  const [problemTags, setProblemTags] = useState<string[]>([]);
  const [reasonText, setReasonText] = useState('');
  const [reflectionText, setReflectionText] = useState('');
  const [conclusionText, setConclusionText] = useState('');
  const [nextActionText, setNextActionText] = useState('');
  const [outcomeText, setOutcomeText] = useState('');
  const [disciplineScore, setDisciplineScore] = useState(3);

  const actions = useMemo(() => (entryType === 'TRADE_ACTION' ? tradeActions : observationActions), [entryType]);

  const changeEntryType = (value: ReviewEntryType) => {
    setEntryType(value);
    setActionType(value === 'TRADE_ACTION' ? 'BUY' : 'WANTED_BUY');
    setPlanStatus(value === 'TRADE_ACTION' ? 'PLANNED' : 'OBSERVED_ONLY');
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        entryType,
        actionType,
        tradeDate,
        code: code.trim() || null,
        name: name.trim() || null,
        sectorTags,
        positionContext,
        planStatus,
        emotionTags,
        problemTags,
        reasonText,
        reflectionText,
        conclusionText,
        nextActionText,
        disciplineScore,
        outcomeText: outcomeText.trim() || null,
      });
      setReasonText('');
      setReflectionText('');
      setConclusionText('');
      setNextActionText('');
      setOutcomeText('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-5" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">记录类型</span>
          <select className={selectClass} value={entryType} onChange={(event) => changeEntryType(event.target.value as ReviewEntryType)}>
            <option value="TRADE_ACTION">交易行为</option>
            <option value="OBSERVATION_DECISION">观察决策</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">行为类型</span>
          <select className={selectClass} value={actionType} onChange={(event) => setActionType(event.target.value)}>
            {actions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">发生日期</span>
          <Input type="date" value={tradeDate} max={today()} onChange={(event) => setTradeDate(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">纪律评分</span>
          <select className={selectClass} value={disciplineScore} onChange={(event) => setDisciplineScore(Number(event.target.value))}>
            {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">股票代码</span>
          <Input value={code} maxLength={6} placeholder="可为空，例如 600519" onChange={(event) => setCode(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">股票名称</span>
          <Input value={name} placeholder="可手动填写，例如 航天电子" onChange={(event) => setName(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">仓位语境</span>
          <select className={selectClass} value={positionContext} onChange={(event) => setPositionContext(event.target.value)}>
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
          <select className={selectClass} value={planStatus} onChange={(event) => setPlanStatus(event.target.value as ReviewPlanStatus)}>
            <option value="PLANNED">计划内</option>
            <option value="UNPLANNED">计划外</option>
            <option value="INTRADAY_ADJUSTMENT">临盘调整</option>
            <option value="OBSERVED_ONLY">观察未执行</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">板块/题材</span>
          <MultiTagInput value={sectorTags} presets={sectorPresets} placeholder="输入板块，例如 商业航天" onChange={setSectorTags} />
        </div>
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">情绪标签</span>
          <MultiTagInput value={emotionTags} presets={emotionPresets} placeholder="输入情绪，例如 怕踏空" onChange={setEmotionTags} />
        </div>
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">问题归因</span>
          <MultiTagInput value={problemTags} presets={problemPresets} placeholder="输入归因，例如 仓位问题" onChange={setProblemTags} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">为什么这么做</span>
          <textarea className={textareaClass} value={reasonText} placeholder={PLACEHOLDERS.reasonText} onChange={(event) => setReasonText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">盘后反思</span>
          <textarea className={textareaClass} value={reflectionText} placeholder={PLACEHOLDERS.reflectionText} onChange={(event) => setReflectionText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">一句话结论</span>
          <textarea className={textareaClass} value={conclusionText} placeholder={PLACEHOLDERS.conclusionText} onChange={(event) => setConclusionText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">下次动作</span>
          <textarea className={textareaClass} value={nextActionText} placeholder={PLACEHOLDERS.nextActionText} onChange={(event) => setNextActionText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col lg:col-span-2">
          <span className="text-[10px] font-bold uppercase text-gray-500">结果验证</span>
          <textarea className={textareaClass} value={outcomeText} placeholder={PLACEHOLDERS.outcomeText} onChange={(event) => setOutcomeText(event.target.value)} />
        </label>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700">
          {submitting ? '保存中...' : '保存复盘记录'}
        </Button>
      </div>
    </form>
  );
};
