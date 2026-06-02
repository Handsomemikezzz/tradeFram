/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { hotStockApi, monitoringApi, researchApi, reviewCardApi, formatTime, HotStockItemResponse, HotStockSnapshotResponse } from '@/services/api';
import { Activity, BookOpenCheck, Eye, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';

type SortField = 'rank' | 'changePercent' | 'price';
type SortDir = 'asc' | 'desc';

export default function HotStocks() {
  const navigate = useNavigate();

  const [snapshot, setSnapshot] = useState<HotStockSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [filterIndustry, setFilterIndustry] = useState<string | null>(null);

  // --- data fetch ---
  const fetchLatest = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await hotStockApi.getLatest(50);
      setSnapshot(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '加载失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLatest(); }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const data = await hotStockApi.createSnapshot({ limit: 50, forceRefresh: true, source: 'EastmoneyHotRank' });
      setSnapshot(data);
      toast.success('热门股票快照已刷新');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '刷新失败';
      toast.error(msg);
    } finally {
      setRefreshing(false);
    }
  };

  // --- actions ---
  const handleResearch = async (item: HotStockItemResponse) => {
    try {
      const task = await researchApi.createTask({ code: item.code });
      toast.success(`已启动 ${item.name} 的研究任务`);
      navigate(`/research/${task.code}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '启动研究失败';
      toast.error(msg);
    }
  };

  const handleAddWatchlist = async (item: HotStockItemResponse) => {
    try {
      await monitoringApi.addWatchlistItem({ code: item.code, source: 'hot_stock' });
      toast.success(`${item.name} 已加入观察池`);
      // Refresh to update inWatchlist state
      fetchLatest();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '加入观察池失败';
      toast.error(msg);
    }
  };

  const handleCreateReviewCard = async (item: HotStockItemResponse) => {
    try {
      const today = new Date().toISOString().slice(0, 10);
      await reviewCardApi.createCard({
        code: item.code,
        name: item.name,
        sectorTags: item.industry ? [item.industry] : [],
        startDate: today,
        initialAction: 'WATCH',
        initialPlanStatus: 'OBSERVED_ONLY',
        initialReasonText: `热门股票排名第 ${item.rank}，来源：热门股票榜`,
        expectedMoveText: '',
        originalPlanText: '',
        initialEmotionTags: [],
      });
      toast.success(`已为 ${item.name} 创建复盘卡片`);
      fetchLatest();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '创建复盘卡片失败';
      toast.error(msg);
    }
  };

  // --- sorting & filtering ---
  const industries = useMemo(() => {
    if (!snapshot) return [];
    const set = new Set<string>();
    snapshot.items.forEach((i) => { if (i.industry) set.add(i.industry); });
    return Array.from(set).sort();
  }, [snapshot]);

  const sortedItems = useMemo(() => {
    if (!snapshot) return [];
    let items = [...snapshot.items];
    if (filterIndustry) items = items.filter((i) => i.industry === filterIndustry);
    items.sort((a, b) => {
      let cmp = 0;
      if (sortField === 'rank') cmp = a.rank - b.rank;
      else if (sortField === 'changePercent') cmp = (a.changePercent ?? 0) - (b.changePercent ?? 0);
      else if (sortField === 'price') cmp = (a.price ?? 0) - (b.price ?? 0);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return items;
  }, [snapshot, sortField, sortDir, filterIndustry]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'rank' ? 'asc' : 'desc');
    }
  };

  const sortIndicator = (field: SortField) => (sortField === field ? (sortDir === 'asc' ? ' ↑' : ' ↓') : '');

  // --- render helpers ---
  const trendColor = (label: string) => {
    if (label.includes('偏强') || label.includes('上升') || label.includes('多头')) return 'text-red-600';
    if (label.includes('偏弱') || label.includes('下降') || label.includes('空头')) return 'text-green-600';
    return 'text-gray-500';
  };

  const changeBg = (pct: number | null) => {
    if (pct === null) return '';
    if (pct > 5) return 'bg-red-100 text-red-700';
    if (pct > 0) return 'text-red-600';
    if (pct < -5) return 'bg-green-100 text-green-700';
    if (pct < 0) return 'text-green-600';
    return 'text-gray-500';
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold tracking-tight">🔥 热门股票排行</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {snapshot?.tradeDate ? `交易日 ${snapshot.tradeDate}` : '加载中...'}
            {snapshot?.generatedAt && (
              <span className="ml-2 text-gray-400">拉取于 {formatTime(snapshot.generatedAt)}</span>
            )}
            {snapshot?.isFallback && <Badge variant="outline" className="ml-2 text-[10px]">回退数据</Badge>}
            {snapshot?.source && <span className="ml-2 text-gray-400">来源: {snapshot.source}</span>}
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={handleRefresh} disabled={refreshing} className="text-xs">
          <RefreshCw className={cn('w-3.5 h-3.5 mr-1', refreshing && 'animate-spin')} />
          {refreshing ? '刷新中...' : '刷新快照'}
        </Button>
      </div>

      {/* Error / Warning banner */}
      {error && (
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-3 text-xs text-red-700">{error}</CardContent>
        </Card>
      )}
      {snapshot?.errorMessage && (
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="p-3 text-xs text-amber-700">⚠️ {snapshot.errorMessage}</CardContent>
        </Card>
      )}

      {/* Industry filter chips */}
      {industries.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <Badge
            variant={filterIndustry === null ? 'default' : 'outline'}
            className="cursor-pointer text-[10px]"
            onClick={() => setFilterIndustry(null)}
          >
            全部
          </Badge>
          {industries.map((ind) => (
            <Badge
              key={ind}
              variant={filterIndustry === ind ? 'default' : 'outline'}
              className="cursor-pointer text-[10px]"
              onClick={() => setFilterIndustry(filterIndustry === ind ? null : ind)}
            >
              {ind}
            </Badge>
          ))}
        </div>
      )}

      {/* Main table */}
      <Card className="border border-gray-200 shadow-sm rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="text-[10px] uppercase tracking-wider">
              <TableHead className="cursor-pointer select-none w-14" onClick={() => toggleSort('rank')}>
                排名{sortIndicator('rank')}
              </TableHead>
              <TableHead>代码</TableHead>
              <TableHead>名称</TableHead>
              <TableHead className="cursor-pointer select-none" onClick={() => toggleSort('price')}>
                现价{sortIndicator('price')}
              </TableHead>
              <TableHead className="cursor-pointer select-none" onClick={() => toggleSort('changePercent')}>
                涨跌幅{sortIndicator('changePercent')}
              </TableHead>
              <TableHead>行业</TableHead>
              <TableHead>趋势</TableHead>
              <TableHead>标签</TableHead>
              <TableHead>研究</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={10} className="text-center text-xs text-gray-400 py-12">加载中...</TableCell>
              </TableRow>
            )}
            {!loading && sortedItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={10} className="text-center text-xs text-gray-400 py-12">暂无数据</TableCell>
              </TableRow>
            )}
            {!loading && sortedItems.map((item) => (
              <TableRow key={item.id} className="text-xs hover:bg-gray-50">
                <TableCell className="font-mono font-bold text-center">{item.rank}</TableCell>
                <TableCell className="font-mono text-blue-600">{item.code}</TableCell>
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell className="font-mono tabular-nums">
                  {item.price !== null ? item.price.toFixed(2) : '-'}
                </TableCell>
                <TableCell className={cn('font-mono tabular-nums font-medium', changeBg(item.changePercent))}>
                  {item.changePercent !== null ? `${item.changePercent >= 0 ? '+' : ''}${item.changePercent.toFixed(2)}%` : '-'}
                </TableCell>
                <TableCell className="text-gray-500">{item.industry ?? '-'}</TableCell>
                <TableCell>
                  <span className={cn('text-[10px] font-medium', trendColor(item.trendLabel))}>{item.trendLabel}</span>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    {item.isRecentLimitUpBreak && <Badge variant="destructive" className="text-[9px] px-1 py-0">连板</Badge>}
                    {item.inWatchlist && <Badge variant="outline" className="text-[9px] px-1 py-0 border-blue-300 text-blue-600">观察中</Badge>}
                    {item.hasOpenReviewCard && <Badge variant="outline" className="text-[9px] px-1 py-0 border-amber-300 text-amber-600">复盘中</Badge>}
                  </div>
                </TableCell>
                <TableCell>
                  {item.research.status === 'HAS_REPORT' && (
                    <Badge className="text-[9px] bg-green-100 text-green-700 hover:bg-green-200 cursor-pointer" onClick={() => navigate(`/research/${item.code}`)}>
                      查看报告
                    </Badge>
                  )}
                  {item.research.status === 'PROCESSING' && <Badge variant="outline" className="text-[9px] text-blue-500 animate-pulse">研究中</Badge>}
                  {item.research.status === 'PENDING' && <Badge variant="outline" className="text-[9px] text-gray-400">排队中</Badge>}
                  {item.research.status === 'NONE' && <span className="text-gray-300 text-[10px]">—</span>}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      title="AI 研究"
                      onClick={() => handleResearch(item)}
                      disabled={item.research.status === 'PROCESSING' || item.research.status === 'PENDING'}
                    >
                      <Search className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      title="加入观察池"
                      onClick={() => handleAddWatchlist(item)}
                      disabled={item.inWatchlist}
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      title="创建复盘卡片"
                      onClick={() => handleCreateReviewCard(item)}
                      disabled={item.hasOpenReviewCard}
                    >
                      <BookOpenCheck className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Summary footer */}
      {snapshot && !loading && (
        <div className="flex items-center gap-4 text-[10px] text-gray-400 font-mono">
          <span>共 {snapshot.items.length} 只热门股票</span>
          {filterIndustry && <span>筛选: {filterIndustry} ({sortedItems.length} 只)</span>}
          <span>快照来源: {snapshot.source}</span>
          {snapshot.createdAt && <span>更新于: {snapshot.createdAt.replace('T', ' ').slice(0, 19)}</span>}
        </div>
      )}
    </div>
  );
}
