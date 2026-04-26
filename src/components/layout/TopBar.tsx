/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Database } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { DataSourceHealthItem, systemApi, SystemStatusResponse, systemStatusLabel } from '@/services/api';

export const TopBar = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [dataSources, setDataSources] = useState<DataSourceHealthItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const now = new Date();
  const timeStr = (systemStatus?.currentTime || now.toISOString()).replace('T', ' ').substring(0, 19);
  const akshare = dataSources.find((source) => source.name === 'AkShare') || dataSources[0];

  useEffect(() => {
    let cancelled = false;
    Promise.all([systemApi.getStatus(), systemApi.getDataSourcesHealth()])
      .then(([status, sources]) => {
        if (cancelled) return;
        setSystemStatus(status);
        setDataSources(sources.items);
        setError(null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center space-x-4">
        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] font-bold rounded uppercase">Paper Trading / 模拟交易</span>
        <div className="flex items-center text-xs text-gray-500">
          <span className={`w-2 h-2 rounded-full mr-2 shadow-[0_0_5px_currentColor] ${error ? 'bg-red-500' : 'bg-green-500'}`}></span>
          系统状态：{error ? '连接异常' : `运行中 (${systemStatusLabel(systemStatus?.status || 'NORMAL')})`}
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <TooltipProvider>
          <div className="flex items-center gap-4">
            <Tooltip>
              <TooltipTrigger>
                <div className="flex items-center gap-1.5 cursor-help">
                  <Database className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-[10px] font-medium text-gray-500">
                    {akshare ? `${akshare.name}: ${akshare.latency}` : '数据源: 加载中'}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>{error || (akshare ? `数据源状态：${akshare.status}` : '正在读取数据源状态')}</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>

        <div className="text-right">
          <p className="text-[10px] text-gray-400 uppercase tabular-nums">{timeStr}</p>
          <p className="text-[10px] font-mono text-gray-700 font-semibold uppercase tracking-tighter">
            {systemStatus?.tradeDay ? 'SH/SZ 交易日' : '非交易日'}
          </p>
        </div>
        
        <button className="px-3 py-1.5 bg-gray-900 text-white text-[10px] font-bold rounded hover:bg-gray-800 transition-colors uppercase tracking-wider">
          导出日报
        </button>
      </div>
    </header>
  );
};
