/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  BookOpenCheck,
  Flame,
  LayoutDashboard,
  Search,
  TrendingDown,
  Database,
  MonitorPlay,
  History,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { dataSourceStatusLabel, DataSourceHealthItem, systemApi, SystemStatusResponse, systemStatusLabel } from '@/services/api';

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: '首页概览', path: '/' },
  { icon: Flame, label: '热门股票', path: '/hot-stocks' },
  { icon: Search, label: '股票研究', path: '/research' },
  { icon: TrendingDown, label: '连板断板', path: '/limit-up-breaks' },
  { icon: BookOpenCheck, label: '交易复盘', path: '/reviews' },
  { icon: Database, label: '数据健康', path: '/data-health' },
  { icon: MonitorPlay, label: '交易控制台', path: '/trading' },
  { icon: History, label: '持仓与日志', path: '/history' },
];

export const Sidebar = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [dataSources, setDataSources] = useState<DataSourceHealthItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([systemApi.getStatus(), systemApi.getDataSourcesHealth()])
      .then(([status, sources]) => {
        if (cancelled) return;
        setSystemStatus(status);
        setDataSources(sources.items);
      })
      .catch(() => {
        if (cancelled) return;
        setSystemStatus(null);
        setDataSources([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const akshare = dataSources.find((source) => source.name === 'AkShare');
  const aiService = dataSources.find((source) => source.name === 'AI Service');

  return (
    <aside className="w-56 bg-[var(--color-sidebar-dark)] text-white flex flex-col h-screen sticky top-0 shrink-0">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 bg-blue-500 rounded-sm flex items-center justify-center font-bold text-xs text-white">A</div>
          <h1 className="text-sm font-bold tracking-tight">A股研投模拟系统</h1>
        </div>
        <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-widest font-mono">v1.2.0 Desktop</p>
      </div>
      
      <nav className="flex-1 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center px-6 py-3 transition-colors text-sm",
              isActive 
                ? "bg-blue-600/10 border-r-4 border-blue-500 text-blue-400" 
                : "text-gray-400 hover:text-white hover:bg-white/5"
            )}
          >
            <item.icon className="w-4 h-4 mr-3" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-6 text-[11px] text-gray-500 space-y-2">
        <div className="flex justify-between">
          <span>数据源 AkShare</span>
          <span className="text-green-500 underline underline-offset-2">{akshare ? dataSourceStatusLabel(akshare.status) : '加载中'}</span>
        </div>
        <div className="flex justify-between">
          <span>AI 服务</span> 
          <span className="text-green-500 underline underline-offset-2">{aiService ? dataSourceStatusLabel(aiService.status) : systemStatusLabel(systemStatus?.status || 'NORMAL')}</span>
        </div>
      </div>
      
      <div className="p-4 border-t border-white/10">
        <button className="flex w-full items-center gap-3 px-3 py-2 text-gray-400 hover:text-white transition-colors text-xs font-medium">
          <Settings className="w-4 h-4" />
          系统设置
        </button>
      </div>
    </aside>
  );
};
