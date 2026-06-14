import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CheckCircle, 
  Circle, 
  Sun, 
  Moon, 
  ArrowRight, 
  Sparkles, 
  Clock, 
  ArrowUpRight, 
  Calendar, 
  AlertCircle,
  EyeOff
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { reviewCardApi, StockReviewCardResponse } from '@/services/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type Phase = 'PRE_MARKET' | 'POST_MARKET';

interface DailyFlowState {
  emptyToday: boolean;
  checkedSteps: Record<string, boolean>;
}

export const DailyFlow = () => {
  const navigate = useNavigate();
  
  // Determine current phase based on local time
  // Before 3:00 PM (15:00) -> Pre-market
  // After 3:00 PM -> Post-market
  const getAutoPhase = (): Phase => {
    const hour = new Date().getHours();
    return hour < 15 ? 'PRE_MARKET' : 'POST_MARKET';
  };

  const getTodayStr = (): string => {
    return new Date().toISOString().slice(0, 10);
  };

  const todayStr = getTodayStr();
  const isWeekend = (): boolean => {
    const day = new Date().getDay();
    return day === 0 || day === 6; // Sunday or Saturday
  };

  const [phase, setPhase] = useState<Phase>(getAutoPhase());
  const [emptyToday, setEmptyToday] = useState(false);
  const [checkedSteps, setCheckedSteps] = useState<Record<string, boolean>>({});
  const [todayCards, setTodayCards] = useState<StockReviewCardResponse[]>([]);
  const [weeklyCards, setWeeklyCards] = useState<StockReviewCardResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [showOptional, setShowOptional] = useState(false);

  // Load state from localStorage
  useEffect(() => {
    const storageKey = `waytofree:daily-flow:${todayStr}`;
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as DailyFlowState;
        setEmptyToday(parsed.emptyToday || false);
        setCheckedSteps(parsed.checkedSteps || {});
      } catch (e) {
        console.error('Failed to parse daily flow state', e);
      }
    }
  }, [todayStr]);

  // Save state to localStorage
  const saveState = (newEmpty: boolean, newChecked: Record<string, boolean>) => {
    const storageKey = `waytofree:daily-flow:${todayStr}`;
    const state: DailyFlowState = {
      emptyToday: newEmpty,
      checkedSteps: newChecked,
    };
    localStorage.setItem(storageKey, JSON.stringify(state));
  };

  // Fetch today's and weekly review cards for auto-check and stats
  const fetchCards = async () => {
    setLoading(true);
    try {
      const response = await reviewCardApi.getCards({ pageSize: 100 });
      const cards = response.items;
      
      // Filter today's cards
      const filteredToday = cards.filter(card => card.startDate === todayStr);
      setTodayCards(filteredToday);

      // Filter past 7 days cards (for weekend workbench)
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      const sevenDaysAgoStr = sevenDaysAgo.toISOString().slice(0, 10);
      const filteredWeekly = cards.filter(card => card.startDate >= sevenDaysAgoStr);
      setWeeklyCards(filteredWeekly);
    } catch (err) {
      console.error('Failed to fetch cards in DailyFlow', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCards();
  }, [todayStr]);

  // Toggle checklist step
  const toggleStep = (stepId: string) => {
    const nextChecked = {
      ...checkedSteps,
      [stepId]: !checkedSteps[stepId],
    };
    setCheckedSteps(nextChecked);
    saveState(emptyToday, nextChecked);
  };

  // Toggle empty today status
  const handleToggleEmptyToday = () => {
    const nextEmpty = !emptyToday;
    setEmptyToday(nextEmpty);
    
    // Auto check/uncheck Step 5 and auto-toggle card creation step if empty today is selected
    const nextChecked = {
      ...checkedSteps,
      'step-5': nextEmpty,
    };
    if (nextEmpty) {
      nextChecked['step-4'] = true; // No plan cards needed if empty today
    }
    setCheckedSteps(nextChecked);
    saveState(nextEmpty, nextChecked);
    
    if (nextEmpty) {
      toast.success('已标记今日空仓，盘前流程已完成。');
    }
  };

  // Derived states
  const hasCards = todayCards.length > 0;
  const openCards = todayCards.filter(c => c.status === 'OPEN');
  const openCardsCount = openCards.length;
  
  // Auto-calculated step completions
  const isStepCompleted = (stepId: string): boolean => {
    if (stepId === 'step-4') {
      return hasCards || emptyToday || !!checkedSteps['step-4'];
    }
    if (stepId === 'step-5') {
      return emptyToday || !!checkedSteps['step-5'];
    }
    if (stepId === 'step-6') {
      return (hasCards && openCardsCount === 0) || emptyToday || !!checkedSteps['step-6'];
    }
    return !!checkedSteps[stepId];
  };

  const preSteps = [
    { id: 'step-1', text: '打开走势 A confirmed 列表', url: '/screeners', actionText: '去选股' },
    { id: 'step-2', text: '查看自动计算的 R:R，并过滤 < 2:1', url: '/screeners', actionText: '去查看' },
    { id: 'step-3', text: '按 R:R 降序，深入查看 Top ≤ 3 标的', url: '/screeners', actionText: '去研判' },
    { 
      id: 'step-4', 
      text: '写 0–3 张计划卡（含 If-Then 假设 + 止损 + 目标）', 
      url: '/reviews', 
      actionText: '去写卡',
      hint: hasCards ? `(已检测到今日建立 ${todayCards.length} 张计划卡)` : emptyToday ? '(今日已标记空仓)' : undefined
    },
    { 
      id: 'step-5', 
      text: '若今日无合适标的，一键标记「今日空仓」', 
      isAction: true, 
      action: handleToggleEmptyToday, 
      actionText: emptyToday ? '已空仓' : '标记空仓' 
    },
  ];

  const postSteps = [
    { 
      id: 'step-6', 
      text: '关闭今日 OPEN 计划卡（分批离场或判定无效）', 
      url: '/reviews', 
      actionText: '去关单',
      hint: hasCards ? (openCardsCount > 0 ? `(今日仍有 ${openCardsCount} 张进行中)` : '(今日计划已全部结束)') : '(今日无计划交易)'
    },
    { id: 'step-7', text: '标记 FOLLOWED / DEVIATED（是否遵守计划）', url: '/reviews', actionText: '去标记' },
    { id: 'step-8', text: '对未执行或偏离的计划记录「为什么没做」', url: '/reviews', actionText: '去记录' },
  ];

  const currentSteps = phase === 'PRE_MARKET' ? preSteps : postSteps;
  const completedCount = currentSteps.filter(s => isStepCompleted(s.id)).length;
  const progressPercent = Math.round((completedCount / currentSteps.length) * 100);
  const isPhaseDone = completedCount === currentSteps.length;

  // Weekend stats calculations
  const weeklyTotal = weeklyCards.length;
  const weeklyClosed = weeklyCards.filter(c => c.status === 'CLOSED').length;
  const weeklyFollowed = weeklyCards.filter(c => c.status === 'CLOSED' && c.followedPlan === true).length;
  const weeklyDeviated = weeklyCards.filter(c => c.status === 'CLOSED' && c.followedPlan === false).length;
  const closeRate = weeklyTotal > 0 ? Math.round((weeklyClosed / weeklyTotal) * 100) : 0;
  const followedRate = weeklyClosed > 0 ? Math.round((weeklyFollowed / weeklyClosed) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Weekend Workbench Alert */}
      {isWeekend() && (
        <Card className="border-indigo-200 bg-gradient-to-r from-indigo-50/70 to-blue-50/70 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
          <CardContent className="p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex gap-3">
              <Calendar className="h-5 w-5 text-indigo-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  周末 Workbench 周复盘提醒
                  <span className="bg-indigo-600 text-white font-mono text-[9px] px-1 rounded uppercase tracking-wider font-bold">Weekend</span>
                </h4>
                <p className="text-[11px] text-slate-500 mt-1">
                  今天是周末，建议进入复盘 workbench 进行周度提炼，并将偏离与心法候选沉淀写入铁律。
                </p>
                {weeklyTotal > 0 && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[10px] font-mono text-slate-600 font-semibold">
                    <span>本周计划卡: {weeklyTotal} 张</span>
                    <span className="text-emerald-600">已关单率: {closeRate}%</span>
                    <span className={cn(followedRate >= 80 ? "text-blue-600" : "text-amber-600")}>
                      纪律遵守率: {followedRate}% ({weeklyFollowed} 守纪 / {weeklyDeviated} 偏离)
                    </span>
                  </div>
                )}
              </div>
            </div>
            <Button
              size="sm"
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-bold shrink-0 self-end md:self-center uppercase tracking-wider h-8"
              onClick={() => navigate('/reviews')}
            >
              去 Workbench 复盘
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Main Daily Flow Card */}
      <Card className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <CardContent className="p-5 space-y-4">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-3">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-blue-500" />
                今日交易流程 (Daily Flow v1)
              </h3>
              <p className="text-[10px] text-slate-400 font-medium uppercase tracking-widest font-mono">
                {todayStr} · Guided Trade Coach
              </p>
            </div>
            
            {/* Phase Switcher */}
            <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-lg border border-slate-200 shadow-inner">
              <button
                type="button"
                onClick={() => setPhase('PRE_MARKET')}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold transition-all',
                  phase === 'PRE_MARKET'
                    ? 'bg-white text-blue-600 shadow-sm border border-slate-200'
                    : 'text-slate-500 hover:text-slate-800'
                )}
              >
                <Sun className="h-3.5 w-3.5" />
                盘前流程 (08:00–09:20)
              </button>
              <button
                type="button"
                onClick={() => setPhase('POST_MARKET')}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold transition-all',
                  phase === 'POST_MARKET'
                    ? 'bg-white text-blue-600 shadow-sm border border-slate-200'
                    : 'text-slate-500 hover:text-slate-800'
                )}
              >
                <Moon className="h-3.5 w-3.5" />
                盘后复盘 (21:30–22:30)
              </button>
            </div>
          </div>

          {/* Time Sync Alert */}
          <div className="flex items-center gap-2 text-[10px] text-slate-500 bg-slate-50 border border-slate-100 px-3 py-1.5 rounded">
            <Clock className="h-3.5 w-3.5 text-blue-500 shrink-0" />
            <span>当前时段自动推荐：</span>
            <span className="font-bold text-slate-700 uppercase">{phase === 'PRE_MARKET' ? '盘前准备' : '盘后复盘'}</span>
            <span className="text-slate-300">|</span>
            <button 
              type="button" 
              className="text-blue-600 hover:underline font-semibold"
              onClick={() => setPhase(getAutoPhase())}
            >
              同步本地时间
            </button>
          </div>

          {/* Progress Indicator */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
              <span>{phase === 'PRE_MARKET' ? '盘前准备进度' : '盘后复盘进度'}</span>
              <span>{completedCount} / {currentSteps.length} 已完成 ({progressPercent}%)</span>
            </div>
            <Progress value={progressPercent} className="h-1.5 bg-slate-100" />
          </div>

          {/* Completion Banner */}
          {isPhaseDone && (
            <div className="bg-emerald-50 border border-emerald-100 text-emerald-800 rounded-lg p-3 text-[11px] font-semibold flex items-center gap-2 animate-in fade-in zoom-in-95 duration-200">
              <CheckCircle className="h-4.5 w-4.5 text-emerald-600 shrink-0 animate-bounce" />
              {phase === 'PRE_MARKET' 
                ? '盘前准备已全部就绪！纪律是你的坚实防线，静待符合预期的开盘假设。' 
                : '今日盘后复盘记录已录入完毕！在记录中孵化逻辑，期待明天的稳定交易。'}
            </div>
          )}

          {/* Checklist Items */}
          <div className="divide-y divide-slate-100">
            {currentSteps.map((step) => {
              const done = isStepCompleted(step.id);
              return (
                <div key={step.id} className="py-3 flex items-center justify-between gap-4 group">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <button
                      type="button"
                      onClick={() => toggleStep(step.id)}
                      className="mt-0.5 shrink-0 transition-transform group-hover:scale-110 active:scale-95"
                      aria-label={done ? 'Mark incomplete' : 'Mark complete'}
                    >
                      {done ? (
                        <CheckCircle className="h-4.5 w-4.5 text-blue-500 fill-blue-50" />
                      ) : (
                        <Circle className="h-4.5 w-4.5 text-slate-300 hover:text-blue-500" />
                      )}
                    </button>
                    <div className="min-w-0">
                      <p className={cn(
                        'text-[11px] font-semibold text-slate-700 leading-normal',
                        done && 'text-slate-400 line-through font-medium'
                      )}>
                        {step.text}
                      </p>
                      {step.hint && (
                        <p className="text-[9px] text-blue-500 font-medium font-mono mt-0.5">{step.hint}</p>
                      )}
                    </div>
                  </div>
                  
                  {/* Action Link/Button */}
                  {step.isAction ? (
                    <Button
                      size="sm"
                      variant={done ? 'secondary' : 'outline'}
                      className={cn(
                        'h-7 text-[10px] font-bold px-2.5 shrink-0 border border-slate-200',
                        !done && 'text-blue-600 hover:text-blue-700 hover:bg-blue-50 hover:border-blue-200'
                      )}
                      onClick={step.action}
                    >
                      {step.actionText}
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-[10px] font-bold px-2 text-slate-500 hover:text-slate-900 shrink-0 border border-slate-200 hover:bg-slate-50 hover:border-slate-300"
                      onClick={() => navigate(step.url!)}
                    >
                      <span>{step.actionText}</span>
                      <ArrowUpRight className="h-3 w-3 ml-0.5 text-slate-400" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Tier 2 Folding Optional Section */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowOptional(v => !v)}
              className="flex items-center justify-between w-full text-[10px] text-slate-400 font-bold uppercase tracking-widest hover:text-slate-600 transition-colors"
            >
              <span>🔍 盘前/盘后可选模块 (今日建议不必看)</span>
              <EyeOff className={cn("h-3.5 w-3.5 transition-transform duration-200", showOptional && "rotate-180")} />
            </button>
            {showOptional && (
              <div className="mt-3 p-3 bg-slate-50/70 border border-slate-100 rounded-lg text-[10px] text-slate-500 leading-relaxed space-y-2 animate-in slide-in-from-top-1 duration-200">
                <p>
                  以下模块可做情绪参考，但**绝对不进入今日交易主流程，不可临时起意写计划卡或介入交易**：
                </p>
                <ul className="list-disc list-inside pl-1 space-y-1 font-semibold text-slate-600">
                  <li><span className="text-slate-500 font-normal">断板监控 (Limit Up Breaks)</span> — 仅做热点及连板情绪判定</li>
                  <li><span className="text-slate-500 font-normal">上行趋势选股 (Uptrend Screener)</span> — 只做大中盘趋势观察</li>
                  <li><span className="text-slate-500 font-normal">热门股票排行 (Hot Stocks)</span> — 仅用作超短情绪指标</li>
                </ul>
                <div className="flex gap-2 pt-1">
                  <button type="button" className="text-blue-500 hover:underline font-bold" onClick={() => navigate('/screeners')}>断板监控</button>
                  <span className="text-slate-300">|</span>
                  <button type="button" className="text-blue-500 hover:underline font-bold" onClick={() => navigate('/screeners')}>趋势选股</button>
                  <span className="text-slate-300">|</span>
                  <button type="button" className="text-blue-500 hover:underline font-bold" onClick={() => navigate('/hot-stocks')}>热门股</button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
