import React, { useState } from 'react';
import { toast } from 'sonner';
import { Calendar, Tag, Smile, AlertCircle, Sparkles, Star, MessageSquareCode, Link2 } from 'lucide-react';

interface ReflectionFormProps {
  onSubmit: (payload: {
    tradeDate: string;
    actionType: string;
    disciplineScore: number;
    emotionTags: string[];
    problemTags: string[];
    reasonText: string;
    reflectionText: string;
    conclusionText: string;
    nextActionText: string;
    outcomeText?: string | null;
  }) => Promise<void>;
  onCancel: () => void;
}

const ACTION_TYPES = ['心法顿悟', '盘后忏悔', '自我对话'];

const EMOTION_OPTIONS = [
  { label: '理性 Calibrated', val: '理智', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  { label: '贪婪 Greedy', val: '贪婪', color: 'bg-rose-50 text-rose-700 border-rose-200' },
  { label: '恐惧 Fearful', val: '恐惧', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  { label: '急躁 Impatient', val: '急躁', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  { label: '焦虑 Anxious', val: '焦虑', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  { label: '自信 Confident', val: '自信', color: 'bg-violet-50 text-violet-700 border-violet-200' },
];

const PROBLEM_OPTIONS = [
  { val: '追高', label: '追高跟风' },
  { val: '抗单', label: '抗单硬撑' },
  { val: '随意交易', label: '随意交易' },
  { val: '重仓', label: '重仓赌博' },
  { val: '提前下车', label: '提前下车/卖飞' },
  { val: '踏空急躁', label: '踏空焦虑' },
];

export const ReflectionForm = ({ onSubmit, onCancel }: ReflectionFormProps) => {
  const [submitting, setSubmitting] = useState(false);
  const [tradeDate, setTradeDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [actionType, setActionType] = useState('心法顿悟');
  const [disciplineScore, setDisciplineScore] = useState(5);
  const [selectedEmotions, setSelectedEmotions] = useState<string[]>([]);
  const [selectedProblems, setSelectedProblems] = useState<string[]>([]);
  
  const [musingsText, setMusingsText] = useState('');
  const [externalUrl, setExternalUrl] = useState('');

  const toggleEmotion = (emotion: string) => {
    if (selectedEmotions.includes(emotion)) {
      setSelectedEmotions(selectedEmotions.filter((e) => e !== emotion));
    } else {
      setSelectedEmotions([...selectedEmotions, emotion]);
    }
  };

  const toggleProblem = (problem: string) => {
    if (selectedProblems.includes(problem)) {
      setSelectedProblems(selectedProblems.filter((p) => p !== problem));
    } else {
      setSelectedProblems([...selectedProblems, problem]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!musingsText.trim()) {
      toast.error('写点牢骚或者心得再保存吧！');
      return;
    }

    setSubmitting(true);
    try {
      // Map single textbox text to conclusionText (the main musings).
      // Fill standard placeholder '-' to other required DB fields to pass API validation.
      await onSubmit({
        tradeDate,
        actionType,
        disciplineScore,
        emotionTags: selectedEmotions,
        problemTags: selectedProblems.length > 0 ? selectedProblems : ['自我管理'],
        reasonText: '-',
        reflectionText: '-',
        conclusionText: musingsText.trim(),
        nextActionText: '-',
        outcomeText: externalUrl.trim() || null,
      });
      // Success toast handled in parent
    } catch (err) {
      // Error toast handled in parent
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-5 animate-in fade-in duration-200">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <h4 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          <Sparkles className="h-4.5 w-4.5 text-blue-600 animate-pulse" />
          记一笔交易随感 (朋友圈说说)
        </h4>
        <span className="text-[10px] text-slate-400 font-mono">Dojo moments creator</span>
      </div>

      {/* Date, Type, Score row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Date */}
        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" /> 交易日期
          </label>
          <input
            type="date"
            required
            max={new Date().toISOString().slice(0, 10)}
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
            className="w-full h-9 rounded border border-slate-200 bg-white px-3 text-xs outline-none focus:ring-2 focus:ring-blue-100 font-mono"
          />
        </div>

        {/* Type */}
        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
            <Smile className="h-3.5 w-3.5" /> 说说分类
          </label>
          <div className="grid grid-cols-3 gap-1">
            {ACTION_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setActionType(type)}
                className={`h-9 text-[11px] font-semibold rounded border transition-all ${
                  actionType === type
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {/* Discipline Score (Stars) */}
        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
            <Star className="h-3.5 w-3.5" /> 今日纪律得分
          </label>
          <div className="flex h-9 items-center gap-1.5 bg-slate-50 rounded border border-slate-100 px-3">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setDisciplineScore(star)}
                className="transition-transform active:scale-90"
              >
                <Star
                  className={`h-5 w-5 ${
                    star <= disciplineScore
                      ? 'fill-amber-400 text-amber-400'
                      : 'text-slate-300'
                  }`}
                />
              </button>
            ))}
            <span className="ml-auto text-[11px] font-mono font-bold text-slate-600">
              {disciplineScore} / 5
            </span>
          </div>
        </div>
      </div>

      {/* Emotion Tags Selector */}
      <div className="space-y-1.5">
        <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
          <Tag className="h-3.5 w-3.5" /> 我的心理状态 (多选)
        </label>
        <div className="flex flex-wrap gap-1.5">
          {EMOTION_OPTIONS.map((opt) => {
            const active = selectedEmotions.includes(opt.val);
            return (
              <button
                key={opt.val}
                type="button"
                onClick={() => toggleEmotion(opt.val)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-all flex items-center gap-1 ${
                  active
                    ? `${opt.color} ring-2 ring-blue-500/20 shadow-xs`
                    : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Problem/Trap Tags Selector */}
      <div className="space-y-1.5">
        <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
          <AlertCircle className="h-3.5 w-3.5" /> 触发的战术问题 (可多选，关联左侧铁律卡)
        </label>
        <div className="flex flex-wrap gap-1.5">
          {PROBLEM_OPTIONS.map((opt) => {
            const active = selectedProblems.includes(opt.val);
            return (
              <button
                key={opt.val}
                type="button"
                onClick={() => toggleProblem(opt.val)}
                className={`px-3 py-1 rounded border text-xs font-semibold transition-all ${
                  active
                    ? 'border-rose-300 bg-rose-50 text-rose-700 shadow-xs ring-2 ring-rose-500/10'
                    : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Single Consolidated Rant Box */}
      <div className="flex flex-col space-y-1.5">
        <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
          <MessageSquareCode className="h-3.5 w-3.5 text-blue-600" />
          今日盘后牢骚与碎碎念 / 随笔日记 (支持 Markdown)
        </label>
        <textarea
          required
          rows={5}
          value={musingsText}
          onChange={(e) => setMusingsText(e.target.value)}
          placeholder="吐槽一下盘后的牢骚、今天交易时让你拍大腿的真实心态、被拉升行情诱多追高的经历，或者灵光一闪的心法顿悟...（排遣情绪，不设格式约束，想怎么写就怎么写！）"
          className="w-full rounded-lg border border-slate-200 bg-white p-3 text-xs outline-none focus:ring-2 focus:ring-blue-100 leading-relaxed font-sans"
        />
        <div className="text-right text-[10px] text-slate-400">
          已输入 {musingsText.length} 字
        </div>
      </div>

      {/* External Reference Link Input */}
      <div className="flex flex-col space-y-1.5 animate-in fade-in duration-200">
        <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <Link2 className="h-3.5 w-3.5 text-blue-500" />
          关联外部参考链接 (URL) - 可选
        </label>
        <input
          type="url"
          value={externalUrl}
          onChange={(e) => setExternalUrl(e.target.value)}
          placeholder="把触发你灵感或牢骚的文章、微博、推贴、雪球讨论链接复制到这里..."
          className="w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs outline-none focus:ring-2 focus:ring-blue-100 placeholder:text-slate-400"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-2.5 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="h-9 px-4 rounded-md border border-slate-200 bg-white text-xs font-semibold text-slate-600 shadow-xs hover:bg-slate-50"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="h-9 px-5 rounded-md bg-blue-600 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors flex items-center gap-1.5"
        >
          {submitting ? (
            <>
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              写入说说中...
            </>
          ) : (
            '发表这笔说说'
          )}
        </button>
      </div>
    </form>
  );
};
