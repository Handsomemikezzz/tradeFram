import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Zap, CheckCircle2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ExecutionTraceResponse, ExecutionTraceStepResponse, tradingApi } from '@/services/api';

export const PROCESS_STEPS = [
  { label: 'Signal Engine', step: 'SIGNAL' },
  { label: 'Risk Engine', step: 'RISK_CHECK' },
  { label: 'Order Manager', step: 'ORDER' },
  { label: 'Paper Broker', step: 'EXECUTION' },
  { label: 'Position Manager', step: 'POSITION' },
  { label: 'Trade Logger', step: 'LOG' },
];

const normalizeStatus = (status: string) => status.toLowerCase();

interface TraceStepperProps {
  refreshKey?: number;
}

export const TraceStepper = ({ refreshKey = 0 }: TraceStepperProps) => {
  const [trace, setTrace] = useState<ExecutionTraceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    tradingApi.getLatestExecutionTrace()
      .then((data) => {
        if (cancelled) return;
        setTrace(data);
        setError(null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const steps: ExecutionTraceStepResponse[] = trace?.steps || PROCESS_STEPS.map((step) => ({ ...step, status: 'PENDING', relId: null }));

  return (
    <Card className="bg-[#151619] border border-gray-800 shadow-sm rounded-lg text-white">
      <CardHeader className="px-4 py-3 border-b border-white/10">
        <CardTitle className="text-[10px] font-bold flex items-center gap-2 uppercase tracking-wider italic font-serif">
          <Zap className="w-3.5 h-3.5 text-blue-400" />
          最新链路执行追踪 (Trace)
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        {loading && <div className="text-[10px] text-white/40">正在加载链路追踪...</div>}
        {!loading && error && <div className="text-[10px] text-red-400">{error}</div>}
        {!loading && !error && (
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {steps.map((step, idx) => {
              const status = normalizeStatus(step.status);
              return (
                <React.Fragment key={step.step}>
                  <div className={cn("flex flex-col items-center gap-1 shrink-0", status === 'pending' || status === 'skipped' ? "opacity-30" : "opacity-100")}>
                    <div className={cn(
                      "w-5 h-5 rounded-full border flex items-center justify-center text-[8px]",
                      status === 'completed' ? "bg-blue-600 border-blue-600 text-white" :
                      status === 'active' || trace?.currentStep === step.step ? "bg-white text-blue-600 border-blue-600 animate-pulse font-bold" :
                      "bg-transparent border-white/20 text-white/20"
                    )}>
                      {status === 'completed' ? <CheckCircle2 className="w-3 h-3" /> : (idx + 1)}
                    </div>
                    <span className={cn("text-[8px] font-bold uppercase tracking-tighter text-center w-16", status === 'active' || trace?.currentStep === step.step ? "text-blue-400" : "text-white/60")}>{step.label}</span>
                  </div>
                  {idx < steps.length - 1 && <ArrowRight className="w-3 h-3 text-white/30 shrink-0 mb-4" />}
                </React.Fragment>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
