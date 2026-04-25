/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { 
  Bell, 
  Activity, 
  Database, 
  CircleCheck,
  AlertCircle
} from 'lucide-react';
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export const TopBar = () => {
  const now = new Date();
  const timeStr = now.toISOString().replace('T', ' ').substring(0, 19);

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center space-x-4">
        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] font-bold rounded uppercase">Paper Trading / 模拟交易</span>
        <div className="flex items-center text-xs text-gray-500">
          <span className="w-2 h-2 rounded-full bg-green-500 mr-2 shadow-[0_0_5px_#22c55e]"></span>
          系统状态：运行中 (正常)
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <TooltipProvider>
          <div className="flex items-center gap-4">
            <Tooltip>
              <TooltipTrigger>
                <div className="flex items-center gap-1.5 cursor-help">
                  <Database className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-[10px] font-medium text-gray-500">Tushare: 35ms</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>数据源延迟良好</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>

        <div className="text-right">
          <p className="text-[10px] text-gray-400 uppercase tabular-nums">{timeStr}</p>
          <p className="text-[10px] font-mono text-gray-700 font-semibold uppercase tracking-tighter">SH/SZ 交易日</p>
        </div>
        
        <button className="px-3 py-1.5 bg-gray-900 text-white text-[10px] font-bold rounded hover:bg-gray-800 transition-colors uppercase tracking-wider">
          导出日报
        </button>
      </div>
    </header>
  );
};
