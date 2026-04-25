/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Search, 
  MonitorPlay, 
  History, 
  Settings, 
  ShieldCheck,
  TrendingUp,
  FileText
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: '首页概览', path: '/' },
  { icon: Search, label: '股票研究', path: '/research' },
  { icon: MonitorPlay, label: '交易控制台', path: '/trading' },
  { icon: History, label: '持仓与日志', path: '/history' },
];

export const Sidebar = () => {
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
          <span>数据源 Tushare</span> 
          <span className="text-green-500 underline underline-offset-2">已连接</span>
        </div>
        <div className="flex justify-between">
          <span>AI 服务</span> 
          <span className="text-green-500 underline underline-offset-2">正常</span>
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
