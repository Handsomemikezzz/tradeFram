/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Research from './pages/Research';
import ReportDetail from './pages/ReportDetail';
import LimitUpBreakMonitor from './pages/LimitUpBreakMonitor';
import DataHealth from './pages/DataHealth';
import TradingConsole from './pages/TradingConsole';
import HistoryPage from './pages/History';
import Reviews from './pages/Reviews';
import HotStocks from './pages/HotStocks';
import { TooltipProvider } from "@/components/ui/tooltip";

export default function App() {
  return (
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/research" element={<Research />} />
            <Route path="/research/:code" element={<ReportDetail />} />
            <Route path="/hot-stocks" element={<HotStocks />} />
            <Route path="/limit-up-breaks" element={<LimitUpBreakMonitor />} />
            <Route path="/reviews" element={<Reviews />} />
            <Route path="/data-health" element={<DataHealth />} />
            <Route path="/trading" element={<TradingConsole />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  );
}
