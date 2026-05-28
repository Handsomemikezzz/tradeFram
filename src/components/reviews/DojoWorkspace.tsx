import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { AlertCircle, Brain, RefreshCw, ShieldCheck } from 'lucide-react';
import { reviewApi } from '@/services/api/reviewApi';
import { ReviewEntryResponse } from '@/services/api/types';
import { IronLawsBoard } from './IronLawsBoard';
import { ReflectionTimeline } from './ReflectionTimeline';

export const DojoWorkspace = () => {
  const [reflections, setReflections] = useState<ReviewEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchReflections = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);

    try {
      // Query the backend entries
      const response = await reviewApi.getEntries({
        entryType: 'OBSERVATION_DECISION',
        pageSize: 100,
      });
      
      // Filter entries tagged with name === 'MINDSET_DOJO'
      const dojoItems = response.items.filter(
        (item) => item.name === 'MINDSET_DOJO'
      );
      
      // Sort by tradeDate descending, then by createdAt descending
      const sortedItems = [...dojoItems].sort((a, b) => {
        const dateCompare = b.tradeDate.localeCompare(a.tradeDate);
        if (dateCompare !== 0) return dateCompare;
        return b.createdAt.localeCompare(a.createdAt);
      });

      setReflections(sortedItems);
    } catch (err) {
      toast.error('加载交易心法记录失败，请检查网络联通');
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchReflections().catch(() => {});
  }, []);

  const handleAddReflection = async (payload: {
    tradeDate: string;
    actionType: string; // '心法顿悟' | '盘后忏悔' | '自我对话'
    disciplineScore: number;
    emotionTags: string[];
    problemTags: string[];
    reasonText: string;
    reflectionText: string;
    conclusionText: string;
    nextActionText: string;
    outcomeText?: string | null;
  }) => {
    try {
      await reviewApi.createEntry({
        entryType: 'OBSERVATION_DECISION',
        actionType: 'PLAN_OBSERVE', // backend restricted, map here
        tradeDate: payload.tradeDate,
        code: '000000', // fallback required field
        name: 'MINDSET_DOJO', // tag to identify Dojo entry
        planStatus: 'OBSERVED_ONLY',
        sectorTags: [payload.actionType], // sectorTags used to store ActionType
        positionContext: 'MINDSET',
        emotionTags: payload.emotionTags,
        problemTags: payload.problemTags,
        reasonText: payload.reasonText,
        reflectionText: payload.reflectionText,
        conclusionText: payload.conclusionText,
        nextActionText: payload.nextActionText,
        disciplineScore: payload.disciplineScore,
        outcomeText: payload.outcomeText || null,
      });

      toast.success('心法与反思已成功记录');
      await fetchReflections(true);
    } catch (err) {
      toast.error('保存心法记录失败，请检查表单必填项');
      throw err;
    }
  };

  const handleDeleteReflection = async (id: string) => {
    try {
      await reviewApi.deleteEntry(id);
      toast.success('记录已成功删除');
      await fetchReflections(true);
    } catch (err) {
      toast.error('删除记录失败');
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50/70 via-indigo-50/40 to-white p-5 shadow-sm">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <Brain className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                交易员道场 (Trader's Dojo)
                <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/10">
                  <ShieldCheck className="h-3 w-3" /> 心法纪律
                </span>
              </h3>
              <p className="text-xs text-slate-600 mt-1 max-w-2xl">
                “交易是心性的镜像”。这里是你进行战略性自我审视、累积否定性规则（避坑指南）和记录心理印记的主阵地，帮助你在波动的市场中保持觉知。
              </p>
            </div>
          </div>
          <button
            onClick={() => fetchReflections(true)}
            disabled={refreshing}
            className="flex self-start md:self-auto h-8 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-600 shadow-xs hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-xs text-slate-500 font-medium">正在开启交易员道场...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-6 items-start">
          {/* Left Column: Iron Laws Board */}
          <IronLawsBoard reflections={reflections} />

          {/* Right Column: Reflection Timeline */}
          <ReflectionTimeline
            reflections={reflections}
            onAddReflection={handleAddReflection}
            onDeleteReflection={handleDeleteReflection}
          />
        </div>
      )}
    </div>
  );
};
