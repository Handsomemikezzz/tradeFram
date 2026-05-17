import React from 'react';
import { Badge } from '@/components/ui/badge';
import { StockReviewEventResponse } from '@/services/api';
import { stockReviewEventTypeLabel } from './reviewLabels';

interface EventTimelineProps {
  events?: StockReviewEventResponse[];
}

const TagRow = ({ label, tags, tone }: { label: string; tags: string[]; tone: 'blue' | 'amber' }) => {
  if (tags.length === 0) return null;
  const classes = tone === 'blue' ? 'bg-blue-50 text-blue-700 border-blue-100' : 'bg-amber-50 text-amber-700 border-amber-100';

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-bold uppercase text-gray-400">{label}</span>
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className={`border text-[9px] ${classes}`}>{tag}</Badge>
      ))}
    </div>
  );
};

export const EventTimeline = ({ events = [] }: EventTimelineProps) => {
  if (events.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 p-5 text-center text-[12px] text-gray-400">暂无过程事件。</div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.id} className="border-l-2 border-blue-100 pl-3">
          <div className="rounded-lg border border-gray-200 bg-white p-3 space-y-2">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="font-mono text-[10px] font-bold text-gray-400">{event.eventDate}</div>
                <h4 className="break-words text-[13px] font-bold text-gray-900">{event.title}</h4>
              </div>
              <div className="flex shrink-0 flex-wrap justify-end gap-1">
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">
                  {stockReviewEventTypeLabel[event.eventType] || event.eventType}
                </Badge>
                {event.deviatedFromPlan && <Badge variant="secondary" className="text-[9px] bg-red-50 text-red-700">偏离计划</Badge>}
              </div>
            </div>

            <p className="whitespace-pre-wrap break-words text-[11px] leading-5 text-gray-700">{event.reasonText}</p>
            {event.positionSnapshot && (
              <p className="whitespace-pre-wrap break-words rounded border border-gray-100 bg-gray-50 px-2 py-1.5 text-[11px] leading-5 text-gray-600">
                {event.positionSnapshot}
              </p>
            )}

            <TagRow label="情绪" tags={event.emotionTags} tone="blue" />
            <TagRow label="问题" tags={event.problemTags} tone="amber" />
          </div>
        </div>
      ))}
    </div>
  );
};
