
import React from 'react';
import { cn } from '@/lib/utils';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

export const STEPS = [
    '识别股票',
    '获取行情数据',
    '运行 TradingAgents',
    '整理研究报告',
    '完成'
  ];

interface ResearchStepperProps {
    step: number;
}

export const ResearchStepper = ({ step }: ResearchStepperProps) => {
    return (
        <div className="space-y-6 pt-4 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="space-y-2">
                <div className="flex justify-between text-xs font-bold text-muted-foreground uppercase tracking-widest">
                <span>正在处理: {STEPS[step]}</span>
                <span>{Math.round(((step + 1) / STEPS.length) * 100)}%</span>
                </div>
                <Progress value={((step + 1) / STEPS.length) * 100} className="h-1.5" />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {STEPS.map((s, idx) => (
                <div 
                    key={s} 
                    className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg border text-[11px] font-medium transition-all duration-300",
                    idx < step ? "bg-green-50 border-green-200 text-green-700" :
                    idx === step ? "bg-primary/5 border-primary/20 text-primary animate-pulse" :
                    "bg-zinc-50/50 border-transparent text-zinc-400"
                    )}
                >
                    {idx < step ? <CheckCircle2 className="w-3.5 h-3.5" /> : 
                    idx === step ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 
                    <div className="w-3.5 h-3.5 rounded-full border border-current" />}
                    {s}
                </div>
                ))}
            </div>
        </div>
    );
};
