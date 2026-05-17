import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ReviewStatsResponse } from '@/services/api';

const topEntry = (items: Record<string, number>) => Object.entries(items).sort((a, b) => b[1] - a[1])[0];

export const StatsOverview = ({ stats }: { stats: ReviewStatsResponse | null }) => {
  const topProblem = stats ? topEntry(stats.problemTagCounts) : undefined;
  const topEmotion = stats ? topEntry(stats.emotionTagCounts) : undefined;
  const planDeviation = stats ? (stats.planStatusCounts.UNPLANNED || 0) + (stats.planStatusCounts.INTRADAY_ADJUSTMENT || 0) : null;
  const cards = [
    ['统计区间', stats ? `${stats.startDate} ~ ${stats.endDate}` : '-'],
    ['记录数', stats ? String(stats.totalCount) : '-'],
    ['交易 / 观察', stats ? `${stats.tradeActionCount} / ${stats.observationDecisionCount}` : '-'],
    ['计划外次数', planDeviation == null ? '-' : String(planDeviation)],
    ['最高频问题', topProblem ? `${topProblem[0]} (${topProblem[1]})` : '-'],
    ['最高频情绪', topEmotion ? `${topEmotion[0]} (${topEmotion[1]})` : '-'],
    ['平均纪律', stats?.averageDisciplineScore == null ? '-' : stats.averageDisciplineScore.toFixed(2)],
    ['低纪律', stats ? `${stats.lowDisciplineCount} 条 <= ${stats.lowDisciplineThreshold}` : '-'],
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map(([label, value]) => (
        <Card key={label} className="rounded-lg border-gray-200 bg-white">
          <CardContent className="p-4">
            <p className="text-[10px] uppercase tracking-widest text-gray-400 font-bold">{label}</p>
            <p className="mt-2 text-lg font-bold text-gray-900">{value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
