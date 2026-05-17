import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { WeeklyReviewRequest, WeeklyWorkbenchResponse } from '@/services/api';
import { EntryList } from './EntryList';

interface WeeklyWorkbenchProps {
  data: WeeklyWorkbenchResponse | null;
  onSave: (payload: WeeklyReviewRequest) => Promise<void>;
}

const textareaClass = 'min-h-20 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

export const WeeklyWorkbench = ({ data, onSave }: WeeklyWorkbenchProps) => {
  const [saving, setSaving] = useState(false);
  const [summaryText, setSummaryText] = useState('');
  const [repeatedMistakesText, setRepeatedMistakesText] = useState('');
  const [effectiveActionsText, setEffectiveActionsText] = useState('');
  const [emotionPatternText, setEmotionPatternText] = useState('');
  const [nextWeekFocusText, setNextWeekFocusText] = useState('');
  const [ruleCandidatesText, setRuleCandidatesText] = useState('');

  useEffect(() => {
    setSummaryText(data?.weeklyReview?.summaryText || '');
    setRepeatedMistakesText(data?.weeklyReview?.repeatedMistakesText || '');
    setEffectiveActionsText(data?.weeklyReview?.effectiveActionsText || '');
    setEmotionPatternText(data?.weeklyReview?.emotionPatternText || '');
    setNextWeekFocusText(data?.weeklyReview?.nextWeekFocusText || '');
    setRuleCandidatesText(data?.weeklyReview?.ruleCandidatesText || '');
  }, [data?.weeklyReview?.id, data?.weekStart]);

  const save = async () => {
    if (!data) return;
    setSaving(true);
    try {
      await onSave({
        summaryText,
        repeatedMistakesText,
        effectiveActionsText,
        emotionPatternText,
        nextWeekFocusText,
        ruleCandidatesText,
        linkedEntryIds: data.entries.map((entry) => entry.id),
      });
    } finally {
      setSaving(false);
    }
  };

  if (!data) {
    return <div className="p-8 text-center text-gray-400">正在加载周复盘...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="rounded-lg border-gray-200 bg-white">
          <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">计划外记录</CardTitle></CardHeader>
          <CardContent className="text-[11px] text-gray-600 space-y-2">
            {data.planDeviationEntries.length === 0 ? <p className="text-gray-400">本周暂无计划外或临盘调整记录。</p> : data.planDeviationEntries.map((entry) => (
              <p key={entry.id}>{entry.tradeDate} / {entry.conclusionText}</p>
            ))}
          </CardContent>
        </Card>
        <Card className="rounded-lg border-gray-200 bg-white">
          <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">低纪律记录</CardTitle></CardHeader>
          <CardContent className="text-[11px] text-gray-600 space-y-2">
            {data.lowDisciplineEntries.length === 0 ? <p className="text-gray-400">本周暂无低纪律评分记录。</p> : data.lowDisciplineEntries.map((entry) => (
              <p key={entry.id}>{entry.tradeDate} / 纪律 {entry.disciplineScore} / {entry.conclusionText}</p>
            ))}
          </CardContent>
        </Card>
      </div>

      <EntryList entries={data.entries} />

      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">周总结</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <label className="space-y-1 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-gray-500">本周总评</span>
            <textarea className={textareaClass} value={summaryText} placeholder="例：本周主要问题是急躁，计划外加仓增多。" onChange={(event) => setSummaryText(event.target.value)} />
          </label>
          <label className="space-y-1 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-gray-500">本周重复错误</span>
            <textarea className={textareaClass} value={repeatedMistakesText} placeholder="例：无操作日后更容易急于出手；看到龙头涨停后追后排。" onChange={(event) => setRepeatedMistakesText(event.target.value)} />
          </label>
          <label className="space-y-1 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-gray-500">本周做对动作</span>
            <textarea className={textareaClass} value={effectiveActionsText} placeholder="例：大盘不明朗时减仓；忍住没有接飞刀。" onChange={(event) => setEffectiveActionsText(event.target.value)} />
          </label>
          <label className="space-y-1 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-gray-500">本周情绪模式</span>
            <textarea className={textareaClass} value={emotionPatternText} placeholder="例：怕踏空主要出现在板块龙头封板后。" onChange={(event) => setEmotionPatternText(event.target.value)} />
          </label>
          <label className="space-y-1 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-gray-500">下周重点</span>
            <textarea className={textareaClass} value={nextWeekFocusText} placeholder="例：只做计划内交易；后排不放量不加仓。" onChange={(event) => setNextWeekFocusText(event.target.value)} />
          </label>
          <label className="space-y-1 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-gray-500">本周可沉淀规则</span>
            <textarea className={textareaClass} value={ruleCandidatesText} placeholder="例：缩量反弹不视为板块启动；高开回落不追后排。" onChange={(event) => setRuleCandidatesText(event.target.value)} />
          </label>
          <div className="lg:col-span-2 flex justify-end">
            <Button type="button" disabled={saving} onClick={save} className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700">
              {saving ? '保存中...' : '保存周复盘'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
