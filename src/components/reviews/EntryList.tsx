import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ReviewEntryResponse } from '@/services/api';
import { reviewActionLabel, reviewEntryTypeLabel, reviewPlanStatusLabel } from './reviewLabels';

export const EntryList = ({ entries }: { entries: ReviewEntryResponse[] }) => (
  <Card className="rounded-lg border-gray-200 bg-white overflow-hidden">
    <CardContent className="p-0">
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto">日期</TableHead>
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto">行为</TableHead>
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto">标的/板块</TableHead>
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto">计划</TableHead>
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto">标签</TableHead>
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto text-center">纪律</TableHead>
            <TableHead className="px-4 py-2 text-[10px] font-bold uppercase text-gray-400 h-auto">结论</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.length === 0 && (
            <TableRow><TableCell colSpan={7} className="px-4 py-8 text-center text-gray-400">暂无复盘记录。</TableCell></TableRow>
          )}
          {entries.map((entry) => (
            <TableRow key={entry.id} className="hover:bg-blue-50 transition-colors border-gray-50">
              <TableCell className="px-4 py-3 text-[11px] font-mono text-gray-500">{entry.tradeDate}</TableCell>
              <TableCell className="px-4 py-3 text-[11px]">
                <div className="font-bold text-gray-900">{reviewActionLabel[entry.actionType] || entry.actionType}</div>
                <div className="text-[10px] text-gray-400">{reviewEntryTypeLabel[entry.entryType] || entry.entryType}</div>
              </TableCell>
              <TableCell className="px-4 py-3 text-[11px]">
                <div className="font-mono text-gray-700">{entry.code || '-'}</div>
                <div className="text-gray-500">{entry.name || entry.sectorTags.join(' / ') || '-'}</div>
              </TableCell>
              <TableCell className="px-4 py-3 text-[11px] text-gray-600">{reviewPlanStatusLabel[entry.planStatus] || entry.planStatus}</TableCell>
              <TableCell className="px-4 py-3">
                <div className="flex flex-wrap gap-1">
                  {[...entry.emotionTags, ...entry.problemTags].slice(0, 4).map((tag) => (
                    <Badge key={`${entry.id}-${tag}`} variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{tag}</Badge>
                  ))}
                </div>
              </TableCell>
              <TableCell className="px-4 py-3 text-center font-mono text-[12px] font-bold text-gray-800">{entry.disciplineScore}</TableCell>
              <TableCell className="px-4 py-3 text-[11px] text-gray-700 max-w-md">{entry.conclusionText}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </CardContent>
  </Card>
);
