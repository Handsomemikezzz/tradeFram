import React from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export const TodayTasks = () => {
  const tasks = [
    { title: '风控拦截待查看', count: 2, color: 'text-red-600' },
    { title: '数据超过 24 小时未更新', count: 0, color: 'text-gray-400' },
    { title: '研究报告生成失败', count: 1, color: 'text-red-600' },
    { title: '交易监控池暂停股票', count: 3, color: 'text-gray-500' },
  ];

  return (
    <Card className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
      <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-700 italic font-serif mb-3">今日待处理事项</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {tasks.map((task) => (
          <div key={task.title} className="flex items-center justify-between border border-gray-100 rounded p-3 bg-gray-50/50">
            <span className="text-[11px] font-bold text-gray-700">{task.title}</span>
            <span className={cn("text-xs font-bold font-mono", task.color)}>{task.count}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};
